"""Test Lab 2 broker and shared-artifact configuration without Azure writes."""

import contextlib
import copy
import importlib.util
import io
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location("configure_lab2", Path(__file__).with_name("configure-lab2.py"))
LAB2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LAB2)
SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
GROUP = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/workshop"
SITE = f"{GROUP}/providers/Microsoft.Web/sites/site"
NAMESPACE = f"{GROUP}/providers/Microsoft.ServiceBus/namespaces/bus"
FQDN = "bus.servicebus.windows.net"
EXISTING = {
    "managedApiConnections": {"otherApi": {"connection": {"id": "keep"}}},
    "serviceProviderConnections": {"lab01Cosmos": {"displayName": "Keep me"}},
}


class AzureRequests:
    def __init__(self, connections=EXISTING, missing=False):
        self.connections = copy.deepcopy(connections)
        self.missing = missing
        self.calls = []
        self.rules = {
            name: [
                {"name": "$Default", "properties": {"filterType": "SqlFilter", "sqlFilter": {"sqlExpression": "1=1"}}},
                {"name": "order-created", "properties": {
                    "filterType": "SqlFilter", "sqlFilter": {"sqlExpression": LAB2.FILTER},
                    "action": {"compatibilityLevel": 20, "sqlExpression": None},
                }},
            ]
            for name in LAB2.SUBSCRIPTIONS
        }

    def __call__(self, method, path, body=None, api_version=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if path.endswith("/listWorkflowsConnections"):
            if self.missing:
                raise LAB2.MissingConnectionsFile()
            return {"properties": {"files": {"connections.json": copy.deepcopy(self.connections)}}}
        if path.endswith("/deployWorkflowArtifacts"):
            if set(body["files"]) != {"connections.json"}:
                raise AssertionError("Only the shared connection file may be uploaded.")
            self.connections = copy.deepcopy(body["files"]["connections.json"])
            self.missing = False
            return None
        if path.endswith("/topics/orders/subscriptions"):
            return {"value": [{"name": name} for name in LAB2.SUBSCRIPTIONS]}
        if "/topics/orders/subscriptions/" in path:
            name = path.split("/subscriptions/")[-1].split("/")[0]
            if method == "delete" and path.endswith("/rules/$Default"):
                self.rules[name] = [rule for rule in self.rules[name] if rule["name"] != "$Default"]
                return None
            if method == "get" and path.endswith("/rules"):
                return {"value": copy.deepcopy(self.rules[name])}
        raise AssertionError(f"Unexpected request: {method} {path}")


class ConfigurationTests(unittest.TestCase):
    def run_configuration(self, requests, action="configure"):
        with patch.object(LAB2, "az_json", return_value=SUBSCRIPTION), \
                patch.object(LAB2, "request", side_effect=requests), \
                contextlib.redirect_stdout(io.StringIO()):
            LAB2.configure(action, SITE, NAMESPACE, FQDN)

    def test_configuration_preserves_other_connections_and_is_idempotent(self):
        azure = AzureRequests()
        self.run_configuration(azure)
        connection = azure.connections["serviceProviderConnections"][LAB2.CONNECTION_NAME]
        self.assertEqual(connection["parameterSetName"], "ManagedServiceIdentity")
        self.assertEqual(connection["parameterValues"], {
            "fullyQualifiedNamespace": FQDN, "authProvider": {"Type": "ManagedServiceIdentity"},
        })
        self.assertEqual(connection["serviceProvider"]["id"], "/serviceProviders/serviceBus")
        self.assertEqual(azure.connections["managedApiConnections"], EXISTING["managedApiConnections"])
        self.assertEqual(azure.connections["serviceProviderConnections"]["lab01Cosmos"],
                         EXISTING["serviceProviderConnections"]["lab01Cosmos"])
        self.assertEqual(sum(method == "delete" for method, _, _ in azure.calls), 3)
        before = len(azure.calls)
        self.run_configuration(azure)
        self.assertFalse(any(method == "delete" or path.endswith("/deployWorkflowArtifacts")
                             for method, path, _ in azure.calls[before:]))

    def test_empty_site_connection_can_be_created(self):
        azure = AzureRequests(connections={}, missing=True)
        self.run_configuration(azure)
        self.assertEqual(azure.connections, {
            "serviceProviderConnections": {LAB2.CONNECTION_NAME: LAB2.connection(FQDN)},
        })

    def test_cleanup_does_not_create_a_connection_file_on_an_empty_site(self):
        azure = AzureRequests(connections={}, missing=True)
        self.run_configuration(azure, action="remove")
        self.assertEqual(len(azure.calls), 1)

    def test_remove_preserves_other_artifacts_and_never_changes_rules(self):
        azure = AzureRequests()
        self.run_configuration(azure)
        azure.calls.clear()
        self.run_configuration(azure, action="remove")
        self.assertEqual(azure.connections, EXISTING)
        self.assertFalse(any("/topics/" in path for _, path, _ in azure.calls))
        azure.calls.clear()
        self.run_configuration(azure, action="remove")
        self.assertFalse(any(path.endswith("/deployWorkflowArtifacts") for _, path, _ in azure.calls))

    def test_conflicting_connection_is_rejected_before_any_broker_change(self):
        for action in ("configure", "remove"):
            with self.subTest(action=action):
                azure = AzureRequests(connections={
                    "serviceProviderConnections": {LAB2.CONNECTION_NAME: {"unexpected": "keep"}},
                })
                with self.assertRaisesRegex(ValueError, "different definition"):
                    self.run_configuration(azure, action)
                self.assertEqual(len(azure.calls), 1)

    def test_bad_filter_or_unrelated_rule_prevents_default_deletion(self):
        for rules in [
            [{"name": "$Default", "properties": {}}],
            [{"name": "order-created", "properties": {
                "filterType": "SqlFilter", "sqlFilter": {"sqlExpression": "1=1"},
            }}],
            [{"name": "unexpected", "properties": {}}],
        ]:
            with self.subTest(rules=rules):
                azure = AzureRequests()
                azure.rules["audit"] = rules
                with self.assertRaisesRegex(ValueError, "expected order-created"):
                    self.run_configuration(azure)
                self.assertFalse(any(method == "delete" or path.endswith("/deployWorkflowArtifacts")
                                     for method, path, _ in azure.calls))

    def test_authorization_failure_does_not_become_an_empty_connection_file(self):
        with self.assertRaisesRegex(RuntimeError, "Forbidden"):
            self.run_configuration(lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Forbidden")))

    def test_missing_file_detection_does_not_swallow_other_errors_or_log_values(self):
        for message, exception in [
            ('{"code":"NotFound","message":"File \'connections.json\' not found"}', LAB2.MissingConnectionsFile),
            ('{"code":"NotFound","message":"Site not found"}', RuntimeError),
            ('{"code":"Forbidden","message":"private-value"}', RuntimeError),
        ]:
            with self.subTest(message=message), patch.object(LAB2.subprocess, "run", return_value=
                    subprocess.CompletedProcess([], 1, stdout="", stderr=message)):
                with self.assertRaises(exception) as error:
                    LAB2.request("post", f"{SITE}/listWorkflowsConnections")
                self.assertNotIn("private-value", str(error.exception))
                if "Site not found" in message:
                    self.assertNotIsInstance(error.exception, LAB2.MissingConnectionsFile)

    def test_wrong_namespace_or_subscription_never_writes(self):
        with patch.object(LAB2, "request") as request, \
                patch.object(LAB2, "az_json", return_value="other-subscription"):
            for namespace, fqdn in [(NAMESPACE, FQDN), (NAMESPACE, "other.servicebus.windows.net")]:
                with self.subTest(namespace=namespace, fqdn=fqdn), self.assertRaises(ValueError):
                    LAB2.configure("configure", SITE, namespace, fqdn)
            request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
