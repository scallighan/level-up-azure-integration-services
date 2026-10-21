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
    def test_fresh_events_preserve_public_sample_data_but_avoid_duplicate_suppression(self):
        before = SMOKE.SAMPLE.read_text()
        first, second = SMOKE.fresh_event(), SMOKE.fresh_event()
        self.assertNotEqual(first["eventId"], second["eventId"])
        self.assertNotEqual(first["correlationId"], second["correlationId"])
        self.assertEqual(first["data"], json.loads(before)["data"])
        self.assertTrue(first["occurredAt"].endswith("Z"))
        self.assertEqual(SMOKE.SAMPLE.read_text(), before)

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
        event = SMOKE.fresh_event()
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
                SMOKE.publish(FOUNDATION["service_bus_fqdn"], SMOKE.fresh_event())
            self.assertNotIn("private-token", str(error.exception))
            send.assert_called_once()

    def test_run_success_requires_processing_and_settlement_not_just_run_status(self):
        event = SMOKE.fresh_event()
        run = {"name": "run-1", "properties": {"status": "Succeeded"}}
        actions = [
            {"name": "Process_message", "properties": {"status": "Succeeded"}},
            {"name": "Complete_message", "properties": {"status": "Succeeded"}},
            {"name": "Emit_telemetry", "properties": {
                "status": "Succeeded", "trackedProperties": {
                    "eventId": event["eventId"], "correlationId": event["correlationId"],
                },
            }},
        ]
        with patch.object(SMOKE, "arm_get", return_value={"value": actions}):
            self.assertTrue(SMOKE.check_run("/runtime", run, event))
        failed = copy.deepcopy(actions)
        failed[1]["properties"]["status"] = "Skipped"
        with patch.object(SMOKE, "arm_get", return_value={"value": failed}), \
                self.assertRaisesRegex(RuntimeError, "Complete_message"):
            SMOKE.check_run("/runtime", run, event)
        actions[2]["properties"]["trackedProperties"]["eventId"] = "wrong-event"
        with patch.object(SMOKE, "arm_get", return_value={"value": actions}), \
                self.assertRaisesRegex(RuntimeError, "does not match"):
            SMOKE.check_run("/runtime", run, event)

    def test_wait_matches_only_fresh_correlation_and_checks_all_three_workflows(self):
        event = SMOKE.fresh_event()
        response = {"value": [
            {"name": "old", "properties": {"correlation": {"clientTrackingId": "old"}}},
            {"name": "fresh", "properties": {"correlation": {"clientTrackingId": event["correlationId"]}}},
        ]}
        output = io.StringIO()
        with patch.object(SMOKE, "arm_get", return_value=response), \
                patch.object(SMOKE, "check_run", return_value=True) as check, \
                contextlib.redirect_stdout(output):
            SMOKE.wait_for_fanout(SITE, event, 10)
        self.assertEqual(check.call_count, 3)
        self.assertTrue(all(call.args[1]["name"] == "fresh" for call in check.call_args_list))
        self.assertIn("PASS", output.getvalue())
        self.assertNotIn("customerEmail", output.getvalue())

    def test_timeout_never_reports_pass(self):
        with patch.object(SMOKE.time, "monotonic", side_effect=[0, 2]), \
                self.assertRaisesRegex(TimeoutError, "audit, fulfillment, notification"):
            SMOKE.wait_for_fanout(SITE, SMOKE.fresh_event(), 1)

    def test_dry_run_never_contacts_azure(self):
        with patch.object(SMOKE.sys, "argv", ["test-lab2.py", "--dry-run"]), \
                patch.object(Path, "read_text", side_effect=[
                    json.dumps(FOUNDATION), SMOKE.SAMPLE.read_text(),
                ]), patch.object(SMOKE, "az_json") as azure, \
                patch.object(SMOKE, "urlopen") as send, \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(SMOKE.main(), 0)
            azure.assert_not_called()
            send.assert_not_called()


if __name__ == "__main__":
    unittest.main()
