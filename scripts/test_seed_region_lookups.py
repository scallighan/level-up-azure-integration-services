"""Test private-network region seeding without deploying Azure resources."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("seed-region-lookups.py")
SPEC = importlib.util.spec_from_file_location("seed_region_lookups", SCRIPT)
SEED = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(SEED)
SUBSCRIPTION = "00000000-0000-0000-0000-000000000001"
GROUP_ID = f"/subscriptions/{SUBSCRIPTION}/resourceGroups/student"
SITE_ID = f"{GROUP_ID}/providers/Microsoft.Web/sites/site"
FOUNDATION = {
    "logic_app_id": SITE_ID,
    "resource_group_name": "student",
    "cosmos_account_id": f"{GROUP_ID}/providers/Microsoft.DocumentDB/databaseAccounts/cosmos",
    "cosmos_database_name": "workshop",
    "cosmos_container_name": "items",
}
REGIONS = json.loads(SEED.REGIONS.read_text())


class AzureRequests:
    def __init__(self, status="Succeeded", connections=None):
        self.status = status
        self.connections = {} if connections is None else connections
        self.calls = []
        self.workflow_name = None

    def __call__(self, method, path, body=None):
        self.calls.append((method, path, copy.deepcopy(body)))
        if path.endswith("/listWorkflowsConnections"):
            return {"properties": {"files": {"connections.json": copy.deepcopy(self.connections)}}}
        if path.endswith("/deployWorkflowArtifacts"):
            if "files" in body:
                self.workflow_name = next(
                    name.split("/")[0] for name in body["files"] if name.endswith("/workflow.json")
                )
            return None
        if path.endswith("/workflows"):
            return {"value": [{
                "name": f"site/{self.workflow_name}",
                "properties": {"health": {"state": "Healthy"}},
            }]}
        if path.endswith("/triggers/seed/run") or path.endswith("/runs/seed-run/cancel"):
            return None
        if path.endswith("/runs?$top=1"):
            return {"value": [{"name": "seed-run", "properties": {"status": self.status}}]}
        raise AssertionError(f"Unexpected Azure request: {method} {path}")


class SeedTests(unittest.TestCase):
    def run_seed(self, requests, output=None):
        if output is None:
            output = io.StringIO()
        with patch.object(SEED, "az_json", return_value=SUBSCRIPTION), \
                patch.object(SEED, "request", side_effect=requests), \
                contextlib.redirect_stdout(output):
            SEED.seed(FOUNDATION, copy.deepcopy(REGIONS))
        return output.getvalue()

    def test_seeding_preserves_connections_and_removes_only_its_helper(self):
        existing = {
            "managedApiConnections": {"otherApi": {"connection": {"id": "existing"}}},
            "serviceProviderConnections": {"otherLab": {"displayName": "Keep me"}},
        }
        requests = AzureRequests(connections=existing)
        output = self.run_seed(requests)
        deployments = [body for _, path, body in requests.calls if path.endswith("/deployWorkflowArtifacts")]
        files = deployments[0]["files"]
        self.assertEqual(set(files), {"connections.json", f"{requests.workflow_name}/workflow.json"})
        self.assertEqual(files["connections.json"]["managedApiConnections"], existing["managedApiConnections"])
        self.assertEqual(
            files["connections.json"]["serviceProviderConnections"]["otherLab"],
            existing["serviceProviderConnections"]["otherLab"],
        )
        workflow = files[f"{requests.workflow_name}/workflow.json"]["definition"]
        self.assertEqual(workflow["parameters"]["regionData"]["defaultValue"], REGIONS)
        upsert = workflow["actions"]["Seed_regions"]["actions"]["Upsert_region"]["inputs"]
        self.assertTrue(upsert["parameters"]["isUpsert"])
        self.assertEqual(upsert["parameters"]["partitionKey"], "@items('Seed_regions')?['id']")
        self.assertEqual(deployments[1], {
            "filesToDelete": [f"{requests.workflow_name}/workflow.json", f"{requests.workflow_name}/"]
        })
        self.assertIn("Seeded 6 region lookups.", output)

    def test_failed_seed_is_not_reported_as_success_and_still_removes_helper(self):
        requests = AzureRequests(status="Failed")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaisesRegex(RuntimeError, "finished with Failed"):
            self.run_seed(requests, output)
        self.assertIn("filesToDelete", requests.calls[-1][2])
        self.assertNotIn("Seeded 6", output.getvalue())

    def test_conflicting_connection_stops_before_deployment(self):
        requests = AzureRequests(connections={"serviceProviderConnections": {
            "lab01Cosmos": {"parameterSetName": "connectionString"}
        }})
        with self.assertRaisesRegex(ValueError, "different settings"):
            self.run_seed(requests)
        self.assertFalse(any(path.endswith("/deployWorkflowArtifacts") for _, path, _ in requests.calls))

    def test_first_run_accepts_only_a_missing_connection_file(self):
        missing = RuntimeError(
            'ERROR: Not Found({"error":{"code":"NotFound",'
            '"message":"Error retrieving connections. \'C:\\\\home\\\\connections.json\' not found."}})'
        )
        with patch.object(SEED, "request", side_effect=missing), \
                contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(SEED.read_connections(SITE_ID), {})
        for error in [
            RuntimeError('{"error":{"code":"AuthorizationFailed"}}'),
            RuntimeError('{"error":{"code":"NotFound","message":"Site not found"}}'),
        ]:
            with self.subTest(error=str(error)), patch.object(SEED, "request", side_effect=error), \
                    self.assertRaises(RuntimeError):
                SEED.read_connections(SITE_ID)

    def test_wrong_subscription_and_unsafe_seed_ids_stop_before_writes(self):
        with patch.object(SEED, "az_json", return_value="other-subscription"), \
                patch.object(SEED, "request") as request, \
                self.assertRaisesRegex(ValueError, "Select the Azure subscription"):
            SEED.seed(FOUNDATION, REGIONS)
        request.assert_not_called()
        invalid = copy.deepcopy(REGIONS)
        invalid[0]["id"] = "unrelated-document"
        with patch.object(SEED, "az_json") as azure, \
                self.assertRaisesRegex(ValueError, "Seed IDs"):
            SEED.seed(FOUNDATION, invalid)
        azure.assert_not_called()

    def test_timeout_cancels_the_running_seed(self):
        requests = AzureRequests(status="Running")
        with patch.object(SEED, "request", side_effect=requests), \
                patch.object(SEED.time, "monotonic", side_effect=[0, 1, 301]), \
                patch.object(SEED.time, "sleep"), contextlib.redirect_stdout(io.StringIO()), \
                self.assertRaises(TimeoutError):
            SEED.wait_for_completion("/runtime/seed", "seed")
        self.assertEqual(requests.calls[-1][:2], ("post", "/runtime/seed/runs/seed-run/cancel"))

    def test_seed_rejects_missing_or_empty_region_labels_before_azure(self):
        for field in ["displayName", "physicalLocation"]:
            for value in [None, "", "   "]:
                with self.subTest(field=field, value=value):
                    invalid = copy.deepcopy(REGIONS)
                    if value is None:
                        del invalid[0][field]
                    else:
                        invalid[0][field] = value
                    with patch.object(SEED, "az_json") as azure, self.assertRaises(ValueError):
                        SEED.seed(FOUNDATION, invalid)
                    azure.assert_not_called()

    def test_success_fixtures_match_the_seeded_lookup_data(self):
        contracts = SEED.REGIONS.parent
        by_name = {region["programmaticName"]: region for region in REGIONS}
        cases = json.loads((contracts / "test-cases.json").read_text())
        cases.append({
            "name": "README sample", "status": 200,
            "request": json.loads((contracts / "sample-request.json").read_text()),
            "response": json.loads((contracts / "sample-response.json").read_text()),
        })
        for case in cases:
            if case["status"] != 200:
                continue
            with self.subTest(case=case["name"]):
                name = case["request"]["programmaticName"]
                self.assertEqual(case["response"], {
                    **case["request"],
                    "regionDisplayName": by_name[name]["displayName"],
                    "physicalLocation": by_name[name]["physicalLocation"],
                })


if __name__ == "__main__":
    unittest.main()
