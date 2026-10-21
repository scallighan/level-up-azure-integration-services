# Lab 2 implementation requirements

These requirements define the implementation boundary for the topic fan-out
integration. Read them with [`README.md`](README.md), all files under
[`contracts/`](contracts/), the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Broker topology

- Reference the Standard Service Bus namespace deployed by Lab 0. It uses
  Entra-only authorization over its public endpoint; Standard has no private
  endpoint support. Recommend Premium for production private networking.
- Create the `orders` topic with duplicate detection enabled.
- Create exactly three subscriptions and one named SQL rule on each:

  | Subscription / workflow | Rule name | SQL filter | Responsibility |
  |---|---|---|---|
  | `audit` | `all-events` | `1 = 1` | Receive every event type and emit sanitized audit telemetry |
  | `order-created` | `order-created` | `eventType = 'order.created'` | Create an order in Cosmos DB |
  | `order-cancelled` | `order-cancelled` | `eventType = 'order.cancelled'` | Mark an existing Cosmos order cancelled |

- Add the named rules, then remove each subscription's `$Default` rule.
  Leave exactly one rule per subscription. Audit deliberately accepts all
  event types, including future types; the specialists must never have a
  catch-all rule.
- Filter on the string application property `eventType`, not JSON body fields.
  Do not receive every message and discard unrelated types in the workflows.
- Make lock duration, maximum delivery count, message TTL, duplicate-detection
  window, retry behavior, and failure behavior explicit.

Treat the schemas and samples under `contracts/` as the source of truth.
Audit validates the common `event-envelope.schema.json`, not an allow-list of
known event types. Each specialist validates its own event schema and checks
that broker and body event type, schema version, and correlation ID agree.
Use the broker message ID equal to the body's event ID.

## Logic App hosting and identities

Require [Lab 0](../00-foundation/README.md) and explicit references from its
local `foundation.deployment.json`. Reference its integration subnet, host
storage, host identity, WS1 plan, monitoring, Standard site, and Service Bus
namespace. Validate subscription, deployment region, connectivity, and host
settings. Reject missing/incompatible inputs; do not infer names or create a
fallback foundation. There is no standalone `new` mode.

Also reference the handoff's existing Cosmos account, endpoint, and
`cosmos_database_name`. Lab 2 owns one new **NoSQL container** named `orders`
in that database, partition key `/id`; this is not a Cosmos Table API table.
Do not use or modify Lab 0's `items` container or Lab 1's lookup documents.
Keep the account private and keyless, reusing Lab 0's Cosmos private endpoint,
DNS, and site VNet integration. Explain the container's request-unit/storage
cost and preserve the account/database throughput model; do not provision a
new Cosmos account or change parent throughput.

Add one Cosmos DB Built-in Data Contributor data-plane assignment for the
site's system identity, scoped only to the new `orders` container. Preserve
the existing `items` grant. Do not grant account/database-wide Cosmos access,
give the publishing user Cosmos access, or use host-storage identity for data.
Add a built-in managed-identity Cosmos connection named `lab02Cosmos`, using
the handoff's endpoint. Keep `authProvider.Type = ManagedServiceIdentity`
inside `parameterValues`, omitting an explicitly selected identity.

Do not import, retag, modify, or delete Lab 0 resources or own the parent group,
site, or namespace. Use one shared site for all three workflows. Grant its system identity the
receiver role separately at each of the three subscription scopes. Never grant
it receiver access at namespace or topic scope. The user-assigned identity
remains limited to host storage.

Reusing the Lab 0 site means its system identity retains its Lab 0 Cosmos role
and gains three Lab 2 subscription-scoped Service Bus roles plus the new
container-scoped Cosmos grant. Make this
cross-lab identity tradeoff explicit before deployment. Lab 2 may own its role
assignments and child workflow resources, but it must not manage the existing
parent site.

Preserve other labs' workflow artifacts, app settings, and `connections.json`
entries. Add only `lab02ServiceBus` and `lab02Cosmos` entries. Never expose
credentials or observability connection strings as outputs.

For publishing tests, reuse the signed-in student's namespace-scoped Data
Sender grant owned by Lab 0. Lab 0 resolves and confirms that user; the test
helper must not create roles or grant the site sender access. Namespace-wide
student publishing is an explicit workshop convenience, not a production
least-privilege recommendation. Keep all three workflow receiver grants
subscription-scoped.

## Implementation sequence

Keep infrastructure provisioning separate from workflow behavior in both IaC
tracks:

0. Verify Lab 0 and configure existing-resource references, with no managed
   resource changes. Lab 1 is not a prerequisite.
1. Create the Service Bus topology, `orders` Cosmos container, both
   managed-identity connections, three subscription-scoped receiver grants,
   and one container-scoped Cosmos contributor grant for the site's system
   identity. Do not add workflow definitions.
2. Add only `audit`, `order-created`, and `order-cancelled` workflow definitions
   and their message-processing behavior.

Destroying Lab 2 must remove only its messaging children, four scoped grants,
`orders` Cosmos container and its lab sample documents, and workflow artifacts.
The Lab 0 resource group, namespace, hosting, monitoring, and parent site remain
untouched, including the Lab 0 student sender grant. Explicitly remove uploaded
workflows and unused connection entries;
Terraform action-state destruction alone may not remove deployed artifacts.

## Message processing

Each workflow must use managed identity and peek-lock semantics:

1. Receive and lock one message from its assigned subscription.
2. Parse and validate the event.
3. Perform its workflow-specific action.
4. Complete the message only after processing succeeds.
5. Preserve abandon, retry, and dead-letter behavior on failure.

### Audit all event types

Audit emits structured telemetry with event type, event ID, correlation ID,
workflow/run ID, and outcome, without persisting or logging the full payload.
It must process both supplied event types and a well-formed envelope with an
unfamiliar event type. No Cosmos operation is required for audit.

### Persist an order lifecycle

Use `data.orderId` for both document `id` and partition-key value:

- **order-created:** create a document containing `id`, `orderId`,
  `customerId`, `customerEmail`, numeric `total`, `currency`,
  `status = 'created'`, `createdEventId`, and `createdAt`. Copy order fields
  unchanged, and take the last two fields from event ID and `occurredAt`.
  Redelivery must not create another document. On an existing ID, read and
  validate the original creation event and fields; never reset a cancelled
  order to created or overwrite unrelated data with an unconditional upsert.
- **order-cancelled:** read the existing document, preserve its creation and
  customer/order fields, and set `status = 'cancelled'`, `cancelledEventId`,
  `cancelledAt`, and `cancellationReason` from the cancellation event.
  Redelivery of that cancellation is a successful no-op after validating the
  stored result. Do not silently replace conflicting cancellation metadata.
  If the order is missing, fail processing and preserve retry/dead-letter
  handling; do not fabricate an order. Use optimistic concurrency for a
  read/replace update, or an equivalent atomic conditional update, so a
  conflicting write fails and is retried rather than overwriting newer data.

Cosmos writes and Service Bus completion are not one transaction. Explain
why stable document IDs and idempotent state transitions remain necessary
after the topic's duplicate-detection window. There is no cross-subscription
ordering guarantee. The core test waits for creation to finish before sending
cancellation; an early cancellation must retry and can dead-letter if the
order never arrives. Do not promise exactly-once processing.

Before completing either specialist message, read the persisted document
back and validate its ID, required fields, event metadata, and expected state.
Use the built-in Cosmos connector's `content` JSON string as the document;
do not mistake connector metadata for order fields. Carry the successful
write's session token into the read-back so it observes that write.
Use a `Process_message` scope and top-level `Complete_message` action in every
workflow. Inside each specialist's processing scope, name the final Cosmos
read `Read_order` and the native assertion `Verify_order`; both must execute
on every successful path, including duplicate/no-op paths. `Verify_order`
must fail on an incorrect stored result, not merely compose a success string.
The smoke helper checks these action statuses without downloading data
payloads or requiring direct workstation access to private Cosmos.
Use `Receive_order` as the trigger name in all three workflows.

Use native validation/actions and explicit, bounded connector retries.
Keep the schemas unchanged; adapt unsupported `ParseJson` keywords with
native guards as in Lab 1. Avoid inline JavaScript and extra services.
Do not add email, a new account/database, or other paid dependencies.
Never place connection strings or sensitive payloads in source, outputs,
state, console output, or unprotected run history.

All three workflows follow the repository-wide
[sample payload visibility](../../docs/implementation-standards.md#sample-payload-visibility)
standard: `show_sample_payloads=true` by default in both tracks, making the
sanitized teaching events visible in run history. Keep `false` available and
require it before using real customer data. Telemetry should still contain
status and correlation IDs, not full event bodies.

## Routing and persistence checks

Run `python3 scripts/test-lab2.py` after deploying both tasks. It sends a fresh
order creation, waits for audit and creation success, then sends cancellation
for the same fresh order and waits for audit and cancellation success.
Each publication has its own event ID and correlation ID.

| Event type | Audit | Order-created | Order-cancelled | Persisted state |
|---|---|---|---|---|
| `order.created` | One successful run | One successful run | No matching run | `created` |
| `order.cancelled` | One successful run | No matching run | One successful run | `cancelled` |

The helper preflights the exact broker rules, checks successful processing,
specialist read-back assertions, and completion, and watches for incorrectly
routed runs during a bounded observation window. Two publications produce
four expected subscription copies/runs, not six. Runtime observation cannot
prove the permanent absence of a late run; rule inspection establishes the
intended routing configuration.

Also test an unfamiliar event type with a valid common envelope: only audit
should receive it. A valid specialist event with a mismatched broker event
type must fail validation without writing to Cosmos. Exercise same-event
redelivery and missing-order cancellation without weakening RBAC or networking.
