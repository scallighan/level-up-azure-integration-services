"""Check Lab 2 contracts and receiver-run validation without generated solutions."""

import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator, FormatChecker


SPEC = importlib.util.spec_from_file_location("lab2_receivers", Path(__file__).with_name("test-lab2.py"))
LAB2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB2)
CONTRACTS = Path(__file__).resolve().parent.parent / "labs/02-topic-fanout/contracts"
SPECIALISTS = {
    "order.created": "order-created",
    "order.cancelled": "order-cancelled",
}


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.validators = {}
        for name in ("event-envelope", "order-created", "order-cancelled"):
            schema = json.loads((CONTRACTS / f"{name}.schema.json").read_text())
            Draft202012Validator.check_schema(schema)
            cls.validators[name] = Draft202012Validator(schema, format_checker=FormatChecker())
        cls.samples = {
            event_type: json.loads((CONTRACTS / f"sample-{workflow}.json").read_text())
            for event_type, workflow in SPECIALISTS.items()
        }

    def test_samples_and_fresh_events_match_the_envelope_and_only_their_specialist(self):
        for event_type, workflow in SPECIALISTS.items():
            for event in (self.samples[event_type], LAB2.fresh_event(event_type, "ORD-portable-test")):
                with self.subTest(event_type=event_type, event_id=event["eventId"]):
                    self.validators["event-envelope"].validate(event)
                    self.validators[workflow].validate(event)
                    for other in set(SPECIALISTS.values()) - {workflow}:
                        self.assertFalse(self.validators[other].is_valid(event))

    def test_audit_accepts_future_event_types_without_a_specialist_payload_shape(self):
        event = copy.deepcopy(self.samples["order.created"])
        event["eventType"] = "order.shipped"
        event["data"] = {"shipmentId": "SHIP-1042"}
        self.validators["event-envelope"].validate(event)
        for workflow in SPECIALISTS.values():
            self.assertFalse(self.validators[workflow].is_valid(event))

    def test_order_lifecycle_samples_share_an_order_but_not_message_identifiers(self):
        created, cancelled = (self.samples[event_type] for event_type in SPECIALISTS)
        self.assertEqual(created["data"]["orderId"], cancelled["data"]["orderId"])
        self.assertNotEqual(created["eventId"], cancelled["eventId"])
        self.assertNotEqual(created["correlationId"], cancelled["correlationId"])

    def test_specialists_reject_invalid_creation_and_cancellation_data(self):
        for event_type, field, value in [
            ("order.created", "total", 0),
            ("order.created", "total", "149.95"),
            ("order.created", "currency", "usd"),
            ("order.cancelled", "reason", ""),
            ("order.cancelled", "orderId", "x" * 51),
        ]:
            event = copy.deepcopy(self.samples[event_type])
            event["data"][field] = value
            with self.subTest(event_type=event_type, field=field):
                self.assertFalse(self.validators[SPECIALISTS[event_type]].is_valid(event))
        for event_type, field in [
            ("order.created", "customerId"), ("order.cancelled", "reason"),
        ]:
            event = copy.deepcopy(self.samples[event_type])
            del event["data"][field]
            with self.subTest(event_type=event_type, missing=field):
                self.assertFalse(self.validators[SPECIALISTS[event_type]].is_valid(event))

    def test_invalid_metadata_and_unexpected_envelope_fields_are_rejected(self):
        for field, value in [
            ("eventId", "not-a-uuid"),
            ("correlationId", "not-a-uuid"),
            ("occurredAt", "not-a-timestamp"),
            ("schemaVersion", "2.0"),
            ("unexpected", "extra"),
        ]:
            event = {**self.samples["order.created"], field: value}
            with self.subTest(field=field):
                for validator in (self.validators["event-envelope"], self.validators["order-created"]):
                    self.assertFalse(validator.is_valid(event))


class ReceiverRunTests(unittest.TestCase):
    def setUp(self):
        self.event = json.loads((CONTRACTS / "sample-order-created.json").read_text())
        self.run = {"name": "run-1", "properties": {"status": "Succeeded"}}

    def actions(self, specialist):
        names = ["Process_message", "Complete_message"]
        if specialist:
            names.extend(["Read_order", "Verify_order"])
        return [
            {"name": name, "properties": {"status": "Succeeded"}}
            for name in names
        ]

    def test_specialists_require_processing_read_back_verification_and_completion(self):
        for event_type, workflow in SPECIALISTS.items():
            event = {**self.event, "eventType": event_type}
            actions = self.actions(specialist=True)
            with self.subTest(workflow=workflow), patch.object(LAB2, "arm_get", return_value={"value": actions}):
                self.assertTrue(LAB2.check_run("/runtime", self.run, event, workflow))
            for name in ("Process_message", "Complete_message", "Read_order", "Verify_order"):
                for status in ("Failed", "Skipped", "TimedOut"):
                    failed = copy.deepcopy(actions)
                    next(action for action in failed if action["name"] == name)["properties"]["status"] = status
                    with self.subTest(workflow=workflow, action=name, status=status), \
                            patch.object(LAB2, "arm_get", return_value={"value": failed}), \
                            self.assertRaisesRegex(RuntimeError, name):
                        LAB2.check_run("/runtime", self.run, event, workflow)

    def test_audit_requires_processing_and_completion_but_no_cosmos_actions(self):
        actions = self.actions(specialist=False)
        with patch.object(LAB2, "arm_get", return_value={"value": actions}) as get:
            self.assertTrue(LAB2.check_run("/runtime", self.run, self.event, "audit"))
            get.assert_called_once_with("/runtime/runs/run-1/actions")
        for name in ("Process_message", "Complete_message"):
            missing = [action for action in actions if action["name"] != name]
            with self.subTest(missing=name), patch.object(LAB2, "arm_get", return_value={"value": missing}), \
                    self.assertRaisesRegex(RuntimeError, name):
                LAB2.check_run("/runtime", self.run, self.event, "audit")

    def test_nested_cosmos_actions_are_checked_without_fetching_payload_links(self):
        paths = []

        def response(path):
            paths.append(path)
            if path == "/runtime/runs/run-1/actions":
                return {"value": self.actions(specialist=False)}
            if path in ("/runtime/runs/run-1/actions/Read_order", "/runtime/runs/run-1/actions/Verify_order"):
                return {"properties": {
                    "status": "Succeeded", "outputsLink": {"uri": "https://example.invalid/private-payload"},
                }}
            self.fail(f"Unexpected action or payload request: {path}")

        with patch.object(LAB2, "arm_get", side_effect=response), patch.object(LAB2, "urlopen") as fetch:
            self.assertTrue(LAB2.check_run("/runtime", self.run, self.event, "order-created"))
            fetch.assert_not_called()
        self.assertEqual(len(paths), 3)

    def test_failed_or_active_runs_cannot_be_reported_as_success(self):
        for status in ("Running", "Waiting", "Accepted"):
            run = {"name": "run-1", "properties": {"status": status}}
            with self.subTest(status=status), patch.object(LAB2, "arm_get") as get:
                self.assertFalse(LAB2.check_run("/runtime", run, self.event, "order-created"))
                get.assert_not_called()
        for status in ("Failed", "TimedOut", "Cancelled"):
            run = {"name": "run-1", "properties": {"status": status}}
            with self.subTest(status=status), \
                    patch.object(LAB2, "arm_get", return_value={"value": self.actions(specialist=True)}), \
                    self.assertRaisesRegex(RuntimeError, f"finished {status}"):
                LAB2.check_run("/runtime", run, self.event, "order-created")

    def test_telemetry_must_match_the_event_when_visible_but_is_optional_in_protected_history(self):
        actions = self.actions(specialist=True)
        with patch.object(LAB2, "arm_get", return_value={"value": actions}):
            self.assertTrue(LAB2.check_run("/runtime", self.run, self.event, "order-created"))
        telemetry = {"name": "Emit_telemetry", "properties": {
            "status": "Succeeded", "trackedProperties": {
                "eventId": self.event["eventId"], "correlationId": self.event["correlationId"],
            },
        }}
        actions.append(telemetry)
        with patch.object(LAB2, "arm_get", return_value={"value": actions}):
            self.assertTrue(LAB2.check_run("/runtime", self.run, self.event, "order-created"))
        for field in ("eventId", "correlationId"):
            invalid = copy.deepcopy(actions)
            invalid[-1]["properties"]["trackedProperties"][field] = "different"
            with self.subTest(field=field), patch.object(LAB2, "arm_get", return_value={"value": invalid}), \
                    self.assertRaisesRegex(RuntimeError, "does not match"):
                LAB2.check_run("/runtime", self.run, self.event, "order-created")


if __name__ == "__main__":
    unittest.main()
