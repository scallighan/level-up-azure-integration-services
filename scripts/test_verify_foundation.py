#!/usr/bin/env python3
"""Exercise the readiness gate without provisioning Azure resources."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
ROOT = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/student"
SCRIPT = Path(__file__).with_name("verify-foundation.sh")
IDS = {
    "virtual_network_id": f"{ROOT}/providers/Microsoft.Network/virtualNetworks/vnet",
    "host_storage_id": f"{ROOT}/providers/Microsoft.Storage/storageAccounts/storage",
    "host_storage_identity_id": f"{ROOT}/providers/Microsoft.ManagedIdentity/userAssignedIdentities/host",
    "service_plan_id": f"{ROOT}/providers/Microsoft.Web/serverfarms/plan",
    "logic_app_id": f"{ROOT}/providers/Microsoft.Web/sites/site",
    "cosmos_account_id": f"{ROOT}/providers/Microsoft.DocumentDB/databaseAccounts/cosmos",
    "service_bus_namespace_id": f"{ROOT}/providers/Microsoft.ServiceBus/namespaces/bus",
    "application_insights_id": f"{ROOT}/providers/Microsoft.Insights/components/insights",
    "log_analytics_workspace_id": f"{ROOT}/providers/Microsoft.OperationalInsights/workspaces/logs",
}
HANDOFF = {
    **IDS,
    "resource_group_name": "student",
    "resource_group_created": False,
    "location": "westus",
    "integration_subnet_id": f"{IDS['virtual_network_id']}/subnets/snet-logic-app",
    "private_endpoint_subnet_id": f"{IDS['virtual_network_id']}/subnets/snet-private-endpoints",
    "logic_app_name": "site",
    "logic_app_principal_id": "00000000-0000-0000-0000-000000000002",
    "cosmos_account_name": "cosmos",
    "cosmos_account_endpoint": "https://cosmos.documents.azure.com:443/",
    "cosmos_database_name": "workshop",
    "cosmos_container_name": "items",
    "service_bus_namespace_name": "bus",
    "service_bus_fqdn": "bus.servicebus.windows.net",
}


def azure_response(args):
    if args[:2] == ["account", "show"]:
        return SUBSCRIPTION
    if args[:2] == ["identity", "show"]:
        return "host-principal"
    if args[:3] == ["role", "assignment", "list"]:
        if "--all" in args and "--scope" in args:
            raise AssertionError("Azure CLI rejects --all combined with --scope")
        return [
            {"principalId": "host-principal", "scope": IDS["host_storage_id"],
             "roleDefinitionId": f"/roles/{role}"}
            for role in ["ba92f5b4-2d11-453d-a403-e96b0029c9fe",
                         "974c5e8b-45b9-4653-ba55-5f855dd0fb88",
                         "0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3"]
        ]
    if args[:2] == ["resource", "show"]:
        resource = args[args.index("--ids") + 1]
        responses = {
            IDS["logic_app_id"]: {
                "kind": "functionapp,workflowapp",
                "identity": {
                    "type": "SystemAssigned, UserAssigned",
                    "principalId": HANDOFF["logic_app_principal_id"],
                    "userAssignedIdentities": {IDS["host_storage_identity_id"]: {}},
                },
                "properties": {
                    "serverFarmId": IDS["service_plan_id"],
                    "virtualNetworkSubnetId": HANDOFF["integration_subnet_id"],
                    "httpsOnly": True, "outboundVnetRouting": {"allTraffic": True},
                },
            },
            IDS["service_plan_id"]: {"sku": {"name": "WS1"}, "properties": {"reserved": False}},
            IDS["host_storage_id"]: {
                "name": "storage", "kind": "StorageV2", "sku": {"name": "Standard_LRS"},
                "properties": {
                    "accessTier": "Hot", "supportsHttpsTrafficOnly": True,
                    "minimumTlsVersion": "TLS1_2", "allowBlobPublicAccess": False,
                    "allowSharedKeyAccess": False, "publicNetworkAccess": "Disabled",
                },
            },
            IDS["cosmos_account_id"]: {
                "properties": {
                    "publicNetworkAccess": "Enabled" if os.environ["FAKE_AZ_CASE"] == "public-cosmos" else "Disabled",
                    "disableLocalAuth": True, "capabilities": [{"name": "EnableServerless"}],
                },
            },
            IDS["service_bus_namespace_id"]: {
                "sku": {"name": "Standard"},
                "properties": {"disableLocalAuth": True, "minimumTlsVersion": "1.2",
                               "publicNetworkAccess": "Enabled"},
            },
            IDS["application_insights_id"]: {
                "properties": {"WorkspaceResourceId": IDS["log_analytics_workspace_id"]},
            },
            IDS["log_analytics_workspace_id"]: {"properties": {"retentionInDays": 30}},
        }
        response = responses[resource]
        case = os.environ["FAKE_AZ_CASE"]
        if resource == IDS["logic_app_id"] and case in ["identity-id-casing", "wrong-identity"]:
            identity = IDS["host_storage_identity_id"]
            identity = (
                identity.replace("/resourceGroups/", "/resourcegroups/")
                if case == "identity-id-casing"
                else identity.replace("/student/", "/other-group/")
            )
            response["identity"]["userAssignedIdentities"] = {identity: {}}
        return response
    if args[:3] == ["network", "vnet", "show"]:
        return {
            "addressSpace": {"addressPrefixes": ["172.22.0.0/16"]},
            "subnets": [
                {"name": f"snet-{name}", "defaultOutboundAccess": False,
                 "delegations": [{"serviceName": delegation}] if delegation else []}
                for name, delegation in [
                    ("default", None), ("private-endpoints", None),
                    ("container-apps", "Microsoft.App/environments"),
                    ("logic-app", "Microsoft.Web/serverFarms"),
                ]
            ],
        }
    if args[:4] == ["cosmosdb", "sql", "container", "show"]:
        return {"resource": {"partitionKey": {"paths": ["/id"]}}}
    if args[:5] == ["cosmosdb", "sql", "role", "assignment", "list"]:
        return [{"principalId": HANDOFF["logic_app_principal_id"],
                 "scope": f"{IDS['cosmos_account_id']}/dbs/workshop/colls/items",
                 "roleDefinitionId": "/roles/00000000-0000-0000-0000-000000000002"}]
    if args[:3] == ["network", "private-endpoint", "list"]:
        return [
            {"name": service, "provisioningState": "Succeeded",
             "privateLinkServiceConnections": [{
                 "privateLinkServiceId": IDS["cosmos_account_id" if service == "Sql" else "host_storage_id"],
                 "groupIds": [service],
                 "privateLinkServiceConnectionState": {"status": "Approved"},
             }]}
            for service in ["blob", "queue", "table", "file", "Sql"]
        ]
    if args[:4] == ["network", "private-endpoint", "dns-zone-group", "list"]:
        service = args[args.index("--endpoint-name") + 1]
        zone = "privatelink.documents.azure.com" if service == "Sql" else f"privatelink.{service}.core.windows.net"
        return [{"privateDnsZoneConfigs": [{"privateDnsZoneId": f"{ROOT}/providers/Microsoft.Network/privateDnsZones/{zone}"}]}]
    if args[:5] == ["network", "private-dns", "link", "vnet", "list"]:
        return [{"virtualNetwork": {"id": IDS["virtual_network_id"]},
                 "provisioningState": "Succeeded", "registrationEnabled": False}]
    if args[:5] == ["network", "private-dns", "record-set", "a", "list"]:
        if os.environ["FAKE_AZ_CASE"] == "missing-dns":
            return []
        zone = args[args.index("-z") + 1]
        return [{"name": "cosmos" if "documents" in zone else "storage",
                 "aRecords": [{"ipv4Address": "172.22.2.4"}]}]
    if args[:4] == ["webapp", "config", "appsettings", "list"]:
        if "--resource-group" not in args or "--name" not in args:
            raise AssertionError("App settings require --resource-group and --name")
        if args[args.index("--query") + 1].startswith("length("):
            return 1
        settings = {
            "AzureWebJobsStorage__credential": "managedidentity",
            "AzureWebJobsStorage__managedIdentityResourceId": IDS["host_storage_identity_id"],
            "FUNCTIONS_EXTENSION_VERSION": "~4", "FUNCTIONS_WORKER_RUNTIME": "dotnet",
            "APP_KIND": "workflowApp", "FUNCTIONS_INPROC_NET8_ENABLED": "1",
            "LOGIC_APPS_POWERSHELL_VERSION": "7.4",
            "AzureFunctionsJobHost__extensionBundle__id": "Microsoft.Azure.Functions.ExtensionBundle.Workflows",
            "AzureFunctionsJobHost__extensionBundle__version": "[1.*, 2.0.0)",
        }
        settings.update({
            f"AzureWebJobsStorage__{service}ServiceUri": f"https://storage.{service}.core.windows.net"
            for service in ["blob", "queue", "table"]
        })
        return [{"name": name, "value": value} for name, value in settings.items()]
    raise AssertionError(f"Unexpected Azure command: {args}")


class ReadinessTests(unittest.TestCase):
    def run_check(self, case, handoff=None):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            stub = path / "az"
            stub.write_text(f"#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} \"$@\"\n")
            stub.chmod(0o700)
            fixture = path / "foundation.json"
            fixture.write_text(json.dumps(HANDOFF if handoff is None else handoff))
            return subprocess.run(
                ["bash", str(SCRIPT), str(fixture)], capture_output=True, text=True,
                env={**os.environ, "PATH": f"{path}:{os.environ['PATH']}", "FAKE_AZ_CASE": case},
                check=False,
            )

    def test_ready_foundation_passes(self):
        result = self.run_check("ready")
        self.assertEqual(result.returncode, 0, result.stderr)
        for service in ["blob", "queue", "table", "file", "Sql"]:
            self.assertIn(f"Checking {service} private endpoint and DNS...", result.stdout)
        self.assertIn("Checking Logic App telemetry setting...", result.stdout)
        self.assertIn("Foundation provisioning checks passed.", result.stdout)

    def test_public_cosmos_is_rejected(self):
        result = self.run_check("public-cosmos")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private serverless Cosmos", result.stderr)

    def test_identity_resource_id_casing_is_accepted(self):
        result = self.run_check("identity-id-casing")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_different_host_identity_is_rejected(self):
        result = self.run_check("wrong-identity")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("dual identities", result.stderr)

    def test_missing_dns_is_rejected(self):
        result = self.run_check("missing-dns")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("private DNS A record", result.stderr)
        self.assertIn("Checking blob private endpoint and DNS...", result.stdout)
        self.assertNotIn("Checking queue private endpoint and DNS...", result.stdout)
        self.assertNotIn("Foundation provisioning checks passed.", result.stdout)

    def test_incomplete_handoff_is_rejected_before_azure(self):
        result = self.run_check("unexpected", {"resource_group_name": "student"})
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("every non-secret foundation reference", result.stderr)

    def test_other_subscription_is_rejected(self):
        handoff = {**HANDOFF, "logic_app_id": IDS["logic_app_id"].replace(SUBSCRIPTION, "another-subscription")}
        result = self.run_check("unexpected", handoff)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("select the subscription and group", result.stderr)


if __name__ == "__main__":
    if "FAKE_AZ_CASE" in os.environ:
        response = azure_response(sys.argv[1:])
        print(response if isinstance(response, str) else json.dumps(response))
    else:
        unittest.main()
