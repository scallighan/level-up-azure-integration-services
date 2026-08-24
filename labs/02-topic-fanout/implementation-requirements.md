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

Create one shared Logic App Standard hosting foundation:

- one VNet;
- one host storage account with four private endpoints and private DNS;
- one host-storage user-assigned identity; and
- one Windows WS1 Workflow Standard plan.

Create three independently deployable Logic App Standard sites on that plan.
Each site uses the shared host-storage identity and has its own system-assigned
identity. Grant each system identity access only to its assigned Service Bus
subscription.

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
