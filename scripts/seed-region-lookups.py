#!/usr/bin/env python3
"""Seed Lab 1 through the existing Logic App's private Cosmos connection."""

import argparse
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
API_VERSION = "2025-03-01"
CONNECTION_NAME = "lab01Cosmos"
CONNECTION = {
    "displayName": "Lab 1 region lookup",
    "parameterSetName": "ManagedServiceIdentity",
    "parameterValues": {"accountURI": "@appsetting('AzureCosmosDB_accountEndpoint')"},
    "serviceProvider": {"id": "/serviceProviders/AzureCosmosDB"},
    "authProvider": {"Type": "ManagedServiceIdentity"},
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
    return az_json(
        ["rest", "--method", method, "--url",
         f"https://management.azure.com{path}{separator}api-version={API_VERSION}"],
        body,
    )


def validate_inputs(foundation, regions):
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
    if not isinstance(regions, list) or not regions:
        raise ValueError("The seed data must be a nonempty JSON array.")
    ids = set()
    for region in regions:
        if not isinstance(region, dict) or set(region) != {
            "id", "programmaticName", "physicalLocation"
        }:
            raise ValueError("Each region needs only id, programmaticName, and physicalLocation.")
        name = region["programmaticName"]
        if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9]{1,39}", name):
            raise ValueError("Seed programmatic names must match the API contract.")
        if region["id"] != f"lab01-region-{name}" or region["id"] in ids:
            raise ValueError("Seed IDs must be unique and use the lab01-region- prefix.")
        if not isinstance(region["physicalLocation"], str) or not region["physicalLocation"].strip():
            raise ValueError("Each seeded physical location must be a nonempty string.")
        ids.add(region["id"])
    return match[1]


def read_connections(site_id):
    try:
        result = request("post", f"{site_id}/listWorkflowsConnections")
    except RuntimeError as error:
        # A new foundation has no connections.json until its first workflow.
        message = str(error)
        if not re.search(r'"code"\s*:\s*"NotFound"', message) or "connections.json' not found" not in message:
            raise
        print("No connections.json yet; creating the Lab 1 connection.", flush=True)
        return {}
    connections = result["properties"]["files"]["connections.json"]
    if not isinstance(connections, dict):
        raise ValueError("Azure returned an invalid connections.json; nothing was changed.")
    return connections


def seed_workflow(regions):
    # Keep the schedule dormant; the script starts the trigger through Azure ARM.
    return {
        "kind": "Stateful",
        "definition": {
            "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
            "contentVersion": "1.0.0.0",
            "parameters": {"regionData": {"type": "Array", "defaultValue": regions}},
            "triggers": {
                "seed": {
                    "type": "Recurrence",
                    "recurrence": {
                        "frequency": "Day", "interval": 1,
                        "startTime": "2099-01-01T00:00:00Z",
                    },
                }
            },
            "actions": {
                "Seed_regions": {
                    "type": "Foreach",
                    "foreach": "@parameters('regionData')",
                    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
                    "actions": {
                        "Upsert_region": {
                            "type": "ServiceProvider",
                            "inputs": {
                                "parameters": {
                                    "databaseId": "workshop", "containerId": "items",
                                    "item": "@string(items('Seed_regions'))",
                                    "partitionKey": "@items('Seed_regions')?['id']",
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
                            "runAfter": {},
                        }
                    },
                    "runAfter": {},
                }
            },
            "outputs": {},
        },
    }


def wait_for_workflow(site_id, name):
    deadline = time.monotonic() + 180
    while time.monotonic() < deadline:
        workflows = request("get", f"{site_id}/workflows")["value"]
        for workflow in workflows:
            if workflow["name"].split("/")[-1] != name:
                continue
            health = workflow["properties"]["health"]["state"]
            if health == "Healthy":
                return
            if health == "Unhealthy":
                raise RuntimeError(f"Seed workflow {name} is unhealthy; inspect it in the portal.")
        print("Waiting for the temporary workflow to load...", flush=True)
        time.sleep(5)
    raise TimeoutError(f"Seed workflow {name} did not load within three minutes.")


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
                raise RuntimeError(
                    f"Seed workflow {name}, run {run['name']}, finished with {status}. "
                    "Check Cosmos connectivity and the site's system-identity grant."
                )
        print("Waiting for Cosmos region upserts to finish...", flush=True)
        time.sleep(5)
    if run:
        request("post", f"{runtime_path}/runs/{run['name']}/cancel")
    raise TimeoutError(f"Seed workflow {name} did not finish within five minutes.")


def seed(foundation, regions):
    subscription = validate_inputs(foundation, regions)
    active_subscription = az_json(["account", "show", "--query", "id"])
    if not isinstance(active_subscription, str) or active_subscription.casefold() != subscription.casefold():
        raise ValueError("Select the Azure subscription recorded in foundation.deployment.json.")
    site_id = foundation["logic_app_id"]
    connections = read_connections(site_id)
    providers = connections.setdefault("serviceProviderConnections", {})
    if not isinstance(providers, dict):
        raise ValueError("The site's serviceProviderConnections must be an object.")
    if CONNECTION_NAME in providers and providers[CONNECTION_NAME] != CONNECTION:
        raise ValueError("lab01Cosmos already has different settings; review it before seeding.")
    providers[CONNECTION_NAME] = CONNECTION
    name = f"lab01-seed-{uuid.uuid4().hex[:12]}"
    runtime_path = f"{site_id}/hostruntime/runtime/webhooks/workflow/api/management/workflows/{name}"
    try:
        print(f"Deploying temporary seed workflow {name}...", flush=True)
        request("post", f"{site_id}/deployWorkflowArtifacts", {
            "files": {
                "connections.json": connections,
                f"{name}/workflow.json": seed_workflow(regions),
            }
        })
        wait_for_workflow(site_id, name)
        print(f"Seeding {len(regions)} region lookups through the private Cosmos connection...", flush=True)
        request("post", f"{runtime_path}/triggers/seed/run")
        wait_for_completion(runtime_path, name)
    finally:
        print(f"Removing temporary workflow {name}...", flush=True)
        request("post", f"{site_id}/deployWorkflowArtifacts", {
            "filesToDelete": [f"{name}/workflow.json", f"{name}/"]
        })
    print(f"Seeded {len(regions)} region lookups. The lab01Cosmos connection is ready.", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", nargs="?", type=Path, default=ROOT / "foundation.deployment.json")
    args = parser.parse_args()
    try:
        seed(json.loads(args.handoff.read_text()), json.loads(REGIONS.read_text()))
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Region seeding failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
