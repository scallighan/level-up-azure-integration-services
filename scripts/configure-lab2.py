#!/usr/bin/env python3
"""Remove Lab 2 default rules and merge its built-in managed-identity connections."""

import argparse
import copy
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


CONNECTION_NAME = "lab02ServiceBus"
RULES = {
    "audit": ("all-events", "1 = 1"),
    "order-created": ("order-created", "eventType = 'order.created'"),
    "order-cancelled": ("order-cancelled", "eventType = 'order.cancelled'"),
}


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


def cosmos_connection(endpoint):
    return {
        "displayName": "Lab 2 orders Cosmos",
        "parameterSetName": "ManagedServiceIdentity",
        "parameterValues": {
            "accountURI": endpoint,
            "authProvider": {"Type": "ManagedServiceIdentity"},
        },
        "serviceProvider": {"id": "/serviceProviders/AzureCosmosDB"},
    }


def merge_connection(connections, fqdn, remove=False, *, cosmos_endpoint=None):
    if not isinstance(connections, dict):
        raise ValueError("The existing connections.json must be an object; nothing was changed.")
    merged = copy.deepcopy(connections)
    providers = merged.get("serviceProviderConnections", {})
    if not isinstance(providers, dict):
        raise ValueError("serviceProviderConnections must be an object; nothing was changed.")
    expected = {CONNECTION_NAME: connection(fqdn)}
    if cosmos_endpoint is not None:
        expected["lab02Cosmos"] = cosmos_connection(cosmos_endpoint)
    for name, definition in expected.items():
        if name in providers and providers[name] != definition:
            raise ValueError(f"{name} already has a different definition; refusing to overwrite or remove it.")
    if remove:
        for name in expected:
            providers.pop(name, None)
    else:
        merged["serviceProviderConnections"] = providers
        providers.update(expected)
    return merged


def remove_defaults(namespace_id):
    topic_id = f"{namespace_id}/topics/orders"
    subscriptions = request("get", f"{topic_id}/subscriptions", api_version="2024-01-01")
    if {item["name"].split("/")[-1] for item in subscriptions["value"]} != set(RULES):
        raise ValueError("orders must contain exactly audit, order-created, and order-cancelled before configuring it.")
    validated = []
    for name, (rule_name, expression) in RULES.items():
        rules_id = f"{topic_id}/subscriptions/{name}/rules"
        rules = request("get", rules_id, api_version="2024-01-01")["value"]
        by_name = {rule["name"].split("/")[-1]: rule for rule in rules}
        selected = by_name.get(rule_name, {}).get("properties", {})
        if (
            set(by_name) - {"$Default", rule_name}
            or selected.get("filterType") != "SqlFilter"
            or re.sub(
                r"\s*=\s*", "=", (selected.get("sqlFilter") or {}).get("sqlExpression") or "",
            ).strip() != expression.replace(" = ", "=")
            or (selected.get("action") or {}).get("sqlExpression")
        ):
            raise ValueError(f"{name} must have the expected {rule_name} SQL rule ({expression}) and no unrelated rules.")
        validated.append((name, rules_id, rule_name, "$Default" in by_name))
    for name, rules_id, rule_name, has_default in validated:
        if has_default:
            request("delete", f"{rules_id}/$Default", api_version="2024-01-01")
        remaining = request("get", rules_id, api_version="2024-01-01")["value"]
        if [rule["name"].split("/")[-1] for rule in remaining] != [rule_name]:
            raise RuntimeError(f"{name} rules did not converge; receiver grants must not be added.")
        print(f"{name}: {rule_name} filter verified; $Default absent.")


def configure(action, site_id, namespace_id, fqdn, *, cosmos_endpoint=None):
    pattern = r"/subscriptions/([^/]+)/resourceGroups/([^/]+)/providers/Microsoft.Web/sites/([^/]+)"
    site = re.fullmatch(pattern, site_id, re.IGNORECASE)
    if not site:
        raise ValueError("Use the explicit Lab 0 site ID.")
    expected_prefix = f"/subscriptions/{site[1]}/resourceGroups/{site[2]}/providers/Microsoft.ServiceBus/namespaces/"
    namespace = re.fullmatch(re.escape(expected_prefix) + r"([^/]+)", namespace_id, re.IGNORECASE)
    if not namespace or fqdn != f"{namespace[1]}.servicebus.windows.net":
        raise ValueError("Use the Lab 0 namespace ID and FQDN in the site's subscription and group.")
    if cosmos_endpoint is not None and not re.fullmatch(
        r"https://[a-z0-9][a-z0-9-]{1,48}[a-z0-9]\.documents\.azure\.com(?::443)?/?",
        cosmos_endpoint, re.IGNORECASE,
    ):
        raise ValueError("Use the HTTPS Cosmos account endpoint from the Lab 0 handoff.")
    active_subscription = az_json(["account", "show", "--query", "id"])
    if not isinstance(active_subscription, str) or active_subscription.casefold() != site[1].casefold():
        raise ValueError("Select the Azure subscription from the Lab 0 handoff before configuring Lab 2.")

    try:
        response = request("post", f"{site_id}/listWorkflowsConnections")
        current = response["properties"]["files"]["connections.json"]
    except MissingConnectionsFile:
        current = {}
    merged = merge_connection(current, fqdn, remove=action == "remove", cosmos_endpoint=cosmos_endpoint)
    if action == "configure":
        remove_defaults(namespace_id)
    if merged != current:
        request("post", f"{site_id}/deployWorkflowArtifacts", {
            "files": {"connections.json": merged},
        })
        response = request("post", f"{site_id}/listWorkflowsConnections")
        if response["properties"]["files"]["connections.json"] != merged:
            raise RuntimeError("Connection artifact verification failed; inspect the site before retrying.")
    print("Lab 2 connections removed." if action == "remove" else "Lab 2 system-identity connections verified.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("configure", "remove"))
    parser.add_argument("site_id")
    parser.add_argument("namespace_id")
    parser.add_argument("fqdn")
    parser.add_argument("--cosmos-endpoint", help="Also merge lab02Cosmos using the explicit Lab 0 account endpoint.")
    args = parser.parse_args()
    try:
        configure(
            args.action, args.site_id, args.namespace_id, args.fqdn,
            cosmos_endpoint=args.cosmos_endpoint,
        )
    except (ValueError, KeyError, TypeError, OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Lab 2 configuration failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
