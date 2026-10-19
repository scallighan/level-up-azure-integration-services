"""Test Lab 1 preparation without deploying Azure resources."""

import contextlib
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).with_name("prepare-lab1.py")
SPEC = importlib.util.spec_from_file_location("prepare_lab1", SCRIPT)
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
SUPPORT_TIERS = json.loads(SEED.SUPPORT_TIERS.read_text())
DOCUMENTS = REGIONS + SUPPORT_TIERS


class AzureRequests:
    def __init__(self, status="Succeeded", connections=None, runtime_errors=(), trigger_errors=()):
        self.status = status
        self.connections = {} if connections is None else connections
        self.calls = []
        self.workflow_name = None
        self.runtime_errors = list(runtime_errors)
        self.trigger_errors = list(trigger_errors)

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
        if path.endswith("/triggers/seed"):
            if self.runtime_errors:
                raise self.runtime_errors.pop(0)
            return {"properties": {"state": "Enabled"}}
        if path.endswith("/triggers/seed/run"):
            if self.trigger_errors:
                raise self.trigger_errors.pop(0)
            return None
        if path.endswith("/runs/seed-run/cancel"):
            return None
        if path.endswith("/runs?$top=1"):
            return {"value": [{"name": "seed-run", "properties": {"status": self.status}}]}
        if path.endswith("/runs/seed-run/actions"):
            return {"value": [{
                "name": "Upsert_lab01_region_westus",
                "properties": {
                    "status": "Failed", "code": "BadRequest",
                    "error": {"code": "InvalidTemplate", "message": "private action payload"},
                    "inputs": {"private": "must not appear"},
                },
            }]}
        raise AssertionError(f"Unexpected Azure request: {method} {path}")


class SeedTests(unittest.TestCase):
    def run_seed(self, requests, output=None):
        if output is None:
            output = io.StringIO()
        with patch.object(SEED, "az_json", return_value=SUBSCRIPTION), \
                patch.object(SEED, "request", side_effect=requests), \
                contextlib.redirect_stdout(output):
            SEED.seed(FOUNDATION, copy.deepcopy(DOCUMENTS))
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
        connection = files["connections.json"]["serviceProviderConnections"]["lab01Cosmos"]
        self.assertEqual(connection["parameterValues"]["authProvider"], {"Type": "ManagedServiceIdentity"})
        self.assertNotIn("authProvider", connection)
        workflow = files[f"{requests.workflow_name}/workflow.json"]["definition"]
        actions = workflow["actions"]
        self.assertEqual(set(actions), {f"Upsert_{doc['id'].replace('-', '_')}" for doc in DOCUMENTS})
        previous = None
        for document in DOCUMENTS:
            name = f"Upsert_{document['id'].replace('-', '_')}"
            action = actions[name]
            upsert = action["inputs"]["parameters"]
            self.assertEqual(json.loads(upsert["item"]), document)
            self.assertEqual(upsert["partitionKey"], document["id"])
            self.assertTrue(upsert["isUpsert"])
            self.assertEqual(action["runAfter"], {previous: ["Succeeded"]} if previous else {})
            previous = name
        self.assertEqual(deployments[1], {
            "filesToDelete": [f"{requests.workflow_name}/workflow.json", f"{requests.workflow_name}/"]
        })
        self.assertIn("Seeded 9 lookup records.", output)

    def test_failed_seed_is_not_reported_as_success_and_still_removes_helper(self):
        requests = AzureRequests(status="Failed")
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaisesRegex(RuntimeError, "finished with Failed") as failure:
            self.run_seed(requests, output)
        self.assertIn("Upsert_lab01_region_westus (InvalidTemplate)", str(failure.exception))
        self.assertNotIn("private action payload", str(failure.exception))
        self.assertNotIn("must not appear", str(failure.exception))
        self.assertNotIn("system-identity grant", str(failure.exception))
        self.assertIn("filesToDelete", requests.calls[-1][2])
        self.assertNotIn("Seeded ", output.getvalue())

    def test_diagnostic_query_failure_preserves_run_failure_and_cleanup(self):
        requests = AzureRequests(status="Failed")

        def fail_diagnostics(method, path, body=None):
            if path.endswith("/runs/seed-run/actions"):
                raise RuntimeError("diagnostics denied")
            return requests(method, path, body)

        with self.assertRaisesRegex(RuntimeError, "finished with Failed.*diagnostics denied"):
            self.run_seed(fail_diagnostics)
        self.assertIn("filesToDelete", requests.calls[-1][2])

    def test_debug_retains_and_disables_successful_and_failed_workflows(self):
        for status in ["Succeeded", "Failed"]:
            with self.subTest(status=status):
                requests = AzureRequests(status=status)
                output = io.StringIO()
                with patch.object(SEED, "az_json", side_effect=[SUBSCRIPTION, [], ["Disabled"]]) as azure, \
                        patch.object(SEED, "request", side_effect=requests), \
                        contextlib.redirect_stdout(output):
                    if status == "Failed":
                        with self.assertRaisesRegex(RuntimeError, "finished with Failed"):
                            SEED.seed(FOUNDATION, DOCUMENTS, keep_workflow=True)
                    else:
                        SEED.seed(FOUNDATION, DOCUMENTS, keep_workflow=True)
                self.assertFalse(any(body and "filesToDelete" in body for _, _, body in requests.calls))
                arguments = azure.call_args_list[1].args[0]
                self.assertEqual(arguments[:4], ["webapp", "config", "appsettings", "set"])
                self.assertEqual(
                    arguments[arguments.index("--settings") + 1],
                    f"Workflows.{requests.workflow_name}.FlowState=Disabled",
                )
                self.assertEqual(arguments[arguments.index("--name") + 1], "site")
                self.assertEqual(arguments[arguments.index("--resource-group") + 1], "student")
                self.assertIn(f"Retained {requests.workflow_name} (disabled)", output.getvalue())

    def test_debug_disable_failures_are_reported_without_hiding_seed_failure(self):
        for response in [RuntimeError("disable denied"), []]:
            with self.subTest(response=response):
                requests = AzureRequests(status="Failed")
                output = io.StringIO()
                responses = (
                    [SUBSCRIPTION, response] if isinstance(response, RuntimeError)
                    else [SUBSCRIPTION, [], response]
                )
                with patch.object(SEED, "az_json", side_effect=responses), \
                        patch.object(SEED, "request", side_effect=requests), \
                        contextlib.redirect_stdout(output), \
                        self.assertRaisesRegex(RuntimeError, r"finished with Failed[\s\S]*Disabling retained workflow"):
                    SEED.seed(FOUNDATION, DOCUMENTS, keep_workflow=True)
                self.assertNotIn("(disabled)", output.getvalue())
                self.assertFalse(any(body and "filesToDelete" in body for _, _, body in requests.calls))

    def test_cli_passes_debug_flag_to_preparation(self):
        with patch.object(SEED.sys, "argv", ["prepare-lab1.py", "foundation.json", "--keep-workflow"]), \
                patch.object(Path, "read_text", side_effect=[
                    json.dumps(REGIONS), json.dumps(SUPPORT_TIERS), json.dumps(FOUNDATION)
                ]), \
                patch.object(SEED, "seed") as seed:
            self.assertEqual(SEED.main(), 0)
        seed.assert_called_once_with(FOUNDATION, DOCUMENTS, keep_workflow=True)

    def test_cli_rejects_invalid_seed_arrays_without_azure(self):
        for invalid in [{}, [], None]:
            with self.subTest(invalid=invalid), \
                    patch.object(SEED.sys, "argv", ["prepare-lab1.py"]), \
                    patch.object(Path, "read_text", side_effect=[
                        json.dumps(REGIONS), json.dumps(invalid)
                    ]), patch.object(SEED, "az_json") as azure, \
                    contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(SEED.main(), 1)
                self.assertIn("nonempty JSON array", error.getvalue())
            azure.assert_not_called()

    def test_schedule_is_dormant_without_exceeding_the_runtime_future_limit(self):
        before = datetime.now(timezone.utc)
        workflow = SEED.seed_workflow(DOCUMENTS)
        start = workflow["definition"]["triggers"]["seed"]["recurrence"]["startTime"]
        scheduled = datetime.fromisoformat(start.replace("Z", "+00:00"))
        self.assertGreater(scheduled, before)
        self.assertLess(scheduled, before + timedelta(days=2))

    def test_healthy_artifact_waits_for_runtime_registration_before_starting(self):
        missing = RuntimeError('{"error":{"code":"WorkflowNotFound"}}')
        requests = AzureRequests(runtime_errors=[missing, missing])
        with patch.object(SEED.time, "sleep") as sleep:
            output = self.run_seed(requests)
        self.assertEqual(sleep.call_count, 2)
        starts = [path for method, path, _ in requests.calls
                  if method == "post" and path.endswith("/triggers/seed/run")]
        self.assertEqual(len(starts), 1)
        self.assertIn("register in the runtime", output)
        self.assertIn("Seeded 9 lookup records.", output)

    def test_trigger_retries_only_explicit_readiness_errors(self):
        missing = RuntimeError('{"error":{"code":"WorkflowNotFound"}}')
        not_ready = RuntimeError('ERROR: Conflict({"error":{"code":"WorkflowTriggerNotReady"}})')
        requests = AzureRequests(trigger_errors=[missing, not_ready])
        with patch.object(SEED.time, "sleep") as sleep:
            self.run_seed(requests)
        self.assertEqual(sleep.call_count, 2)
        starts = [path for _, path, _ in requests.calls if path.endswith("/triggers/seed/run")]
        self.assertEqual(len(starts), 3)
        for code in ["AuthorizationFailed", "TriggerNotFound", "Conflict"]:
            requests = AzureRequests(trigger_errors=[RuntimeError(f'{{"code":"{code}"}}')])
            with self.subTest(code=code), patch.object(SEED.time, "sleep") as sleep, \
                    self.assertRaisesRegex(RuntimeError, code):
                self.run_seed(requests)
            sleep.assert_not_called()
            self.assertIn("filesToDelete", requests.calls[-1][2])

    def test_trigger_not_ready_times_out_with_diagnostics_and_removes_helper(self):
        not_ready = RuntimeError('{"error":{"code":"WorkflowTriggerNotReady"}}')
        requests = AzureRequests(trigger_errors=[not_ready])
        output = io.StringIO()
        with patch.object(SEED.time, "monotonic", side_effect=[0, 1, 181]), \
                patch.object(SEED.time, "sleep"), \
                self.assertRaisesRegex(TimeoutError, "WorkflowTriggerNotReady"):
            self.run_seed(requests, output)
        self.assertIn("filesToDelete", requests.calls[-1][2])
        self.assertNotIn("Seeded ", output.getvalue())

    def test_missing_runtime_times_out_with_diagnostics_and_removes_helper(self):
        missing = RuntimeError('{"error":{"code":"WorkflowNotFound"}}')
        requests = AzureRequests(runtime_errors=[missing])
        with patch.object(SEED.time, "monotonic", side_effect=[0, 1, 181]), \
                patch.object(SEED.time, "sleep"), \
                self.assertRaisesRegex(TimeoutError, "workflow validation errors.*WorkflowNotFound"):
            self.run_seed(requests)
        self.assertFalse(any(path.endswith("/triggers/seed/run") for _, path, _ in requests.calls))
        self.assertIn("filesToDelete", requests.calls[-1][2])

    def test_azure_failure_identifies_the_operation(self):
        with patch.object(SEED, "az_json", side_effect=RuntimeError("AuthorizationFailed")), \
                self.assertRaisesRegex(RuntimeError, "POST /site/workflow/triggers/seed/run failed"):
            SEED.request("post", "/site/workflow/triggers/seed/run")

    def test_cleanup_failure_does_not_hide_the_original_error(self):
        requests = AzureRequests(status="Failed")

        def fail_cleanup(method, path, body=None):
            if body is not None and "filesToDelete" in body:
                raise RuntimeError("cleanup denied")
            return requests(method, path, body)

        with self.assertRaisesRegex(RuntimeError, r"finished with Failed[\s\S]*cleanup denied"):
            self.run_seed(fail_cleanup)

    def test_conflicting_connection_stops_before_deployment(self):
        legacy = {
            "displayName": "Lab 1 region lookup",
            "parameterSetName": "ManagedServiceIdentity",
            "parameterValues": {"accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')"},
            "serviceProvider": {"id": "/serviceProviders/AzureCosmosDB"},
            "authProvider": {"Type": "ManagedServiceIdentity"},
        }
        different_endpoint = copy.deepcopy(legacy)
        different_endpoint["parameterValues"]["accountURI"] = "https://other-account.documents.azure.com"
        different_identity = copy.deepcopy(legacy)
        different_identity["authProvider"]["Identity"] = "/userAssignedIdentities/other"
        for connection in [
            {"parameterSetName": "connectionString"}, different_endpoint, different_identity
        ]:
            with self.subTest(connection=connection):
                requests = AzureRequests(connections={"serviceProviderConnections": {
                    "lab01Cosmos": connection
                }})
                with self.assertRaisesRegex(ValueError, "different settings"):
                    self.run_seed(requests)
                self.assertFalse(any(path.endswith("/deployWorkflowArtifacts") for _, path, _ in requests.calls))

    def test_previous_helper_connection_is_repaired_without_changing_other_connections(self):
        previous = {
            "displayName": "Lab 1 region lookup",
            "parameterSetName": "ManagedServiceIdentity",
            "parameterValues": {"accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')"},
            "serviceProvider": {"id": "/serviceProviders/AzureCosmosDB"},
            "authProvider": {"Type": "ManagedServiceIdentity"},
        }
        other = {"displayName": "Other lab", "parameterValues": {"keep": "unchanged"}}
        requests = AzureRequests(connections={
            "serviceProviderConnections": {"lab01Cosmos": previous, "otherLab": other}
        })
        output = self.run_seed(requests)
        deployment = next(body for _, _, body in requests.calls if body and "files" in body)
        connections = deployment["files"]["connections.json"]["serviceProviderConnections"]
        repaired = connections["lab01Cosmos"]
        self.assertNotIn("authProvider", repaired)
        self.assertEqual(repaired["parameterValues"], {
            "accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')",
            "authProvider": {"Type": "ManagedServiceIdentity"},
        })
        self.assertEqual(connections["otherLab"], other)
        self.assertIn("Repairing lab01Cosmos", output)

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
            SEED.seed(FOUNDATION, DOCUMENTS)
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

    def test_seed_rejects_invalid_support_records_before_azure(self):
        for field, value in [
            ("id", "unrelated-document"), ("id", "lab01-region-standard"),
            ("supportTier", "Standard"), ("displayName", ""), ("displayName", "   "),
            ("responseTimeHours", 0), ("responseTimeHours", True),
            ("responseTimeHours", "8"), ("responseTimeHours", 1.5),
        ]:
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(DOCUMENTS)
                invalid[-1][field] = value
                with patch.object(SEED, "az_json") as azure, self.assertRaises(ValueError):
                    SEED.seed(FOUNDATION, invalid)
                azure.assert_not_called()
        for invalid in [
            DOCUMENTS + [SUPPORT_TIERS[0]],
            [*REGIONS, {key: value for key, value in SUPPORT_TIERS[0].items() if key != "supportTier"}],
        ]:
            with patch.object(SEED, "az_json") as azure, self.assertRaises(ValueError):
                SEED.seed(FOUNDATION, invalid)
            azure.assert_not_called()

    def test_success_fixtures_match_the_seeded_lookup_data(self):
        contracts = SEED.REGIONS.parent
        by_name = {region["programmaticName"]: region for region in REGIONS}
        by_tier = {tier["supportTier"]: tier for tier in SUPPORT_TIERS}
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
                tier = case["request"]["supportTier"]
                self.assertNotIn("regionDisplayName", case["request"])
                self.assertNotIn("physicalLocation", case["request"])
                self.assertEqual(case["response"], {
                    **case["request"],
                    "regionDisplayName": by_name[name]["displayName"],
                    "physicalLocation": by_name[name]["physicalLocation"],
                    "supportTierDisplayName": by_tier[tier]["displayName"],
                    "responseTimeHours": by_tier[tier]["responseTimeHours"],
                })


if __name__ == "__main__":
    unittest.main()
