# Lab 2 implementation requirements

These requirements define the implementation boundary for the topic fan-out
integration. Read them with [`README.md`](README.md), both files under
[`contracts/`](contracts/), the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Broker topology

- Reference the Standard Service Bus namespace deployed by Lab 0. It uses
  Entra-only authorization over its public endpoint; Standard has no private
  endpoint support. Recommend Premium for production private networking.
- Create the `orders` topic with duplicate detection enabled.
- Create exactly three subscriptions: `audit`, `fulfillment`, and
  `notification`.
- Remove each subscription's `$Default` rule and add a SQL filter for
  `eventType = 'order.created'`.
- Make lock duration, maximum delivery count, message TTL, duplicate-detection
  window, retry behavior, and failure behavior explicit.

Treat [`contracts/order-created.schema.json`](contracts/order-created.schema.json)
and [`contracts/sample-order-created.json`](contracts/sample-order-created.json)
as the source of truth for the event.

## Logic App hosting and identities

Require [Lab 0](../00-foundation/README.md) and explicit references from its
local `foundation.deployment.json`. Reference its integration subnet, host
storage, host identity, WS1 plan, monitoring, Standard site, and Service Bus
namespace. Validate subscription, deployment region, connectivity, and host
settings. Reject missing/incompatible inputs; do not infer names or create a
fallback foundation. There is no standalone `new` mode.

Do not import, retag, modify, or delete Lab 0 resources or own the parent group,
site, or namespace. Use one shared site for all three workflows. Grant its system identity the
receiver role separately at each of the three subscription scopes. Never grant
it receiver access at namespace or topic scope. The user-assigned identity
remains limited to host storage.

Reusing the Lab 0 site means its system identity retains its Lab 0 Cosmos role
and gains three Lab 2 subscription-scoped Service Bus roles. Make this
cross-lab identity tradeoff explicit before deployment. Lab 2 may own its role
assignments and child workflow resources, but it must not manage the existing
parent site.

Preserve other labs' workflow artifacts, app settings, and `connections.json`
entries. Add only the Service Bus connection entry needed here. Never expose
credentials or observability connection strings as outputs.

For publishing tests, the student's Entra principal needs a separate
topic-scoped Data Sender grant. Parameterize and confirm the student principal;
do not grant the site sender access merely to run this manual test. Track this
grant as Lab 2-owned and remove it during cleanup.

## Implementation sequence

Keep infrastructure provisioning separate from workflow behavior in both IaC
tracks:

0. Verify Lab 0 and configure existing-resource references, with no managed
   resource changes. Lab 1 is not a prerequisite.
1. Create the Service Bus topology, managed-identity connection configuration,
   three subscription-scoped receiver role assignments for the selected site's
   system identity, and correlated observability. Do not add workflow
   definitions.
2. Add only the audit, fulfillment, and notification workflow definitions and
   their message-processing behavior.

Destroying Lab 2 must remove only its messaging children, grants, and artifacts.
The Lab 0 resource group, namespace, hosting, monitoring, and parent site remain
untouched. Explicitly remove uploaded workflows and unused connection entries;
Terraform action-state destruction alone may not remove deployed artifacts.

## Message processing

Each workflow must use managed identity and peek-lock semantics:

1. Receive and lock one message from its assigned subscription.
2. Parse and validate the event.
3. Perform its workflow-specific action.
4. Complete the message only after processing succeeds.
5. Preserve abandon, retry, and dead-letter behavior on failure.

The core actions remain lightweight:

- **Audit:** emit structured telemetry.
- **Fulfillment:** compose a fulfillment request and emit telemetry.
- **Notification:** compose a customer message and emit telemetry.

Do not add email, databases, or other paid dependencies to the core lab. Do not
place connection strings or full sensitive event payloads in source, outputs,
state, or run history.

All three workflows follow the repository-wide
[sample payload visibility](../../docs/implementation-standards.md#sample-payload-visibility)
standard: `show_sample_payloads=true` by default in both tracks, making the
sanitized teaching event visible in run history. Keep `false` available and
require it before using real customer data. Telemetry should still contain
status and correlation IDs, not full event bodies.
