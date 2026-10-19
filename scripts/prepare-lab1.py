#!/usr/bin/env python3
"""Prepare Lab 1 lookup data and its private Cosmos connection."""

import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import uuid


ROOT = Path(__file__).resolve().parent.parent
REGIONS = ROOT / "labs/01-crud-integration/contracts/regions.json"
SUPPORT_TIERS = REGIONS.with_name("support-tiers.json")
API_VERSION = "2025-03-01"
CONNECTION_NAME = "lab01Cosmos"
CONNECTION = {
    "displayName": "Lab 1 region lookup",
    "parameterSetName": "ManagedServiceIdentity",
    "parameterValues": {
        "accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')",
        "authProvider": {"Type": "ManagedServiceIdentity"},
    },
    "serviceProvider": {"id": "/serviceProviders/AzureCosmosDB"},
}


def az_json(arguments, body=None):
    with tempfile.TemporaryDirectory(prefix="lab01-seed-") as directory:
        command = ["az", *arguments, "--output", "json", "--only-show-errors"]
        if body is not None:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(body))
            command += ["--body", f"@{path}"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=90)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "Azure CLI failed without an error message.")
    return json.loads(result.stdout) if result.stdout.strip() else None


def request(method, path, body=None):
    separator = "&" if "?" in path else "?"
    try:
        return az_json(
            ["rest", "--method", method, "--url",
             f"https://management.azure.com{path}{separator}api-version={API_VERSION}"],
            body,
        )
    except RuntimeError as error:
        raise RuntimeError(f"{method.upper()} {path} failed: {error}") from error


def has_error_code(error, code):
    return re.search(r'"code"\s*:\s*"' + re.escape(code) + r'"', str(error)) is not None


def validate_inputs(foundation, documents):
    if not isinstance(foundation, dict):
        raise ValueError("The foundation handoff must be a JSON object.")
    site_id = foundation.get("logic_app_id", "")
    if not isinstance(site_id, str) or not isinstance(foundation.get("resource_group_name"), str):
        raise ValueError("The handoff needs string site and resource-group references.")
    match = re.fullmatch(
        r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/Microsoft.Web/sites/([^/]+)",
        site_id, re.IGNORECASE,
    )
    if not match or match[2].casefold() != foundation.get("resource_group_name", "").casefold():
        raise ValueError("The handoff must identify the existing Lab 0 site and parent group.")
    cosmos_id = foundation.get("cosmos_account_id", "")
    expected_prefix = (
        f"/subscriptions/{match[1]}/resourceGroups/{match[2]}"
        "/providers/Microsoft.DocumentDB/databaseAccounts/"
    )
    if not isinstance(cosmos_id, str) or not re.fullmatch(
        re.escape(expected_prefix) + r"[^/]+", cosmos_id, re.IGNORECASE
    ):
        raise ValueError("The Cosmos account must be in the handoff's subscription and group.")
    if (foundation.get("cosmos_database_name"), foundation.get("cosmos_container_name")) != (
        "workshop", "items"
    ):
        raise ValueError("Lab 1 requires the Lab 0 workshop/items container.")
    if not isinstance(documents, list) or not documents:
        raise ValueError("The seed data must be a nonempty JSON array.")
    ids = set()
    for document in documents:
        if not isinstance(document, dict):
            raise ValueError("Each seed document must be an object.")
        if set(document) == {"id", "programmaticName", "displayName", "physicalLocation"}:
            key, prefix = "programmaticName", "lab01-region-"
            text_fields = ["displayName", "physicalLocation"]
        elif set(document) == {"id", "supportTier", "displayName", "responseTimeHours"}:
            key, prefix = "supportTier", "lab01-support-"
            text_fields = ["displayName"]
            hours = document["responseTimeHours"]
            if type(hours) is not int or hours < 1:
                raise ValueError("Seed responseTimeHours must be a positive integer.")
        else:
            raise ValueError("Seed documents must match the region or support-tier shape.")
        name = document[key]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]{1,39}", name):
            raise ValueError("Seed lookup keys must match the API contract.")
        if document["id"] != f"{prefix}{name}" or document["id"] in ids:
            raise ValueError("Seed IDs must be unique and match their lab01-region- or lab01-support- key.")
        for field in text_fields:
            if not isinstance(document[field], str) or not document[field].strip():
                raise ValueError(f"Each seeded {field} must be a nonempty string.")
        ids.add(document["id"])
    return match[1]


def read_connections(site_id):
    try:
        result = request("post", f"{site_id}/listWorkflowsConnections")
    except RuntimeError as error:
        # A new foundation has no connections.json until its first workflow.
        message = str(error)
        if not has_error_code(error, "NotFound") or "connections.json' not found" not in message:
            raise
        print("No connections.json yet; creating the Lab 1 connection.", flush=True)
        return {}
    connections = result["properties"]["files"]["connections.json"]
    if not isinstance(connections, dict):
        raise ValueError("Azure returned an invalid connections.json; nothing was changed.")
    return connections


def seed_workflow(documents):
    actions = {}
    previous_action = None
    for document in documents:
        action_name = f"Upsert_{document['id'].replace('-', '_')}"
        actions[action_name] = {
            "type": "ServiceProvider",
            "inputs": {
                "parameters": {
                    "databaseId": "workshop", "containerId": "items",
                    "item": json.dumps(document),
                    "partitionKey": document["id"],
                    "isUpsert": True,
                },
                "serviceProviderConfiguration": {
                    "connectionName": CONNECTION_NAME,
                    "operationId": "CreateOrUpdateDocument",
                    "serviceProviderId": "/serviceProviders/AzureCosmosDB",
                },
                "retryPolicy": {"type": "none"},
            },
            "runtimeConfiguration": {
                "secureData": {"properties": ["inputs", "outputs"]}
            },
            "runAfter": {previous_action: ["Succeeded"]} if previous_action else {},
        }
        previous_action = action_name
    # Keep the schedule dormant; the script starts the trigger through Azure ARM.
    start_time = (datetime.now(timezone.utc) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "kind": "Stateful",
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "triggers": {
                "seed": {
                    "type": "Recurrence",
                    "recurrence": {
                        "frequency": "Day", "interval": 1,
                        "startTime": start_time,
                    },
                }
            },
            "actions": actions,
            "outputs": {},
        },
    }


def start_seed_workflow(site_id, name, runtime_path):
    deadline = time.monotonic() + 180
    last_error = None
    while time.monotonic() < deadline:
        workflows = request("get", f"{site_id}/workflows")["value"]
        for workflow in workflows:
            if workflow["name"].split("/")[-1] != name:
                continue
            health = workflow["properties"]["health"]["state"]
            if health == "Healthy":
                try:
                    request("get", f"{runtime_path}/triggers/seed")
                    request("post", f"{runtime_path}/triggers/seed/run")
                    return
                except RuntimeError as error:
                    if not any(has_error_code(error, code) for code in (
                        "WorkflowNotFound", "WorkflowTriggerNotReady"
                    )):
                        raise
                    last_error = error
            if health == "Unhealthy":
                raise RuntimeError(f"Seed workflow {name} is unhealthy; check runtime validation logs.")
        print(
            "Waiting for the temporary workflow to register in the runtime and its trigger to become ready...",
            flush=True,
        )
        time.sleep(5)
    detail = f" Last runtime error: {last_error}" if last_error else ""
    raise TimeoutError(
        f"Seed workflow {name} was not runnable within three minutes. "
        f"Check Application Insights for workflow validation errors.{detail}"
    )


def wait_for_completion(runtime_path, name):
    deadline = time.monotonic() + 300
    run = None
    while time.monotonic() < deadline:
        runs = request("get", f"{runtime_path}/runs?$top=1")["value"]
        if runs:
            run = runs[0]
            status = run["properties"]["status"]
            if status == "Succeeded":
                return
            if status not in {"Running", "Waiting", "Accepted"}:
                message = f"Seed workflow {name}, run {run['name']}, finished with {status}."
                try:
                    actions = request("get", f"{runtime_path}/runs/{run['name']}/actions")["value"]
                except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
                    raise RuntimeError(f"{message} Could not read action diagnostics: {error}") from error
                failures = []
                for action in actions:
                    properties = action["properties"]
                    if properties["status"] not in {"Failed", "TimedOut"}:
                        continue
                    error = properties.get("error")
                    code = error.get("code") if isinstance(error, dict) else None
                    code = code or properties.get("code") or "no error code returned"
                    failures.append(f"{action['name']} ({code})")
                detail = ", ".join(failures) if failures else "no failed action details returned"
                raise RuntimeError(
                    f"{message} Failed actions: {detail}."
                )
        print("Waiting for Cosmos lookup upserts to finish...", flush=True)
        time.sleep(5)
    if run:
        request("post", f"{runtime_path}/runs/{run['name']}/cancel")
    raise TimeoutError(f"Seed workflow {name} did not finish within five minutes.")


def seed(foundation, documents, keep_workflow=False):
    subscription = validate_inputs(foundation, documents)
    active_subscription = az_json(["account", "show", "--query", "id"])
    if not isinstance(active_subscription, str) or active_subscription.casefold() != subscription.casefold():
        raise ValueError("Select the Azure subscription recorded in foundation.deployment.json.")
    site_id = foundation["logic_app_id"]
    connections = read_connections(site_id)
    providers = connections.setdefault("serviceProviderConnections", {})
    if not isinstance(providers, dict):
        raise ValueError("The site's serviceProviderConnections must be an object.")
    # Only repair the exact connection shape written by older versions of this helper.
    legacy_connection = {
        **CONNECTION,
        "parameterValues": {"accountURI": CONNECTION["parameterValues"]["accountURI"]},
        "authProvider": CONNECTION["parameterValues"]["authProvider"],
    }
    if CONNECTION_NAME in providers and providers[CONNECTION_NAME] not in (CONNECTION, legacy_connection):
        raise ValueError("lab01Cosmos already has different settings; review it before seeding.")
    if providers.get(CONNECTION_NAME) == legacy_connection:
        print("Repairing lab01Cosmos: moving managed-identity authProvider into parameterValues.", flush=True)
    providers[CONNECTION_NAME] = CONNECTION
    name = f"lab01-seed-{uuid.uuid4().hex[:12]}"
    runtime_path = f"{site_id}/hostruntime/runtime/webhooks/workflow/api/management/workflows/{name}"
    try:
        print(f"Deploying temporary seed workflow {name}...", flush=True)
        request("post", f"{site_id}/deployWorkflowArtifacts", {
            "files": {
                "connections.json": connections,
                f"{name}/workflow.json": seed_workflow(documents),
            }
        })
        start_seed_workflow(site_id, name, runtime_path)
        print(f"Seeding {len(documents)} lookup records through the private Cosmos connection...", flush=True)
        wait_for_completion(runtime_path, name)
    finally:
        failure = sys.exc_info()[1]
        if keep_workflow:
            print(f"Keeping seed workflow {name}; disabling it to prevent scheduled runs...", flush=True)
        else:
            print(f"Removing temporary workflow {name}...", flush=True)
        try:
            if keep_workflow:
                setting = f"Workflows.{name}.FlowState"
                target = [
                    "--resource-group", foundation["resource_group_name"],
                    "--name", site_id.rsplit("/", 1)[-1],
                ]
                az_json([
                    "webapp", "config", "appsettings", "set", *target,
                    "--settings", f"{setting}=Disabled", "--query", "[].name",
                ])
                state = az_json([
                    "webapp", "config", "appsettings", "list", *target,
                    "--query", f"[?name=='{setting}'].value",
                ])
                if state != ["Disabled"]:
                    raise RuntimeError(f"Could not verify {setting}=Disabled; check it before leaving the workflow.")
                print(f"Retained {name} (disabled). Inspect its Run history in the Azure portal.", flush=True)
            else:
                request("post", f"{site_id}/deployWorkflowArtifacts", {
                    "filesToDelete": [f"{name}/workflow.json", f"{name}/"]
                })
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as cleanup_error:
            operation = "Disabling retained workflow" if keep_workflow else "Cleanup"
            if failure is not None:
                raise RuntimeError(
                    f"{failure}\n{operation} also failed for {name}: {cleanup_error}"
                ) from cleanup_error
            raise
    print(f"Seeded {len(documents)} lookup records. The lab01Cosmos connection is ready.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", nargs="?", type=Path, default=ROOT / "foundation.deployment.json")
    parser.add_argument(
        "--keep-workflow", action="store_true",
        help="Retain the seed workflow and run history for debugging; disable it instead of deleting it.",
    )
    args = parser.parse_args()
    try:
        regions = json.loads(REGIONS.read_text())
        support_tiers = json.loads(SUPPORT_TIERS.read_text())
        if not isinstance(regions, list) or not regions or not isinstance(support_tiers, list) or not support_tiers:
            raise ValueError("Each seed file must contain a nonempty JSON array.")
        seed(
            json.loads(args.handoff.read_text()),
            regions + support_tiers,
            keep_workflow=args.keep_workflow,
        )
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Lookup seeding failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
