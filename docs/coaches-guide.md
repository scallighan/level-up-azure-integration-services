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

1. Complete [`prerequisites.md`](prerequisites.md) using the same workstation
   constraints as learners.
2. Read `AGENTS.md`, `.github/copilot-instructions.md`, both lab READMEs, all
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
   ./scripts/check-prereqs.sh
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
for the lab workload: Cosmos DB in Lab 1 and the assigned Service Bus
subscription in Lab 2.

For Lab 2, learners explicitly create a new shared hosting foundation or
reference the compatible foundation from Lab 1. Existing resources remain
owned by Lab 1 and must not appear as managed or deleted in the Lab 2 preview.
In either mode, learners create three separate Lab 2-owned Logic App Standard
workflows in one selected Logic App Standard site. The site's system identity
receives three separate subscription-scoped roles; do not allow topic- or
namespace-scoped receiver access. In existing mode, Lab 2 may add child
workflows and its own role assignments but must not manage the Lab 1 parent
site.

## Lab 1 coaching map

### Checkpoint 1: contract and resource graph

**Learner should explain**

- All CRUD operations and deliberate HTTP statuses in `openapi.yaml`.
- The canonical backend request containing `operationId`, optional item ID,
  body, and correlation ID.
- The Logic App Standard hosting foundation and identity boundaries.

**Coach checks**

- `none` is the default and creates no API Management resources.
- Names, locations, prefixes, publisher details, and existing resource
  references are parameterized.
- Required tags are `workshop=agentic-ais` and `lab=01`.
- No secrets or callback URLs appear in parameters, variables, or outputs.

**Useful hint**

> Compare the preview with the target resource graph one resource type at a
> time. Do not add the data or workflow checkpoint yet.

### Checkpoint 2: data and workflow

**Learner should explain**

- Why `/id` is the partition key for this workshop.
- Which Cosmos DB data-plane role is assigned to the Logic App system identity
  and at what scope.
- How each operation maps contract errors and success responses to HTTP
  statuses.
- Which writes can be repeated and how retry behavior is controlled.

**Coach checks**

- Cosmos local authentication is disabled.
- Host storage uses the user-assigned identity and keyless app settings.
- Cosmos DB access uses the Logic App system identity.
- The callback URL is not an IaC output.
- The Standard site waits for its plan, host-storage roles, and private
  endpoints.

### Checkpoint 3: direct frontend path

- The learner retrieves the callback URL only for the current exercise.
- The URL is not written to source, shell scripts, outputs, logs, or browser
  local storage.
- CORS allows only the deployed Static Web App origin.
- The workflow handles preflight and the canonical request shape.

### Coach-led API Management extension

API Management is not part of the learner path. Offer this extension only when
the core direct flow works and the group has enough time. Keep the three modes
consistent across both IaC tracks:

| Mode | Behavior |
|---|---|
| `none` | Default. Creates no API Management resources. |
| `new` | Creates a workshop API Management instance, API, operations, and API-scoped policies. |
| `existing` | References an instance in the current subscription and creates only workshop-owned child resources. |

Use these matching inputs:

| Bicep | Terraform | Requirement |
|---|---|---|
| `apiManagementMode` | `api_management_mode` | `none`, `new`, or `existing`; default `none` |
| `existingApimName` | `existing_apim_name` | Required only for `existing` |
| `existingApimResourceGroupName` | `existing_apim_resource_group_name` | Required only for `existing` |

**New instance checks**

- The learner explicitly selected `new`.
- The preview includes a new low-cost workshop instance and required child
  resources.

**Existing instance checks**

- The learner supplied the existing name and resource group.
- The preview adds only the workshop API, operations, and API-scoped policies.
- No service-wide policy, hostname, certificate, identity, diagnostic, SKU, or
  network setting changes.

For either API Management path, import `contracts/openapi.yaml`, map every
operation to the canonical backend request, and apply:

- a correlation ID when the client did not provide one;
- JSON content-type enforcement for writes;
- a small workshop rate limit;
- removal of backend-only headers from responses; and
- CORS restricted to the deployed Static Web App hostname.

Inspect policy XML for callback URL exposure and verify every OpenAPI operation
is mapped. In `existing` mode, stop if the preview replaces the service or
changes service-wide policy, hostnames, certificates, identity, diagnostics,
SKU, or networking.

Example existing-instance inputs:

```bash
# Bicep
--parameters apiManagementMode="existing" \
  existingApimName="<apim-name>" \
  existingApimResourceGroupName="<apim-resource-group>"

# Terraform
-var="api_management_mode=existing" \
-var="existing_apim_name=<apim-name>" \
-var="existing_apim_resource_group_name=<apim-resource-group>"
```

Use the API Management test console or contract-derived requests to prove
create, list, get, update, and delete return the expected statuses. During
cleanup, `existing` mode must remove only workshop API resources and never the
API Management instance.

### Checkpoint 4: end-to-end test

Require create, list, get, update, and delete evidence. A successful deployment
is not evidence that the contract works. Ask the learner to correlate one
request across the available telemetry and explain unexpected status codes
from the exact response body.

## Lab 2 coaching map

### Checkpoint 0: shared hosting foundation

**Learner should explain**

- Why `new` is required when Lab 1 was skipped or cleaned up.
- Which deployed Lab 1 resources are referenced by `existing`.
- Which resources Lab 2 owns and what its cleanup is allowed to delete.

**Coach checks**

- The mode is explicit rather than inferred from repository or Azure state.
- Existing mode references a compatible integration subnet, host storage,
  host-storage identity, WS1 plan, and observability foundation.
- The preview never modifies, imports, retags, replaces, or deletes reused
  resources.

### Checkpoint 1: integration infrastructure

**Learner should explain**

- Why Service Bus Standard is required for topics.
- How one published message becomes three independent subscription copies.
- How `MessageId`, duplicate detection, lock duration, maximum delivery count,
  and TTL interact.
- Why one site identity needs three subscription-scoped roles and why namespace
  scope is too broad.

**Coach checks**

- The topic is `orders`.
- Subscriptions are exactly `audit`, `fulfillment`, and `notification`.
- `$Default` is removed before the `eventType = 'order.created'` SQL rule is
  added.
- Required tags are `workshop=agentic-ais` and `lab=02`.
- The selected Logic App Standard site is part of the resolved foundation.
- Its system identity has one receiver assignment per subscription.
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
- Full event payloads and sensitive customer data are not emitted to run
  history.
- Retry and timeout behavior is explicit.

### Checkpoint 3: publish one event

Before sending, ask the learner to predict active message counts and workflow
runs. Check `ContentType`, `MessageId`, `CorrelationId`, `eventType`, and
`schemaVersion`. All three workflows should process one copy with the same
event and correlation IDs.

### Checkpoint 4: failure isolation

Allow only the notification processing scope to fail. Confirm audit and
fulfillment complete, notification delivery count increases independently, and
only the notification copy reaches its dead-letter queue. Ensure the deliberate
failure is reverted.

Do not suggest automatically replaying dead-letter messages. Ask how a replay
tool would preserve diagnostics and identifiers while preventing an infinite
poison-message loop.

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

Avoid pasting complete finished infrastructure into a learner's branch. The
goal is to teach a repeatable engineering loop, not merely reach a green
deployment.

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
- the lab resource group is gone;
- no Terraform state or plan file was committed;
- no callback URL or local configuration was committed; and
- no deliberately failing workflow remains deployed.

Record unresolved resources with subscription, resource group, owner, and
follow-up time so cost cleanup has a clear owner.
