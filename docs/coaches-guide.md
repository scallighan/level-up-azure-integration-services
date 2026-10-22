# Coaches guide

This guide is for coaches helping learners during the workshop. Use it with the
[instructor guide](instructor-guide.md), the
[Copilot working agreement](copilot-working-agreement.md), and the active lab
README. Coaches help learners reason from contracts, deployment previews, and
test results instead of taking over their keyboard or supplying a finished
solution.

## Coach responsibilities

- Keep learners on the current checkpoint and one bounded change at a time.
- Ask learners to explain the resource graph, identities, and expected preview
  before they deploy.
- Help learners give Copilot exact files, constraints, and error output.
- Protect secrets, callback URLs, Terraform state, and local configuration.
- Stop unsafe changes to authentication, TLS, networking, RBAC, or an existing
  API Management service.
- Ensure Bicep and Terraform learners reach behaviorally equivalent outcomes.
- Track cost-bearing resources and confirm cleanup before learners leave.

Do not silently fix a learner's code. Prefer a question, a small hint, or a
command that produces evidence. Take control only to prevent secret exposure,
destructive deployment, or use of the wrong Azure subscription.

## Before learners arrive

1. Complete [Lab 0](../labs/00-foundation/README.md) using the same workstation
   constraints as learners.
2. Read `AGENTS.md`, `.github/copilot-instructions.md`, all lab READMEs, all
   committed contracts, and
   [`logic-app-standard-baseline.md`](logic-app-standard-baseline.md).
3. Review the current
   [Bicep](https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep)
   and
   [Terraform](https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform)
   Logic App reference implementations.
4. Confirm the intended Azure subscription and regions can create the required
   resource types and role assignments.
5. Explain that Windows WS1 Workflow Standard plans, private endpoints, Service
   Bus Standard, Application Insights, Cosmos DB, and optional API Management
   can incur cost.
6. Run:

   ```bash
   ./scripts/check-prereqs.sh bicep "$AZURE_LOCATION"
   # or: ./scripts/check-prereqs.sh terraform "$AZURE_LOCATION"
   ./scripts/validate-workshop.sh
   ```

Have a plan for learners who cannot deploy. They can still complete contract
review, IaC generation, formatting, compilation or validation, deployment
preview review, and cross-track comparison.

## Coaching loop

Use the same sequence at every checkpoint:

1. **Orient:** ask what bounded outcome the checkpoint requires.
2. **Predict:** have the learner draw or describe the resource and identity
   changes they expect.
3. **Prompt:** ensure Copilot was given the repository instructions, active lab
   README, contract, and Logic App Standard baseline.
4. **Inspect:** review generated changes before running a deployment command.
5. **Validate:** use the native formatter, compiler or validator, and deployment
   preview.
6. **Test:** verify the API or event contract, not only provisioning success.
7. **Explain:** ask the learner to describe why the result is safe and how it
   fails.
8. **Commit or continue:** preserve a working checkpoint before adding another
   concern.

Good coaching questions include:

- What resource or behavior does this checkpoint add?
- Which identity calls this service, and at what RBAC scope?
- Where could a secret or callback URL appear?
- What should the deployment preview contain, and what must it not contain?
- What happens if this request or message is retried?
- Which test proves the integration works?

## Logic App Standard guardrails

Every lab uses the mandatory private Logic App Standard hosting baseline. Stop
and correct the design if a generated solution uses a Consumption workflow or
omits any of these responsibilities:

- the reference VNet and four-subnet layout;
- separate blob, queue, table, and file storage private endpoints;
- corresponding private DNS zones, VNet links, and DNS zone groups;
- keyless Logic App host storage using a user-assigned identity;
- Blob, Queue, and Table Data Contributor roles for that identity;
- a Windows WS1 Workflow Standard plan;
- a `functionapp,workflowapp` site with system- and user-assigned identities;
- delegated-subnet integration and route-all outbound traffic; and
- the reference host settings and resource dependencies.

The user-assigned identity is for host storage. The system-assigned identity is
for the lab workload: Cosmos DB in Lab 1, and the assigned Service Bus
subscription plus the `orders` Cosmos container in Lab 2.
Lab 3 derives workload roles from the approved design
and keeps each role at the narrowest individual resource scope.

Lab 0 owns the single shared foundation, including Cosmos and the Service Bus
namespace. Ask students about an existing parent group; only a blank answer
creates a workshop group. Existing group metadata and unrelated resources must
stay untouched, including during cleanup. Verify the explicit handoff before
later labs; never infer a new-foundation mode or silently migrate learner state.

Lab 2 adds three independently deployable workflows in that site, three
subscription-scoped receiver grants, and a Cosmos contributor grant scoped
only to its new `orders` container. Stop namespace/topic receiver grants.
The publishing student reuses Lab 0's namespace-scoped Data Sender grant with
Entra authentication. This workshop convenience does not broaden workflow
receiver scopes; recommend entity-scoped publishers for production.
Preserve other labs' app-level connection entries and workflows;
do not let a later deployment replace the shared parent's settings.

## Lab 0 coaching map

- Compare the provided Bicep and Terraform graphs, not generated foundations.
- Check WS1 quota before previewing; account for five private endpoints and
  monitoring costs.
- Review both identity boundaries and the container-scoped Cosmos grant.
- Confirm Service Bus Standard uses a public endpoint with SAS disabled;
  Premium is the production private-networking alternative.
- Run `bash scripts/verify-foundation.sh foundation.deployment.json`.
- Confirm the handoff, parent-group selection, and cleanup ownership are saved.

## Lab 1 coaching map

### Task 1: prepare the lookup data and connection

- Run `python3 scripts/prepare-lab1.py foundation.deployment.json`.
- Explain why the temporary seed workflow, not the workstation, reaches private
  Cosmos DB. It uses the site's existing system identity and container grant.
- Check that only the six `lab01-region-*` and three `lab01-support-*` records
  are upserted and the helper workflow is removed. Other workflows and connections
  must remain.
- The sample is public Azure region data, not customer cross-reference content.
  Each region includes a display name and physical location. The separate
  support tiers are fictional teaching values, not Azure support plans.

### Task 2: generate the workflow

- Give Copilot the README's short prompt and the committed contract.
- Reference Lab 0 without creating or modifying hosting, Cosmos, networking,
  identities, or roles. Add no website or API Management.
- Use two `ReadDocument` actions, each with its prefixed ID as both document
  ID and partition key: `lab01-region-<programmaticName>` and
  `lab01-support-<supportTier>`.
- Reuse `lab01Cosmos`, managed identity, and the `accountURI` connection shape.
- Deploy artifacts through `deployWorkflowArtifacts`, preserving other labs.
- Put two fixed `PT5S` read retries under `inputs`; handle `NotFound` using the
  action's `code`. Do not return connector diagnostics or full document data.

### Tasks 3-4: test the transformation

- `westus` resolves to `West US` / `California`; `westeurope` resolves to
  `West Europe` / `Netherlands`.
- `standard` adds `Standard` / `8` hours; `priority` adds `Priority` / `1` hour.
  Change one key at a time to prove the lookups are independent.
- Only the seeded subset is supported. An unseeded name returns `404`, not a
  default location or a successful partial response.
- Missing, invalid, or extra fields return the contracted `400` JSON error.
- All five request fields pass through unchanged. Add region and support
  details from Cosmos; no placeholder output fields belong in the request.
- Return only the nine contracted fields; do not expose the document ID or
  Cosmos metadata. This exercise transforms JSON, not Azure resources.
- Inspect a run to prove both Cosmos reads occurred; do not accept hardcoded mappings.
- Protect the callback URL. Show public samples in run history by default;
  require `show_sample_payloads=false` before using real or sensitive data.
- Remove only the learner's workflow and unused connection during cleanup.

## Lab 2 coaching map

### Checkpoint 0: reference Lab 0

**Learner should explain**

- Why Lab 0 is mandatory even if Lab 1 was skipped.
- Which deployed Lab 0 resources are referenced through the handoff.
- Why Lab 2 cleanup cannot delete the parent group, namespace, or site.

**Coach checks**

- Explicit references identify the integration subnet, host storage,
  host identity, WS1 plan, monitoring, site, namespace, and Cosmos account/database.
- The preview never modifies, imports, retags, replaces, or deletes reused
  resources.

### Checkpoint 1: integration infrastructure

**Learner should explain**

- Why Service Bus Standard is required for topics.
- How each known event reaches audit and one specialist, while a future event
  type reaches audit only.
- How `MessageId`, duplicate detection, lock duration, maximum delivery count,
  and TTL interact.
- Why one site identity needs three subscription-scoped roles and why namespace
  scope is too broad.
- Why a separate container and container-scoped Cosmos grant protect Lab 1 data.

**Coach checks**

- The topic is `orders`.
- Subscriptions are exactly `audit`, `order-created`, and `order-cancelled`.
- Named SQL rules are `1 = 1` for audit, `eventType = 'order.created'` for
  creation, and `eventType = 'order.cancelled'` for cancellation. Add the named
  rule before removing `$Default`; each subscription retains exactly one rule.
- Required tags are `workshop=agentic-ais` and `lab=02`.
- The selected Logic App Standard site is part of the resolved foundation.
- Its system identity has one receiver assignment per subscription.
- The new `orders` NoSQL container uses `/id`, with a container-scoped Cosmos
  contributor grant; existing `items`, networking, and throughput are unchanged.
- No workflow definition is present yet.

### Checkpoint 2: isolated receiver workflows

**Learner should explain**

1. Receive and lock.
2. Parse and validate.
3. Process inside a scope.
4. Complete only after success.
5. Abandon or preserve dead-letter behavior after failure.

**Coach checks**

- All three workflows are deployed to the selected Logic App Standard site.
- Each workflow references only its assigned Service Bus subscription.
- Connections use managed identity rather than a namespace connection string.
- Audit accepts the common envelope for any event type; specialists validate
  their own contracts and never discard unrelated events after receipt.
- Creation persists the actual order; cancellation reads and updates it while
  preserving original fields. Both read back and assert the stored result.
- Duplicate creation cannot reset a cancelled order. Missing-order cancellation
  fails and retries. Cross-subscription ordering is not guaranteed.
- All three workflows default `show_sample_payloads` to `true` for the
  sanitized sample event. Sensitive customer data must use protected mode.
- Retry and timeout behavior is explicit.

### Checkpoint 3: route two event types

Run `python3 scripts/test-lab2.py`. Predict the routing matrix before sending:
each of three creations reaches audit and order-created, then one cancellation
reaches audit and order-cancelled. Expect four publications and eight copies
(four audit, three creation, one cancellation), with no cross-routed specialist
runs. The helper waits for all three creations before cancelling only the first
order. It verifies persisted-state assertions, not just provisioning or run
status.
The bounded observation window is not a proof against every possible late run.
Check the exact broker rules too.

Check `ContentType`, `MessageId`, `CorrelationId`, `eventType`, and
`schemaVersion`. The three creations use distinct order IDs, and cancellation
reuses only the first order ID. All four events use fresh event and correlation
IDs. Confirm that the first order becomes `cancelled` without changing
customer/order fields and the other two stay `created`.
Send an unfamiliar event with a valid envelope to prove only audit receives it.
No workstation Cosmos grant or public access is needed.

### Checkpoint 4: failure isolation

Create an order, then fail only cancellation processing before its Cosmos
mutation. Audit must complete, creation must not receive the cancellation,
and only the cancellation copy must retry and dead-letter. The order stays
created. Ensure the deliberate failure is reverted.

Do not suggest automatically replaying dead-letter messages. Ask how a replay
tool would preserve diagnostics and identifiers while preventing an infinite
poison-message loop.

## Lab 3 coaching map

### Task 1: propose and approve the Azure design

**Learner should explain**

- Which sheets and cells establish each source, target, payload, transform,
  response, and error conclusion.
- Why `Architect Diagram` / `Architecture Diagram` tabs define flow guidance,
  XRef entries supply lookup data, and Source-prefixed tabs or tables identify
  starting points.
- How aligned Input, Transformation rule, and Output cells define each
  processing tab's mapping, and how diagram arrows match Output to next Input.
- Which workbook images were reviewed separately.
- Which workbook conflicts or missing links block approval of the flow.

**Coach checks**

- The workbook was extracted locally and was not uploaded to an external
  service.
- Facts and assumptions are visibly separate.
- Every tab is classified; architecture and XRef information do not create
  workflows, and ambiguous diagram links are resolved before approval.
- Customer or production payloads are not being committed.
- All intermediate artifacts stay in the Git-ignored Lab 3 `plans/` folder;
  Task 1 creates only extracted evidence/images, the concise summary, and its SVG.
- The summary contains a verdict, tab/cell table, message-flow graph, actual
  issues/evidence table, and a brief limitations note. It is not a deployment
  dossier and does not invent missing behavior or technical defaults.
- Original names and values may remain in ignored plans; only artifacts intended
  for Git require scrubbing. Secrets remain excluded from planning artifacts.
- `plans/integration-design.svg` is legible, matches the written plan, and shows
  message direction and unresolved links, not infrastructure or RBAC panels.
- Every non-informational tab has its own flow/workflow; Source helpers send
  to ingress queues and inter-tab edges use topics and downstream subscriptions.
- Publishers send to topics, not subscriptions; fan-out uses independent
  subscriptions and XRef data is identified as reference data, not a workflow.
- IaC initialization does not begin until workbook/flow conflicts are resolved and
  `plans/integration-design.md` begins with `Status: approved`.
- External credentials are neither invented nor placed in the proposal.

### Task 2: implement the approved design

Resolve hosting, networking, RBAC, cost, ownership, and operational decisions
here before resource implementation. Keep the decision summary brief and
reference the baseline instead of repeating it; flow approval alone is not
deployment approval. The host-storage user-assigned identity remains limited to
host storage; workload grants use the system identity at individual scopes.

Compare every planned resource with the approved flow. Stop additions that
are merely convenient rather than justified by a flow requirement. Require a
complete private endpoint and DNS path for every approved Azure service whose
public access is disabled.

Require sanitized fixtures for source, canonical, target, response, and error
shapes. Test workbook conditionals, defaults, null handling, lookups, dates,
types, and array behavior. A syntactically translated DataWeave expression is
not proof of equivalent behavior.

Require one workflow per processing tab and a documented sample helper for each
Source starting point. Run helpers with sender-only Microsoft Entra access from
an approved network path. Verify every upstream Output satisfies downstream
Input and that a workflow completes Input only after Output publication.
Include lookup misses and publication-success/settlement-failure duplicates.

Use mocked external systems only. Show sanitized fixtures in run history by
default with `show_sample_payloads=true`; use protected mode for sensitive data.
Require success, invalid input, timeout, transient failure, permanent failure,
and correlation evidence using status and IDs in telemetry, not full payloads.
Review deployment and cleanup previews; existing shared resources must remain
untouched.

## Troubleshooting playbook

Always collect the exact command, exit code, error text, deployment operation,
and relevant resource ID before changing code.

| Symptom | Evidence to collect | Coaching direction |
|---|---|---|
| Bicep build fails | File, line, diagnostic code, and API version | Fix the smallest compiler error; do not guess a replacement property. |
| Terraform validation fails | Provider version, resource address, and full diagnostic | Compare with the pinned provider schema and reference implementation. |
| Preview contains replacements | Resource address, old/new name, scope, and changed property | Stop deployment and determine whether naming, `count`/`for_each`, or parent scope drifted. |
| Role assignment is not effective | Principal ID, role definition, scope, and assignment state | Confirm the correct identity and scope, then allow propagation time; never switch to a key. |
| Logic App cannot reach host storage | VNet integration, route-all setting, DNS resolution, endpoint state, role assignments, and host settings | Compare every item with the baseline; do not add a storage connection string. |
| Logic App cannot reach a workload service | System identity, workload RBAC, connection authentication, DNS/network path, and run error | Keep host-storage and workload identities separate. |
| Direct browser request fails | Browser network error, CORS headers, canonical body, workflow run, and HTTP response | Do not print or persist the callback URL while diagnosing. |
| Existing API Management preview is broad | Planned service and child-resource changes | Stop unless only workshop API-scoped resources are changing. |
| Service Bus message repeats | Delivery count, lock status, workflow action history, and completion path | Verify completion occurs only after successful processing and inspect the failure branch. |
| No workflow run appears | Topic/subscription counts, filter rule, application properties, and connection status | Trace broker routing before editing the workflow. |

If a property or API behavior remains uncertain, consult current Azure
documentation and state the uncertainty. Do not weaken networking,
authentication, TLS, or authorization to make a deployment pass.

## Hint ladder

Use the least-direct intervention that gets the learner moving:

1. Ask the learner to restate the expected behavior.
2. Point to the relevant contract, baseline section, or preview resource.
3. Ask for a focused Copilot explanation of the exact code or error.
4. Suggest one read-only diagnostic command or portal view.
5. Identify the mismatched resource, identity, scope, or contract field.
6. Demonstrate the smallest correction only after the learner understands the
   cause.

Lab 0 deliberately provides finished foundation infrastructure. In later labs,
avoid pasting a complete integration into a learner's branch. The goal is to
teach a repeatable engineering loop, not merely reach a green deployment.

## Escalation and safety

Stop and involve the lead instructor when:

- the selected subscription or tenant is unclear;
- a preview deletes or replaces an existing shared resource;
- an existing API Management service shows service-wide changes;
- credentials, keys, connection strings, callback URLs, or Terraform state may
  have been committed or shared;
- the learner lacks permission to create role assignments;
- Azure service availability or quota blocks multiple learners; or
- a cleanup command could target resources outside the lab.

If secret material was exposed, stop using it, follow the organization's
incident process, rotate or revoke it, and remove it from the learner workflow.
Deleting a visible line from the latest commit is not sufficient remediation.

## Cleanup sign-off

Before a learner leaves, confirm:

- the deletion or destroy preview targets only workshop resources;
- existing API Management mode removes only workshop-owned child resources;
- lab-owned additions and artifacts are gone before Lab 0 cleanup;
- an existing parent group and unrelated resources remain; a Lab 0-created
  group is deleted only after reviewing all remaining contents;
- no Terraform state or plan file was committed;
- no callback URL or local configuration was committed; and
- no deliberately failing workflow remains deployed.

Record unresolved resources with subscription, resource group, owner, and
follow-up time so cost cleanup has a clear owner.
