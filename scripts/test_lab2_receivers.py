"""Render and check Lab 2 receiver artifacts without deploying anything."""

import json
import os
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parent.parent
TRACK = ROOT / "labs/02-topic-fanout/iac/terraform"


def render(visible):
    environment = {
        **os.environ,
        "TF_VAR_subscription_id": "00000000-0000-0000-0000-000000000001",
        "TF_VAR_foundation_resource_group_name": "workshop",
        "TF_VAR_location": "westus",
        "TF_VAR_show_sample_payloads": str(visible).lower(),
    }
    result = subprocess.run(
        ["terraform", f"-chdir={TRACK}", "console", "-no-color"],
        input="jsonencode(local.receiver_workflows)\n", text=True,
        capture_output=True, env=environment, timeout=90,
    )
    if result.returncode:
        raise RuntimeError(f"Workflow rendering failed: {result.stderr}")
    return json.loads(json.loads(result.stdout))


def operations(definition):
    yield from definition["triggers"].values()
    for action in definition["actions"].values():
        yield action
        if "actions" in action:
            yield from operations({"triggers": {}, "actions": action["actions"]})


def settlement_path(actions, processing, complete="Succeeded", abandon="Succeeded"):
    """Follow the rendered runAfter edges for processing/settlement outcomes."""
    statuses = {"Process_message": processing}
    for name, result in [
        ("Complete_message", complete), ("Abandon_message", abandon), ("Fail_run", "Failed"),
    ]:
        enabled = all(statuses[parent] in allowed for parent, allowed in actions[name]["runAfter"].items())
        statuses[name] = result if enabled else "Skipped"
    return statuses


class ReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.visible = render(True)
        cls.protected = render(False)

    def test_exactly_three_independent_peek_lock_receivers_use_prepared_connection(self):
        self.assertEqual(set(self.visible), {"audit", "fulfillment", "notification"})
        for name, workflow in self.visible.items():
            with self.subTest(workflow=name):
                self.assertEqual(workflow["kind"], "Stateful")
                definition = workflow["definition"]
                trigger = definition["triggers"]["Receive_order"]
                self.assertEqual(trigger["inputs"]["parameters"], {
                    "topicName": "orders", "subscriptionName": name, "maxMessageBatchSize": 1,
                })
                self.assertEqual(trigger["splitOn"], "@triggerOutputs()?['body']")
                self.assertIn("correlationId", trigger["splitOnConfiguration"]["correlation"]["clientTrackingId"])
                self.assertNotIn("correlation", trigger)
                service_operations = [
                    operation["inputs"] for operation in operations(definition)
                    if operation["type"] == "ServiceProvider"
                ]
                self.assertEqual({
                    operation["serviceProviderConfiguration"]["operationId"]
                    for operation in service_operations
                }, {"peekLockTopicMessagesV2", "completeTopicMessageV2", "abandonTopicMessageV2"})
                for operation in service_operations:
                    self.assertEqual(operation["serviceProviderConfiguration"]["connectionName"], "lab02ServiceBus")
                    self.assertEqual(operation["serviceProviderConfiguration"]["serviceProviderId"], "/serviceProviders/serviceBus")
                    self.assertEqual(operation["parameters"]["subscriptionName"], name)
                    if "lockToken" in operation["parameters"]:
                        self.assertEqual(operation["parameters"]["lockToken"], "@triggerBody()?['lockToken']")

    def test_completion_requires_success_and_all_failure_paths_abandon_then_fail(self):
        for name, workflow in self.visible.items():
            actions = workflow["definition"]["actions"]
            for processing in ("Succeeded", "Failed", "TimedOut"):
                for complete in ("Succeeded", "Failed", "TimedOut"):
                    for abandon in ("Succeeded", "Failed", "TimedOut"):
                        with self.subTest(workflow=name, processing=processing, complete=complete, abandon=abandon):
                            statuses = settlement_path(actions, processing, complete, abandon)
                            if processing != "Succeeded":
                                self.assertEqual(statuses["Complete_message"], "Skipped")
                            if processing == "Succeeded" and complete == "Succeeded":
                                self.assertEqual(statuses["Abandon_message"], "Skipped")
                                self.assertEqual(statuses["Fail_run"], "Skipped")
                            else:
                                self.assertEqual(statuses["Abandon_message"], abandon)
                                self.assertEqual(statuses["Fail_run"], "Failed")
            for action in ("Complete_message", "Abandon_message"):
                self.assertEqual(actions[action]["inputs"]["retryPolicy"], {
                    "type": "fixed", "count": 2, "interval": "PT5S",
                })

    def test_visibility_protects_every_data_operation_and_never_control_actions(self):
        for name in self.visible:
            visible = list(operations(self.visible[name]["definition"]))
            protected = list(operations(self.protected[name]["definition"]))
            self.assertEqual(len(visible), len(protected))
            for shown, hidden in zip(visible, protected):
                self.assertNotIn("runtimeConfiguration", shown)
                if hidden["type"] == "ServiceProvider":
                    self.assertEqual(hidden["runtimeConfiguration"]["secureData"]["properties"], ["inputs", "outputs"])
                elif hidden["type"] in ("ParseJson", "Compose"):
                    self.assertEqual(hidden["runtimeConfiguration"]["secureData"]["properties"], ["inputs"])
                else:
                    self.assertNotIn("runtimeConfiguration", hidden)
                self.assertNotIn("trackedProperties", hidden)

    def test_lightweight_business_actions_and_identifier_only_telemetry_precede_completion(self):
        for name, workflow in self.visible.items():
            processing = workflow["definition"]["actions"]["Process_message"]["actions"]
            self.assertEqual(processing[f"Process_{name}"]["type"], "Compose")
            self.assertEqual(processing[f"Process_{name}"]["runAfter"], {"Validate_contract": ["Succeeded"]})
            telemetry = processing["Emit_telemetry"]
            self.assertEqual(telemetry["runAfter"], {f"Process_{name}": ["Succeeded"]})
            self.assertEqual(set(telemetry["inputs"]), {"eventId", "correlationId", "subscription", "status"})
            for expression in telemetry["trackedProperties"].values():
                self.assertTrue(expression.startswith("@action().outputs."))
            self.assertNotIn("recipient", self.visible["audit"]["definition"]["actions"]["Process_message"]["actions"]["Process_audit"]["inputs"])
        fulfillment = self.visible["fulfillment"]["definition"]["actions"]["Process_message"]["actions"]["Process_fulfillment"]["inputs"]
        notification = self.visible["notification"]["definition"]["actions"]["Process_message"]["actions"]["Process_notification"]["inputs"]
        self.assertIn("orderId", fulfillment)
        self.assertIn("recipient", notification)
        self.assertIn("message", notification)

    def test_contract_schema_and_metadata_validation_gate_every_business_action(self):
        contract = json.loads((ROOT / "labs/02-topic-fanout/contracts/order-created.schema.json").read_text())
        for workflow in self.visible.values():
            processing = workflow["definition"]["actions"]["Process_message"]["actions"]
            schema = processing["Parse_event"]["inputs"]["schema"]
            self.assertEqual(schema["required"], contract["required"])
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["eventType"]["enum"], ["order.created"])
            self.assertEqual(schema["properties"]["schemaVersion"]["enum"], ["1.0"])
            self.assertNotIn("pattern", json.dumps(schema))
            validation = processing["Validate_contract"]["inputs"]
            self.assertEqual(validation["schema"], {"type": "boolean", "enum": [True]})
            for field in ("contentType", "messageId", "correlationId", "eventType", "schemaVersion"):
                self.assertIn(f"['{field}']", validation["content"])
            self.assertIn("greater(body('Parse_event')['data']['total'], 0)", validation["content"])
            self.assertIn("ticks(body('Parse_event')['occurredAt'])", validation["content"])


if __name__ == "__main__":
    unittest.main()
