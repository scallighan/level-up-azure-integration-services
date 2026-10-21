---
title: "Lab 2: Event routing and Cosmos order lifecycle"
permalink: /labs/02-topic-fanout/
---

# Lab 2: Event routing and Cosmos order lifecycle

Use one topic and three workflows to demonstrate catch-all auditing and
event-type routing. Create an order in Cosmos DB with `order.created`, then
mark it cancelled with `order.cancelled`.

**Time:** 75 minutes. **Required:** [Lab 0](../00-foundation/README.md), not Lab 1.

![An audit workflow receives all events while two filtered workflows create and cancel Cosmos orders](../../docs/assets/lab-02-topic-fanout-architecture.svg)

| Subscription / workflow | Receives | Processing |
|---|---|---|
| `audit` | Every event type | Emit sanitized audit telemetry |
| `order-created` | Only `order.created` | Create an order document |
| `order-cancelled` | Only `order.cancelled` | Mark an existing order cancelled |

The broker filters before delivery; specialists do not receive and discard
other event types. Lab 2 owns a new `orders` NoSQL container in Lab 0's Cosmos
database, separate from Lab 1 lookup data. Lab 1 is still not a prerequisite.

## Start

Read the [implementation requirements](implementation-requirements.md),
[common event envelope](contracts/event-envelope.schema.json), and both event
contracts and samples: [creation](contracts/order-created.schema.json),
[creation sample](contracts/sample-order-created.json),
[cancellation](contracts/order-cancelled.schema.json), and
[cancellation sample](contracts/sample-order-cancelled.json).
Initialize one track with the
[Bicep starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-bicep.prompt.md)
or [Terraform starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-terraform.prompt.md)
([how to invoke](../../docs/copilot-working-agreement.md#invoking-workshop-prompt-files)).
The starter creates files only; use the prompts below one at a time.

Reuse `.env` and `foundation.deployment.json`; set
`FOUNDATION_RESOURCE_GROUP_NAME` from the handoff.

```bash
set -a; source .env; set +a
```

For each change, have Copilot explain the resource graph, identities, files,
and checks before approval. Run Bicep format/build/what-if or Terraform
fmt/validate/plan; review the preview and artifact files before deploying.

## Step 0: reference the foundation

```text
Verify the Lab 0 handoff and configure existing-resource references for its
site, Service Bus namespace, Cosmos account/database, and monitoring.
Follow the Lab 2 requirements.
Do not change the foundation or add messaging, roles, connections, or workflows.
```

Run `bash scripts/verify-foundation.sh foundation.deployment.json`.
This step must produce no managed-resource changes.

## Task 1: add the messaging infrastructure

```text
Add the orders topic and audit/order-created/order-cancelled subscriptions.
Use one catch-all rule for audit and distinct event-type rules for the others.
Add the orders Cosmos container in the existing database, managed-identity
Service Bus and Cosmos connections, three subscription-scoped receiver grants,
and one new-container-scoped Cosmos contributor grant for the site's system
identity. Follow the Lab 2 requirements. Preserve all shared resources,
existing grants, and connection entries. Do not add workflow definitions.
```

Check exactly three subscriptions and one named rule each: audit uses
`1 = 1`, creation uses `eventType = 'order.created'`, and cancellation uses
`eventType = 'order.cancelled'`. Remove `$Default` after adding the named rules.
Check duplicate detection, subscription-scoped receiver grants, and an
`orders` container with partition key `/id` and its own scoped Cosmos grant.
No changes to the existing `items` container or parent throughput are allowed.

## Task 2: add the receivers

```text
Add only audit, order-created, and order-cancelled workflows, each receiving
from its assigned subscription. Audit all event types using the common
envelope. Create a Cosmos order for order.created and mark that existing
order cancelled for order.cancelled. Follow the Lab 2 contracts, idempotency,
read-back verification, and action-naming requirements. Use managed identity
and peek-lock, complete only after processing and persistence checks succeed,
and preserve retries and dead lettering. Do not change infrastructure or grants.
```

Keep generated definitions/templates in the ignored local `workflows/`
folder; students generate their own solution rather than copying one from Git.
Use the same order ID as document ID and partition key. Do not let a repeated
creation overwrite a cancellation. Cancellation of a missing order must fail
and retry, not invent a partial document.

## Task 3: publish and trace

After deploying Tasks 1 and 2, run from the repository root:

```bash
set -a; source .env; set +a
python3 scripts/test-lab2.py
```

The helper uses your current `az login` **user** and reuses the namespace-scoped
**Data Sender** grant created by Lab 0. It creates no grants and never changes
the site's permissions or enables SAS. If access is missing, repeat Lab 0
setup, preview, and deployment with the original foundation inputs.
RBAC propagation can take several minutes.

It sends a creation for a fresh order ID, waits for audit and creation
processing, then sends cancellation for that same order. Each event gets fresh
event/correlation IDs and a timestamp. It checks broker rules, matching runs,
successful Cosmos read-back assertions, and message completion, without
connecting the workstation to private Cosmos.

Expect **two publications and four copies/runs**: audit runs twice, creation
once, and cancellation once. The unrelated specialist must not run for each
event. The helper observes for incorrect routing for 10 seconds after expected
runs finish; the rule checks also detect catch-all specialist filters.
The order must transition from `created` to `cancelled`, preserving its
original customer/order fields.

Only statuses and identifiers are printed; no tokens, event bodies, or linked
action payloads. Existing payload-visibility settings remain unchanged.

Use `python3 scripts/test-lab2.py --dry-run` to preview without Azure requests.
The live test waits up to 180 seconds (`--timeout 300` extends this).
Failures exit nonzero with diagnostics. If a send's outcome is uncertain,
inspect the printed correlation ID before rerunning: each invocation creates
a fresh order lifecycle rather than retrying the previous one. The helper
does not change workflow definitions or create infrastructure/roles; the old
fulfillment/notification solution will not pass the revised preflight.

Service Bus Explorer remains an optional alternative. Set
`ContentType=application/json`, `MessageId=eventId`, and the broker
`CorrelationId` to the body's `correlationId`; add string application
properties `eventType` matching the selected sample, `schemaVersion=1.0`, and
`correlationId`. Send cancellation only after creation succeeds. To demonstrate
catch-all behavior, send a valid common envelope with a new event type:
only audit should run, with no Cosmos changes.

## Task 4: prove failure isolation

After successfully creating a fresh order, ask Copilot for a controlled
`order-cancelled` processing failure before any Cosmos mutation, expected
delivery counts, and an exact revert. Publish cancellation for that order.
Audit must complete independently; only the cancellation copy retries and
eventually dead-letters. The creation workflow must not receive cancellation,
and the document must remain `created`. Revert the deliberate failure.
Also discuss cancellation arriving before creation and replay after the
broker's duplicate-detection window.

## Cleanup

Remove only Lab 2's topic and children, four scoped grants, `orders` Cosmos
container and its lab documents, workflows, and unused `lab02ServiceBus` /
`lab02Cosmos` connection entries. Verify uploaded artifacts are removed even after
Terraform destroy. Preserve Lab 0's group, namespace, site, and other labs'
artifacts, including the Lab 0 student sender grant
([ownership details](implementation-requirements.md#implementation-sequence)).
