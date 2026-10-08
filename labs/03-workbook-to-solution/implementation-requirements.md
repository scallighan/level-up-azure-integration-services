# Lab 3 implementation requirements

These requirements define the boundary for deriving and implementing an Azure
integration from workbook evidence. Read them with [`README.md`](README.md),
any existing local files under `plans/`, the repository-wide
[`implementation standards`](../../docs/implementation-standards.md), and the
[`Logic App Standard baseline`](../../docs/logic-app-standard-baseline.md).

## Evidence and approval boundary

- Treat workbook cells as evidence, not as a complete or authoritative
  specification.
- Extract workbook content locally with
  [`scripts/extract-integration-workbook.py`](../../scripts/extract-integration-workbook.py).
  Do not upload a workbook to an external service.
- Store every intermediate artifact in
  `labs/03-workbook-to-solution/plans/`: extracted evidence and images, design
  proposals, assumptions, review notes, test plans, and validation summaries.
  This folder is Git-ignored and excluded from the published workshop site.
  Never force-add its contents or include secrets in planning artifacts.
- Cite sheet names and cell references for every material design conclusion.
- Keep original customer-specific workbook, sheet, system, and broker labels
  only in local evidence. Use consistent generic replacements in any committed
  fixture or documentation; never commit customer payloads or workbook images.
- Record missing triggers, protocols, authentication, volumes, latency,
  ordering, idempotency, recovery, ownership, and network constraints as
  explicit assumptions.
- Write `plans/integration-design.md` with `Status: proposed` as its first line.
  Include the flow graph, resource responsibilities, identity and network
  boundaries, payload expectations, transformation choices, assumptions,
  reliability, observability, costs, validation, ownership, and cleanup.
- Do not initialize IaC or implement Azure resources until the learner resolves
  blocking questions and changes the plan's first line to `Status: approved`.
  No pre-supplied design schema or `contracts/` folder is required for Lab 3.
- A workbook architecture image is supporting evidence only. The extractor
  lists embedded media but does not interpret images; review those images
  separately and record what was verified, citing the sheet and media reference
  rather than inventing cell references.

## Workbook interpretation and flow mapping

- Trim whitespace and compare tab/table names case-insensitively while
  preserving their original names in evidence.
- Tabs named `Architect Diagram` or `Architecture Diagram` describe the
  intended flow graph. Review their arrows, branches, and embedded images;
  they are informational and do not become workflows.
- XRef tabs and table entries supply reference lookup data, not workflows.
  Document lookup keys, values, consuming transformations, maintenance
  ownership, and behavior for missing or duplicate keys. An XRef table embedded
  in a processing tab does not make that whole tab informational.
- A processing tab whose tab or table name begins with `Source` is a flow
  starting point. Each starting point requires a sample helper script to send
  sanitized Input messages to its Service Bus ingress queue.
- Every non-informational tab maps to one distinct workflow in the Logic App
  Standard app. Do not merge processing tabs into one workflow. Classify any
  additional informational tabs explicitly and resolve ambiguous tabs before
  approving the design.
- Cells aligned under Input are incoming-message examples; transformation
  rules describe how to produce the corresponding Output. Preserve the
  header/cell alignment, including merged headers, rather than assuming fixed
  column positions. Derive sanitized input/output fixtures and validation
  expectations from these examples.
- Determine inter-tab edges from the reviewed architecture and matching
  upstream Output/downstream Input, not tab order. Record conflicts or missing
  links as assumptions that must be confirmed before implementation.
- Describe one workflow per processing tab in the design plan. Record its
  generic sheet label, XRef dependencies, input queue or topic/subscription,
  input/output formats, transformation steps, output topic, and consumers.
  Include every broker entity and its identity access scope in the plan.

## Service Bus handoffs and Source helpers

Service Bus is required for communication between processing tabs in this lab:

- A Source helper publishes to its starting workflow's ingress queue.
- Each workflow receives and locks its Input message, validates it, applies
  the tab's transformation and lookups, validates Output, and publishes that
  Output to the approved topic.
- Publish to topics, not directly to subscriptions. Each downstream workflow
  receives from its own subscription. Diagram fan-out requires independent
  subscriptions, not competing receivers on a shared queue.
- Record topic, subscription, routing properties, and filters for every edge.
  Ensure filters deliver each intended copy without unintended default-rule
  matches. The final tab also publishes Output; identify the approved mock
  consumer or mock target adapter without inventing another workbook workflow.
- Complete the Input only after Output publication succeeds. Failed
  publication must not acknowledge the Input. Document lock renewal,
  retry/dead-letter limits, and duplicate handling for the case where
  publication succeeds but Input completion fails.
- Implement a helper for each Source starting point during workflow
  implementation. Parameterize namespace, ingress queue, and fixture path;
  document dependencies and invocation; use Microsoft Entra authentication;
  and set content type, message ID, and correlation ID. Report send failures
  explicitly and never print credentials or full payloads.
- Give the helper's operator only sender access to the approved ingress queue.
  Confirm network reachability from its execution environment without enabling
  public access merely to run the helper. Give the Logic App system identity
  receiver access to its input entities and sender access to its output topics.
  These are site-level identity grants, not per-workflow identity isolation;
  keep connections and triggers mapped to the approved entities.

## Service selection

Select only services justified by the approved flow:

| Need | Preferred workshop service |
|---|---|
| Orchestration and protocol mediation | Private Logic App Standard |
| API gateway, policy, or stable ingress | API Management, explicitly selected as `none`, `new`, or `existing` |
| Source ingress and inter-tab message handoffs | Service Bus ingress queues and output topics with downstream subscriptions, deliberate settlement, and dead-letter behavior |
| File landing or archive | Storage account with private connectivity and managed identity |
| Secrets for a non-Azure system | Key Vault reference; never an IaC value or output |
| Correlated operations | Application Insights |

Service Bus is justified by this lab's required inter-tab handoffs. Do not add
extra brokers, gateways, databases, Key Vaults, or file stores merely because
they are available. XRef entries alone do not require a database: choose a
reviewed lookup artifact unless confirmed requirements justify a store.
Explain rejected alternatives and cost-bearing resources.

## Logic App hosting and identities

Every implemented design uses the complete private Logic App Standard baseline.
The host-storage user-assigned identity remains limited to host storage. The
Logic App system identity receives separate least-privilege roles on each Azure
workload resource.

External systems are mocked in this lab using sanitized fixtures and mock
endpoints or consumers. Do not require real external-system accounts,
credentials, or production data to complete the lab.

In an actual environment, replace the mocks with connections to the actual
source and target systems. Confirm endpoint ownership, supported authentication,
network access, and payload expectations before connecting. Prefer managed identity
where supported. If an external-system secret is unavoidable, store it in Key
Vault, grant the Logic App system identity only the required secret access, and
use a Key Vault reference. Never commit or output the secret.

When an approved design disables public access to an Azure workload service,
create the complete private endpoint, private DNS zone, VNet link, and DNS zone
group needed by the VNet-integrated Logic App. A private endpoint alone is not
a working data path.

## Transformation implementation

- Translate DataWeave or other source-platform expressions into Logic Apps
  operations, Liquid maps, JavaScript, or a small tested helper only after
  documenting the chosen runtime and tradeoff.
- Do not claim semantic equivalence from syntax conversion alone.
- Commit sanitized source, canonical, target, and error fixtures.
- Keep final fixtures, tests, helper scripts, workflow definitions, and IaC
  alongside the implementation, not in the intermediate `plans/` folder.
- Test defaults, null handling, conditionals, lookups, type conversions, date
  formatting, array cardinality, and required-field failures found in the
  workbook.
- Test each processing tab's Input-to-Output mapping independently, then test
  that its published Output satisfies each downstream tab's Input expectations.
- Do not log full payloads or sensitive field values.

## Reliability and validation

The approved proposal must make these behaviors explicit before resource
implementation:

- synchronous or asynchronous acceptance;
- timeout and retry boundaries;
- idempotency or duplicate handling;
- message lock, completion after publication, abandon, and dead-letter behavior
  at each Service Bus handoff;
- partial failure and replay behavior for fan-out;
- target error mapping;
- correlation propagation; and
- poison-input quarantine or support workflow.

Define input/output validation and tests from sanitized workbook examples.
The workbook alone is not a runtime specification. Do not recreate the removed
`contracts/` folder. Validate Source helper publication,
per-tab transformations, XRef misses, routing/fan-out, failed publication,
duplicate delivery after failed settlement, and end-to-end correlation without
logging full payloads.

## Implementation sequence

1. **Propose and approve:** reference a local workbook, extract and review its
   evidence, apply the workbook interpretation rules, resolve conflicts, and
   approve the design in `plans/integration-design.md`.
2. **Implement:** initialize one IaC track, implement the approved solution,
   review the deployment preview before deploying, and prove end-to-end and
   failure behavior using Source helpers, sanitized fixtures, and mocks.

Within Task 2, implement the hosting foundation before integration resources
and workload access, then workflows and tests. These are implementation
dependencies, not additional student tasks. Real external-system connections
are outside the lab scope.

Before implementation edits, state the resource graph, identity boundaries,
expected files, cost-bearing resources, and validation commands. Keep all work
within the approved design.

## Cleanup ownership

The proposal must identify new versus existing resources. Existing resources
are references and must not be imported, retagged, modified, replaced, or
deleted unless the approved design explicitly grants that ownership. Cleanup
must remove only Lab 3-owned resources.
