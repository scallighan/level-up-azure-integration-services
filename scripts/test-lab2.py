#!/usr/bin/env python3
"""Create three public orders, cancel one, and verify Lab 2 routing and persistence checks."""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid


ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "labs/02-topic-fanout/contracts"
EVENT_WORKFLOWS = {
    "order.created": "order-created",
    "order.cancelled": "order-cancelled",
}
WORKFLOWS = ("audit", *EVENT_WORKFLOWS.values())
RULES = {
    "audit": ("all-events", "1 = 1"),
    "order-created": ("order-created", "eventType = 'order.created'"),
    "order-cancelled": ("order-cancelled", "eventType = 'order.cancelled'"),
}
SENDER_ROLE = "69a216fc-b8fb-44d8-bc22-1f3c2cd27a39"
ARM = "https://management.azure.com"
API_VERSION = "2025-03-01"


def az_json(arguments):
    result = subprocess.run(
        ["az", *arguments, "--output", "json", "--only-show-errors"],
        capture_output=True, text=True, timeout=90,
    )
    if result.returncode:
        codes = re.findall(r'"code"\s*:\s*"([A-Za-z0-9_.-]+)"', result.stderr)
        detail = ", ".join(codes) if codes else "check az login, permissions, and Azure activity logs"
        # Never echo token responses, linked run payloads, or full CLI output.
        raise RuntimeError(f"Azure CLI {arguments[0]} failed: {detail}.")
    return json.loads(result.stdout) if result.stdout.strip() else None


def arm_get(path):
    separator = "&" if "?" in path else "?"
    return az_json([
        "rest", "--method", "get", "--url",
        f"{ARM}{path}{separator}api-version={API_VERSION}",
    ])


def validate_handoff(foundation):
    site_id = foundation["logic_app_id"]
    match = re.fullmatch(
        r"/subscriptions/([0-9a-f-]+)/resourceGroups/([^/]+)/providers/Microsoft.Web/sites/([^/]+)",
        site_id, re.IGNORECASE,
    )
    if not match or match[2].casefold() != foundation["resource_group_name"].casefold():
        raise ValueError("Use the Lab 0 handoff with its explicit site and parent group.")
    uuid.UUID(match[1])
    namespace_name = foundation["service_bus_namespace_name"]
    if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9-]{4,48}[a-zA-Z0-9]", namespace_name):
        raise ValueError("The handoff contains an invalid Service Bus namespace name.")
    namespace_id = (
        f"/subscriptions/{match[1]}/resourceGroups/{match[2]}"
        f"/providers/Microsoft.ServiceBus/namespaces/{namespace_name}"
    )
    if (
        foundation["service_bus_namespace_id"].casefold() != namespace_id.casefold()
        or foundation["service_bus_fqdn"] != f"{namespace_name}.servicebus.windows.net"
    ):
        raise ValueError("The handoff must reference the Lab 0 namespace in the site's subscription and group.")
    return match[1], f"{foundation['service_bus_namespace_id']}/topics/orders"


def signed_in_user(subscription):
    account = az_json(["account", "show"])
    if account["id"].casefold() != subscription.casefold():
        raise ValueError("Select the subscription in foundation.deployment.json with az account set.")
    if account["user"]["type"] != "user":
        raise ValueError("Sign in with the student's user account; this helper does not grant application or site identities access.")
    principal = az_json(["ad", "signed-in-user", "show", "--query", "id"])
    uuid.UUID(principal)
    return principal


def sender_access(topic_id, principal):
    namespace_id = topic_id.rsplit("/topics/", 1)[0]
    assignments = az_json(["role", "assignment", "list", "--scope", topic_id, "--include-inherited"])
    matching = [
        assignment for assignment in assignments
        if assignment["principalId"].casefold() == principal.casefold()
        and assignment["scope"].casefold() in (topic_id.casefold(), namespace_id.casefold())
        and assignment["roleDefinitionId"].lower().endswith(f"/{SENDER_ROLE}")
    ]
    if not matching:
        raise ValueError("Missing student Data Sender access. Complete Lab 0 setup, preview, and deployment; this test never creates grants.")
    print("Current user has Data Sender access on the workshop namespace or orders topic.")


def fresh_event(event_type, order_id):
    sample = f"sample-{event_type.replace('.', '-')}.json"
    event = json.loads((CONTRACTS / sample).read_text())
    event["eventId"] = str(uuid.uuid4())
    event["correlationId"] = str(uuid.uuid4())
    event["occurredAt"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    event["data"]["orderId"] = order_id
    return event


def ready_rules(foundation):
    arguments = [
        "--resource-group", foundation["resource_group_name"],
        "--namespace-name", foundation["service_bus_namespace_name"],
        "--topic-name", "orders",
    ]
    subscriptions = az_json(["servicebus", "topic", "subscription", "list", *arguments])
    if {subscription["name"] for subscription in subscriptions} != set(WORKFLOWS):
        raise RuntimeError("Expected exactly audit, order-created, and order-cancelled subscriptions. Nothing was published.")
    for name, (rule_name, expression) in RULES.items():
        rules = az_json([
            "servicebus", "topic", "subscription", "rule", "list",
            *arguments, "--subscription-name", name,
        ])
        if (
            len(rules) != 1
            or rules[0]["name"] != rule_name
            or rules[0].get("filterType") != "SqlFilter"
            or re.sub(
                r"\s*=\s*", "=", (rules[0].get("sqlFilter") or {}).get("sqlExpression") or "",
            ).strip() != expression.replace(" = ", "=")
            or (rules[0].get("action") or {}).get("sqlExpression")
        ):
            raise RuntimeError(
                f"{name} must have only the {rule_name} SQL rule ({expression}), with no rule action or $Default. Nothing was published."
            )


def publish(fqdn, event):
    token = az_json([
        "account", "get-access-token", "--resource", "https://servicebus.azure.net",
        "--query", "accessToken",
    ])
    if not isinstance(token, str) or not token:
        raise RuntimeError("Azure CLI did not return a Service Bus access token.")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "BrokerProperties": json.dumps({
            "MessageId": event["eventId"],
            "CorrelationId": event["correlationId"],
        }),
        # Quoted HTTP values remain strings, especially schemaVersion=1.0.
        "eventType": json.dumps(event["eventType"]),
        "schemaVersion": json.dumps(event["schemaVersion"]),
        "correlationId": json.dumps(event["correlationId"]),
        "x-ms-retrypolicy": "NoRetry",
    }
    request = Request(
        f"https://{fqdn}/orders/messages",
        data=json.dumps(event).encode("utf-8"), headers=headers, method="POST",
    )
    try:
        with urlopen(request, timeout=30) as response:
            if response.status != 201:
                raise RuntimeError(f"Unexpected send status {response.status}; inspect this correlation ID before rerunning.")
    except HTTPError as error:
        raise RuntimeError(
            f"Service Bus send failed with HTTP {error.code}. Check the Lab 0 student sender grant/propagation and namespace quotas. No keys or new roles will be used."
        ) from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(
            "Send outcome is uncertain; do not automatically resend. Inspect the printed correlation ID first."
        ) from error


def ready_workflows(site_id):
    response = arm_get(f"{site_id}/workflows")
    workflows = {workflow["name"].split("/")[-1]: workflow["properties"] for workflow in response["value"]}
    for name in WORKFLOWS:
        properties = workflows.get(name)
        if not properties or properties.get("health", {}).get("state") != "Healthy":
            raise RuntimeError(f"{name} is missing or unhealthy. Deploy Task 2 and resolve runtime validation errors before publishing.")
        if properties.get("state") == "Disabled":
            raise RuntimeError(f"{name} is disabled; nothing was published.")
        trigger = arm_get(
            f"{site_id}/hostruntime/runtime/webhooks/workflow/api/management/workflows/{name}/triggers/Receive_order"
        )
        if trigger["properties"].get("state") == "Disabled":
            raise RuntimeError(f"{name}/Receive_order is disabled; nothing was published.")


def check_run(runtime, run, event, workflow):
    properties = run["properties"]
    status = properties["status"]
    if status in ("Running", "Waiting", "Accepted"):
        return False
    actions = arm_get(f"{runtime}/runs/{run['name']}/actions")["value"]
    by_name = {action["name"].split("/")[-1]: action["properties"] for action in actions}
    if status != "Succeeded":
        failed = ", ".join(
            f"{name}={action['status']}" for name, action in by_name.items()
            if action["status"] in ("Failed", "TimedOut")
        )
        raise RuntimeError(f"Run {run['name']} finished {status}; failed actions: {failed or 'inspect run history'}.")
    required = ["Process_message", "Complete_message"]
    if workflow != "audit":
        required.extend(["Read_order", "Verify_order"])
    for name in required:
        if name not in by_name and name in ("Read_order", "Verify_order"):
            action = arm_get(f"{runtime}/runs/{run['name']}/actions/{name}")
            by_name[name] = action["properties"]
        if by_name.get(name, {}).get("status") != "Succeeded":
            raise RuntimeError(f"Run {run['name']} did not successfully execute {name}.")
    telemetry = by_name.get("Emit_telemetry", {}).get("trackedProperties")
    if telemetry is not None and (
        telemetry.get("eventId") != event["eventId"]
        or telemetry.get("correlationId") != event["correlationId"]
    ):
        raise RuntimeError(f"Run {run['name']} telemetry does not match the published event and correlation IDs.")
    return True


def wait_for_fanout(site_id, event, timeout, observation_seconds=10):
    deadline = time.monotonic() + timeout
    expected = {"audit", EVENT_WORKFLOWS[event["eventType"]]}
    succeeded = set()
    settled_at = None
    while time.monotonic() < deadline:
        for name in WORKFLOWS:
            runtime = f"{site_id}/hostruntime/runtime/webhooks/workflow/api/management/workflows/{name}"
            runs = arm_get(f"{runtime}/runs?$top=100")["value"]
            matching = [
                run for run in runs
                if run["properties"].get("correlation", {}).get("clientTrackingId") == event["correlationId"]
            ]
            if matching and name not in expected:
                raise RuntimeError(
                    f"Incorrect routing: {name} received {event['eventType']} (correlation {event['correlationId']}). Check subscription rules."
                )
            if len(matching) > 1:
                raise RuntimeError(f"{name} has multiple runs for this correlation ID; inspect redeliveries rather than reporting exactly-once success.")
            if matching and name not in succeeded and check_run(runtime, matching[0], event, name):
                detail = "audit processing" if name == "audit" else "processing and Cosmos read-back assertion"
                print(f"{name}: Succeeded; {detail} and message completion verified (run {matching[0]['name']}).", flush=True)
                succeeded.add(name)
        if succeeded == expected:
            if settled_at is None:
                settled_at = time.monotonic()
            if time.monotonic() - settled_at >= observation_seconds:
                print(f"PASS: {event['eventType']} reached only audit and {EVENT_WORKFLOWS[event['eventType']]} during the observation window.")
                return
        time.sleep(5)
    pending = ", ".join(name for name in WORKFLOWS if name in expected - succeeded)
    raise TimeoutError(
        f"Timed out waiting for {pending or 'the routing observation window'}. Inspect this correlation ID, scoped RBAC, and dead-letter counts before publishing another event."
    )


def positive_seconds(value):
    seconds = int(value)
    if seconds < 1:
        raise argparse.ArgumentTypeError("timeout must be a positive number of seconds")
    return seconds


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("handoff", nargs="?", type=Path, default=ROOT / "foundation.deployment.json")
    parser.add_argument("--dry-run", action="store_true", help="Show identifiers and predicted counts without contacting Azure or changing access.")
    parser.add_argument("--timeout", type=positive_seconds, default=180, help="Seconds per event for correlated runs and routing observation (default: 180).")
    args = parser.parse_args()
    try:
        foundation = json.loads(args.handoff.read_text())
        subscription, topic_id = validate_handoff(foundation)
        order_ids = [f"ORD-{uuid.uuid4()}" for _ in range(3)]
        if args.dry_run:
            print("Dry run: no Azure requests, permission changes, or messages.")
        else:
            principal = signed_in_user(subscription)
            if foundation.get("publisher_principal_id", principal).casefold() != principal.casefold():
                raise ValueError("The current Azure user differs from the publisher selected in Lab 0; sign in as that user or repeat Lab 0 setup and deployment.")
            ready_workflows(foundation["logic_app_id"])
            ready_rules(foundation)
            sender_access(topic_id, principal)
        print("Expected: 4 publications, 8 subscription copies/runs (audit 4, order-created 3, order-cancelled 1); two orders stay created, the first is cancelled.", flush=True)
        scenario = [("order.created", order_id) for order_id in order_ids]
        scenario.append(("order.cancelled", order_ids[0]))
        for event_type, order_id in scenario:
            event = fresh_event(event_type, order_id)
            workflow = EVENT_WORKFLOWS[event_type]
            print(f"{event_type}\nOrderId: {order_id}\nEventId: {event['eventId']}\nCorrelationId: {event['correlationId']}", flush=True)
            print(f"Expected receivers: audit, {workflow}; no run in the other specialist.", flush=True)
            if args.dry_run:
                continue
            publish(foundation["service_bus_fqdn"], event)
            print("Published once; waiting for correlated processing, persistence checks, and routing observation...", flush=True)
            wait_for_fanout(foundation["logic_app_id"], event, args.timeout)
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, EOFError, subprocess.TimeoutExpired) as error:
        print(f"Lab 2 test failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
