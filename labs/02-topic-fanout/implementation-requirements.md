# Lab 2 implementation requirements

These requirements define the implementation boundary for the topic fan-out
integration. Read them with [`README.md`](README.md), both files under
[`contracts/`](contracts/), the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Broker topology

- Use a Standard Service Bus namespace because the lab requires topics.
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

Require an explicit hosting foundation mode of `new` or `existing`. Do not
infer the mode from repository state or from resources found in the
subscription.

- `new`: create a Lab 2-owned Logic App Standard hosting foundation with one
  VNet, one host storage account with four private endpoints and private DNS,
  one host-storage user-assigned identity, one Windows WS1 Workflow Standard
  plan, observability, and one empty Logic App Standard site.
- `existing`: require explicit references to a compatible deployed foundation
  and Standard site, such as those from Lab 1. Reference the Logic App
  integration subnet, host storage, host-storage identity, WS1 plan,
  observability resources, and site without importing, retagging, modifying,
  or deleting the foundation or taking ownership of the parent site.

In both modes, create a Lab 2-owned resource group and use one Logic App
Standard site for all three workflows. Grant the site's system identity the
receiver role separately at each of the three subscription scopes. Never grant
it receiver access at namespace or topic scope. The user-assigned identity
remains limited to host storage.

Reusing the Lab 1 site means its system identity retains its Lab 1 Cosmos role
and gains three Lab 2 subscription-scoped Service Bus roles. Make this
cross-lab identity tradeoff explicit before deployment. Lab 2 may own its role
assignments and child workflow resources, but it must not manage the existing
parent site.

Reject incomplete or mixed mode-specific inputs. Existing mode must confirm
that the referenced resources are in the current subscription and region and
that the subnet, plan, storage connectivity, host-storage identity roles, site,
and host settings remain compatible with the required baseline. Never expose
storage credentials or observability connection strings as outputs.

## Implementation sequence

Keep infrastructure provisioning separate from workflow behavior in both IaC
tracks:

0. Resolve the shared hosting foundation. Create it in `new` mode when Lab 1
   was skipped or cleaned up; otherwise reference the compatible Lab 1
   foundation and Standard site in `existing` mode. Establish ownership and
   cleanup boundaries before adding integration resources.
1. Create the Service Bus topology, managed-identity connection configuration,
   three subscription-scoped receiver role assignments for the selected site's
   system identity, and correlated observability. Do not add workflow
   definitions.
2. Add only the audit, fulfillment, and notification workflow definitions and
   their message-processing behavior.

Destroying Lab 2 must remove only Lab 2-owned resources. In `existing` mode,
the referenced hosting and observability foundation and parent Logic App site
must remain untouched.

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
place connection strings or full event payloads in source, outputs, state, or
run history.
