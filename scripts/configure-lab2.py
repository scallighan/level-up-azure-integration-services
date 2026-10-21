#!/usr/bin/env python3
"""Remove Lab 2 default rules and merge its built-in Service Bus connection."""

import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


CONNECTION_NAME = "lab02ServiceBus"
SUBSCRIPTIONS = ("audit", "fulfillment", "notification")
FILTER = "eventType = 'order.created'"


class MissingConnectionsFile(RuntimeError):
    """The site's connections.json does not exist yet."""


def az_json(arguments, body=None):
    with tempfile.TemporaryDirectory(prefix="lab02-") as directory:
        command = ["az", *arguments, "--output", "json", "--only-show-errors"]
        if body is not None:
            path = Path(directory) / "request.json"
            path.write_text(json.dumps(body))
            command += ["--body", f"@{path}"]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    if result.returncode:
        if (
            arguments[0] == "rest"
            and "/listWorkflowsConnections?" in arguments[arguments.index("--url") + 1]
            and re.search(r'"code"\s*:\s*"NotFound"', result.stderr)
            and "connections.json' not found" in result.stderr
        ):
            raise MissingConnectionsFile("The site has no connections.json yet.")
        # Do not echo responses that might include shared connection values.
        codes = re.findall(r'"code"\s*:\s*"([A-Za-z0-9_.-]+)"', result.stderr)
        detail = ", ".join(codes) if codes else "no Azure error code returned"
        raise RuntimeError(f"Azure CLI {arguments[0]} failed (exit {result.returncode}; {detail}); inspect Azure activity logs.")
    return json.loads(result.stdout) if result.stdout.strip() else None


def request(method, resource_id, body=None, api_version="2025-03-01"):
    return az_json([
        "rest", "--method", method,
        "--url", f"https://management.azure.com{resource_id}?api-version={api_version}",
    ], body)


def connection(fqdn):
    return {
        "displayName": "Lab 2 orders",
        "parameterSetName": "ManagedServiceIdentity",
        "parameterValues": {
            "fullyQualifiedNamespace": fqdn,
            "authProvider": {"Type": "ManagedServiceIdentity"},
        },
        "serviceProvider": {"id": "/serviceProviders/serviceBus"},
    }


def merge_connection(connections, fqdn, remove=False):
    if not isinstance(connections, dict):
        raise ValueError("The existing connections.json must be an object; nothing was changed.")
    merged = copy.deepcopy(connections)
    providers = merged.get("serviceProviderConnections", {})
    if not isinstance(providers, dict):
        raise ValueError("serviceProviderConnections must be an object; nothing was changed.")
    expected = connection(fqdn)
    if CONNECTION_NAME in providers and providers[CONNECTION_NAME] != expected:
        raise ValueError("lab02ServiceBus already has a different definition; refusing to overwrite or remove it.")
    if remove:
        providers.pop(CONNECTION_NAME, None)
    else:
        merged["serviceProviderConnections"] = providers
        providers[CONNECTION_NAME] = expected
    return merged


def remove_defaults(namespace_id):
    topic_id = f"{namespace_id}/topics/orders"
    subscriptions = request("get", f"{topic_id}/subscriptions", api_version="2024-01-01")
    if {item["name"].split("/")[-1] for item in subscriptions["value"]} != set(SUBSCRIPTIONS):
        raise ValueError("orders must contain exactly audit, fulfillment, and notification before configuring it.")
    for name in SUBSCRIPTIONS:
        rules_id = f"{topic_id}/subscriptions/{name}/rules"
        rules = request("get", rules_id, api_version="2024-01-01")["value"]
        by_name = {rule["name"].split("/")[-1]: rule for rule in rules}
        selected = by_name.get("order-created", {}).get("properties", {})
        if (
            set(by_name) - {"$Default", "order-created"}
            or selected.get("filterType") != "SqlFilter"
            or selected.get("sqlFilter", {}).get("sqlExpression") != FILTER
            or (selected.get("action") or {}).get("sqlExpression")
        ):
            raise ValueError(f"{name} must have the expected order-created SQL rule and no unrelated rules.")
        if "$Default" in by_name:
            request("delete", f"{rules_id}/$Default", api_version="2024-01-01")
        remaining = request("get", rules_id, api_version="2024-01-01")["value"]
        if [rule["name"].split("/")[-1] for rule in remaining] != ["order-created"]:
            raise RuntimeError(f"{name} rules did not converge; receiver grants must not be added.")
        print(f"{name}: order-created filter verified; $Default absent.")


def configure(action, site_id, namespace_id, fqdn):
    pattern = r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/Microsoft.Web/sites/([^/]+)"
    site = re.fullmatch(pattern, site_id, re.IGNORECASE)
    if not site:
        raise ValueError("Use the explicit Lab 0 site ID.")
    expected_prefix = f"/subscriptions/{site[1]}/resourceGroups/{site[2]}/providers/Microsoft.ServiceBus/namespaces/"
    namespace = re.fullmatch(re.escape(expected_prefix) + r"([^/]+)", namespace_id, re.IGNORECASE)
    if not namespace or fqdn != f"{namespace[1]}.servicebus.windows.net":
        raise ValueError("Use the Lab 0 namespace ID and FQDN in the site's subscription and group.")
    active_subscription = az_json(["account", "show", "--query", "id"])
    if not isinstance(active_subscription, str) or active_subscription.casefold() != site[1].casefold():
        raise ValueError("Select the Azure subscription from the Lab 0 handoff before configuring Lab 2.")

    try:
        response = request("post", f"{site_id}/listWorkflowsConnections")
        current = response["properties"]["files"]["connections.json"]
    except MissingConnectionsFile:
        current = {}
    merged = merge_connection(current, fqdn, remove=action == "remove")
    if action == "configure":
        remove_defaults(namespace_id)
    if merged != current:
        request("post", f"{site_id}/deployWorkflowArtifacts", {
            "files": {"connections.json": merged},
        })
        response = request("post", f"{site_id}/listWorkflowsConnections")
        if response["properties"]["files"]["connections.json"] != merged:
            raise RuntimeError("Connection artifact verification failed; inspect the site before retrying.")
    print("Lab 2 connection removed." if action == "remove" else "Lab 2 system-identity connection verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("configure", "remove"))
    parser.add_argument("site_id")
    parser.add_argument("namespace_id")
    parser.add_argument("fqdn")
    args = parser.parse_args()
    try:
        configure(args.action, args.site_id, args.namespace_id, args.fqdn)
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Lab 2 configuration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
