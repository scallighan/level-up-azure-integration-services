---
title: "Lab 2: Event routing and Cosmos order lifecycle"
permalink: /labs/02-topic-fanout/
---

# Lab 2: Event routing and Cosmos order lifecycle

Use one topic and three workflows to demonstrate catch-all auditing and
event-type routing. Create an order in Cosmos DB with `order.created`, then
mark it cancelled with `order.cancelled`.

**Time:** 75 minutes. **Required:** [Lab 0](../00-foundation/README.md),
Python 3, and the same Azure CLI session. Lab 1 is not required.

![An audit workflow receives all events while two filtered workflows create and cancel Cosmos orders](../../docs/assets/lab-02-topic-fanout-architecture.svg)

| Subscription / workflow | Receives | Processing |
|---|---|---|
| `audit` | Every event type | Emit sanitized audit telemetry |
| `order-created` | Only `order.created` | Create an order document |
| `order-cancelled` | Only `order.cancelled` | Mark an existing order cancelled |

## Start

Keep the Bicep or Terraform track you chose in Lab 0. Initialize it with the
[Bicep starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-bicep.prompt.md)
or [Terraform starter](https://github.com/scallighan/level-up-azure-integration-services/blob/main/.github/prompts/02-fanout-terraform.prompt.md)
([how to invoke](../../docs/copilot-working-agreement.md#invoking-workshop-prompt-files)).
Use the prompts below one at a time.

Review the generated files and deployment preview before approving each change.
The [implementation requirements](implementation-requirements.md) contain the
contracts, broker configuration, permissions, and message-processing details.

## Step 0: reference the foundation

```text
Verify the Lab 0 handoff and configure existing-resource references for its
site, Service Bus namespace, Cosmos account/database, and monitoring.
Follow the Lab 2 requirements.
Do not change the foundation or add messaging, roles, connections, or workflows.
```

Run `bash scripts/verify-foundation.sh foundation.deployment.json`.

## Task 1: add the messaging infrastructure

```text
Build the Lab 2 messaging and Cosmos resources. Follow
labs/02-topic-fanout/implementation-requirements.md.
Reuse Lab 0 and preserve existing resources, grants, and connections.
Do not add workflow definitions. Show the files and checks before deploying.
```

## Task 2: add the receivers

```text
Build audit, order-created, and order-cancelled workflows for Lab 2.
Follow labs/02-topic-fanout/implementation-requirements.md and its event contracts.
Audit all event types. Create orders on order.created and cancel existing
orders on order.cancelled. Reuse Lab 0 and the existing connections.
Do not change infrastructure or grants. Show the files and checks before
deploying.
```

## Task 3: publish and trace

After deploying Tasks 1 and 2, run from the repository root:

```bash
set -a; source .env; set +a
python3 scripts/test-lab2.py
```

The helper creates three fresh orders, verifies each creation, then cancels
only the first. Expect **four publications and eight workflow runs**:

| Workflow | Expected runs |
|---|---|
| `audit` | 4 |
| `order-created` | 3 |
| `order-cancelled` | 1 |

Two orders remain `created`; the first becomes `cancelled`. Use the printed
correlation IDs to follow the runs in the Azure portal.

See the [test-helper reference](implementation-requirements.md#helper-options-and-troubleshooting)
for options and troubleshooting.

## Task 4: prove failure isolation

Ask Copilot for a controlled failure in cancellation processing and an exact
revert. Publish cancellation for a newly created order.

Confirm audit still succeeds while cancellation retries and eventually
dead-letters. The order should stay `created`. Restore the workflow afterward.

## Cleanup

Remove only Lab 2's resources and workflow artifacts. Preserve Lab 0 and other
labs' workflows and connections. Follow the
[cleanup ownership requirements](implementation-requirements.md#implementation-sequence).
