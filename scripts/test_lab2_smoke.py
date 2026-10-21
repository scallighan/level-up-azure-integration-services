"""Test the Lab 2 publisher and correlated run checks without Azure writes."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError


SPEC = importlib.util.spec_from_file_location("lab2_smoke", Path(__file__).with_name("test-lab2.py"))
SMOKE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SMOKE)
SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
PRINCIPAL = "00000000-0000-0000-0000-000000000003"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/workshop"
NAMESPACE = f"{GROUP}/providers/Microsoft.ServiceBus/namespaces/workshopbus"
SITE = f"{GROUP}/providers/Microsoft.Web/sites/site"
TOPIC = f"{NAMESPACE}/topics/orders"
FOUNDATION = {
    "logic_app_id": SITE, "resource_group_name": "workshop",
    "service_bus_namespace_id": NAMESPACE, "service_bus_namespace_name": "workshopbus",
    "service_bus_fqdn": "workshopbus.servicebus.windows.net",
}


class SmokeTests(unittest.TestCase):
    def event(self, event_type="order.created"):
        return SMOKE.fresh_event(event_type, "ORD-test")

    def test_fresh_events_preserve_public_sample_data_but_avoid_duplicate_suppression(self):
        for event_type in SMOKE.EVENT_WORKFLOWS:
            sample = SMOKE.CONTRACTS / f"sample-{event_type.replace('.', '-')}.json"
            before = sample.read_text()
            first, second = self.event(event_type), self.event(event_type)
            self.assertNotEqual(first["eventId"], second["eventId"])
            self.assertNotEqual(first["correlationId"], second["correlationId"])
            expected = {**json.loads(before)["data"], "orderId": "ORD-test"}
            self.assertEqual(first["data"], expected)
            self.assertTrue(first["occurredAt"].endswith("Z"))
            self.assertEqual(sample.read_text(), before)

    def test_handoff_rejects_cross_group_namespace_and_untrusted_token_destination(self):
        self.assertEqual(SMOKE.validate_handoff(FOUNDATION), (SUBSCRIPTION, TOPIC))
        for key, value in [
            ("service_bus_fqdn", "example.com"),
            ("service_bus_namespace_id", NAMESPACE.replace("/workshop/", "/other/")),
        ]:
            with self.subTest(key=key), self.assertRaises(ValueError):
                SMOKE.validate_handoff({**FOUNDATION, key: value})

    def test_sender_check_accepts_foundation_namespace_or_legacy_topic_without_creating_roles(self):
        for scope in (NAMESPACE, TOPIC):
            assignment = {
                "principalId": PRINCIPAL, "scope": scope,
                "roleDefinitionId": f"/roles/{SMOKE.SENDER_ROLE}",
            }
            with self.subTest(scope=scope), patch.object(SMOKE, "az_json", return_value=[assignment]) as azure, \
                    contextlib.redirect_stdout(io.StringIO()):
                SMOKE.sender_access(TOPIC, PRINCIPAL)
                self.assertEqual(azure.call_args.args[0], [
                    "role", "assignment", "list", "--scope", TOPIC, "--include-inherited",
                ])

    def test_missing_or_unrelated_sender_grants_fail_without_mutations(self):
        for assignments in [[], [{
            "principalId": PRINCIPAL, "scope": GROUP,
            "roleDefinitionId": f"/roles/{SMOKE.SENDER_ROLE}",
        }], [{
            "principalId": "another-user", "scope": NAMESPACE,
            "roleDefinitionId": f"/roles/{SMOKE.SENDER_ROLE}",
        }]]:
            with self.subTest(assignments=assignments), patch.object(SMOKE, "az_json", return_value=assignments) as azure:
                with self.assertRaisesRegex(ValueError, "Complete Lab 0"):
                    SMOKE.sender_access(TOPIC, PRINCIPAL)
                self.assertEqual(azure.call_count, 1)

    def test_publish_uses_entra_and_exactly_one_http_send_with_string_application_properties(self):
        event = self.event()
        with patch.object(SMOKE, "az_json", return_value="private-token") as azure, \
                patch.object(SMOKE, "urlopen") as send:
            send.return_value.__enter__.return_value.status = 201
            SMOKE.publish(FOUNDATION["service_bus_fqdn"], event)
            azure.assert_called_once_with([
                "account", "get-access-token", "--resource", "https://servicebus.azure.net",
                "--query", "accessToken",
            ])
            send.assert_called_once()
            request = send.call_args.args[0]
            headers = {key.lower(): value for key, value in request.header_items()}
            self.assertEqual(request.full_url, "https://workshopbus.servicebus.windows.net/orders/messages")
            self.assertEqual(json.loads(request.data), event)
            self.assertEqual(headers["authorization"], "Bearer private-token")
            self.assertEqual(headers["content-type"], "application/json")
            self.assertEqual(json.loads(headers["brokerproperties"]), {
                "MessageId": event["eventId"], "CorrelationId": event["correlationId"],
            })
            for name in ("eventType", "schemaVersion", "correlationId"):
                self.assertEqual(json.loads(headers[name.lower()]), event[name])
            self.assertEqual(headers["x-ms-retrypolicy"], "NoRetry")

    def test_send_failure_does_not_retry_or_log_token(self):
        with patch.object(SMOKE, "az_json", return_value="private-token"), \
                patch.object(SMOKE, "urlopen", side_effect=HTTPError("https://example", 401, "", {}, None)) as send:
            with self.assertRaisesRegex(RuntimeError, "HTTP 401") as error:
                SMOKE.publish(FOUNDATION["service_bus_fqdn"], self.event())
            self.assertNotIn("private-token", str(error.exception))
            send.assert_called_once()

    def test_wait_matches_only_fresh_correlation_and_checks_the_routing_matrix(self):
        for event_type, specialist in SMOKE.EVENT_WORKFLOWS.items():
            event = self.event(event_type)
            response = {"value": [
                {"name": "old", "properties": {"correlation": {"clientTrackingId": "old"}}},
                {"name": "fresh", "properties": {"correlation": {"clientTrackingId": event["correlationId"]}}},
            ]}
            def runs(path):
                return response if any(f"/workflows/{name}/" in path for name in ("audit", specialist)) else {"value": []}

            output = io.StringIO()
            with self.subTest(event_type=event_type), \
                    patch.object(SMOKE, "arm_get", side_effect=runs), \
                    patch.object(SMOKE, "check_run", return_value=True) as check, \
                    contextlib.redirect_stdout(output):
                SMOKE.wait_for_fanout(SITE, event, 10, observation_seconds=0)
            self.assertEqual(check.call_count, 2)
            self.assertEqual({call.args[3] for call in check.call_args_list}, {"audit", specialist})
            self.assertTrue(all(call.args[1]["name"] == "fresh" for call in check.call_args_list))
            self.assertIn("PASS", output.getvalue())
            self.assertNotIn("customerEmail", output.getvalue())

    def test_unrelated_specialist_run_is_rejected_even_when_it_arrives_later(self):
        event = self.event()
        matching = {"value": [{
            "name": "fresh", "properties": {"correlation": {"clientTrackingId": event["correlationId"]}},
        }]}
        with patch.object(SMOKE, "arm_get", side_effect=[
            matching, matching, {"value": []}, matching, matching, matching,
        ]), patch.object(SMOKE, "check_run", return_value=True), \
                patch.object(SMOKE.time, "monotonic", return_value=0), \
                patch.object(SMOKE.time, "sleep"), \
                contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(RuntimeError, "Incorrect routing: order-cancelled"):
            SMOKE.wait_for_fanout(SITE, event, 30)

    def test_redelivery_is_not_reported_as_single_run_success(self):
        event = self.event()
        run = {"name": "fresh", "properties": {"correlation": {"clientTrackingId": event["correlationId"]}}}
        with patch.object(SMOKE, "arm_get", return_value={"value": [run, run]}), \
                self.assertRaisesRegex(RuntimeError, "multiple runs"):
            SMOKE.wait_for_fanout(SITE, event, 10)

    def test_preflight_requires_exact_broker_filters_without_default_or_rule_actions(self):
        subscriptions = [{"name": name} for name in SMOKE.WORKFLOWS]
        rules = [[{
            "name": name, "filterType": "SqlFilter",
            "sqlFilter": {"sqlExpression": expression}, "action": None,
        }] for name, expression in SMOKE.RULES.values()]
        with patch.object(SMOKE, "az_json", side_effect=[subscriptions, *rules]):
            SMOKE.ready_rules(FOUNDATION)
        compact = copy.deepcopy(rules)
        for rule in compact:
            rule[0]["sqlFilter"]["sqlExpression"] = rule[0]["sqlFilter"]["sqlExpression"].replace(" = ", "=")
        with patch.object(SMOKE, "az_json", side_effect=[subscriptions, *compact]):
            SMOKE.ready_rules(FOUNDATION)
        for bad_rule in [
            [*rules[1], {"name": "$Default"}],
            [{**rules[1][0], "sqlFilter": {"sqlExpression": "1 = 1"}}],
            [{**rules[1][0], "action": {"sqlExpression": "SET eventType = 'order.cancelled'"}}],
        ]:
            with self.subTest(bad_rule=bad_rule), patch.object(
                SMOKE, "az_json", side_effect=[subscriptions, rules[0], bad_rule],
            ), self.assertRaisesRegex(RuntimeError, "order-created must have only"):
                SMOKE.ready_rules(FOUNDATION)
        with patch.object(SMOKE, "az_json", return_value=[{"name": "fulfillment"}]), \
                self.assertRaisesRegex(RuntimeError, "Expected exactly"):
            SMOKE.ready_rules(FOUNDATION)

    def test_timeout_never_reports_pass(self):
        with patch.object(SMOKE.time, "monotonic", side_effect=[0, 2]), \
                self.assertRaisesRegex(TimeoutError, "audit, order-created"):
            SMOKE.wait_for_fanout(SITE, self.event(), 1)

    def test_successful_runs_do_not_skip_the_routing_observation_window(self):
        event = self.event()
        matching = {"value": [{
            "name": "fresh", "properties": {"correlation": {"clientTrackingId": event["correlationId"]}},
        }]}
        output = io.StringIO()
        with patch.object(SMOKE, "arm_get", side_effect=[matching, matching, {"value": []}]), \
                patch.object(SMOKE, "check_run", return_value=True), \
                patch.object(SMOKE.time, "monotonic", side_effect=[0, 0, 0, 0, 11]), \
                patch.object(SMOKE.time, "sleep"), \
                contextlib.redirect_stdout(output), \
                self.assertRaisesRegex(TimeoutError, "routing observation window"):
            SMOKE.wait_for_fanout(SITE, event, 10)
        self.assertNotIn("PASS", output.getvalue())

    def test_creation_is_verified_before_cancellation_is_sent_and_failures_stop_the_test(self):
        for creation_fails in (False, True):
            calls = []
            events = [self.event(), self.event("order.cancelled")]
            def wait(site, event, timeout):
                calls.append(("wait", event["eventType"]))
                if creation_fails:
                    raise RuntimeError("creation did not persist")

            with self.subTest(creation_fails=creation_fails), \
                    patch.object(SMOKE.sys, "argv", ["test-lab2.py"]), \
                    patch.object(Path, "read_text", return_value=json.dumps(FOUNDATION)), \
                    patch.object(SMOKE, "fresh_event", side_effect=events) as fresh, \
                    patch.object(SMOKE, "signed_in_user", return_value=PRINCIPAL), \
                    patch.object(SMOKE, "ready_workflows"), \
                    patch.object(SMOKE, "ready_rules"), \
                    patch.object(SMOKE, "sender_access"), \
                    patch.object(SMOKE, "publish", side_effect=lambda fqdn, event: calls.append(("send", event["eventType"]))), \
                    patch.object(SMOKE, "wait_for_fanout", side_effect=wait), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(SMOKE.main(), 1 if creation_fails else 0)
                self.assertTrue(all(
                    call.args[1] == fresh.call_args_list[0].args[1]
                    for call in fresh.call_args_list
                ))
            expected = [("send", "order.created"), ("wait", "order.created")]
            if not creation_fails:
                expected.extend([("send", "order.cancelled"), ("wait", "order.cancelled")])
            self.assertEqual(calls, expected)

    def test_dry_run_never_contacts_azure(self):
        with patch.object(SMOKE.sys, "argv", ["test-lab2.py", "--dry-run"]), \
                patch.object(Path, "read_text", side_effect=[
                    json.dumps(FOUNDATION),
                    (SMOKE.CONTRACTS / "sample-order-created.json").read_text(),
                    (SMOKE.CONTRACTS / "sample-order-cancelled.json").read_text(),
                ]), patch.object(SMOKE, "az_json") as azure, \
                patch.object(SMOKE, "urlopen") as send, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(SMOKE.main(), 0)
            azure.assert_not_called()
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
