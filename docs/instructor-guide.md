# Instructor guide

## Audience and outcomes

This workshop is for developers, integration engineers, and cloud engineers who
know basic Azure concepts. Deep Logic Apps, Bicep, or Terraform experience is
not required.

By the end, participants can:

- give Copilot durable repository context and bounded task prompts;
- use Copilot to create equivalent Bicep or Terraform deployments;
- review generated IaC for identity, secrets, naming, cost, and idempotency;
- generate and test Logic App workflows from API and event contracts;
- diagnose deployments by grounding Copilot in exact command output; and
- derive an implementation contract from workbook evidence and explicit
  assumptions; and
- manage the deployed solutions through safe previews and cleanup.

In-room helpers should also read the
[coaches guide](coaches-guide.md), which provides checkpoint questions, a hint
ladder, troubleshooting guidance, and cleanup sign-off criteria.

## Facilitation plan

| Time | Activity | Teaching point |
|---:|---|---|
| 0:00 | Lab 0 and architecture overview | Deploy the reviewed shared foundation, not generated infrastructure |
| 0:45 | Lab 1 and context demonstration | Seed a lookup table, then generate a synchronous transformation |
| 1:45 | Break | Compare request and response contracts |
| 2:00 | Lab 2 | Asynchronous fan-out and independent failure |
| 3:15 | Cross-track review | Compare Bicep and Terraform resource graphs |
| 3:30 | Cleanup and discussion | Remove lab additions before the shared foundation |
| Optional extension | Lab 3, 90-150 minutes | Design from workbook evidence |

## Pairing model

Pair participants using different IaC tracks when possible. At each checkpoint,
have pairs compare resource graphs and outputs rather than syntax. The deployed
behavior should match even when implementation details differ.

## Checkpoints

**Lab 0**

- Ask each student whether they have an existing parent resource group.
- Review the committed Bicep or Terraform preview; an existing group and its
  unrelated resources must remain untouched.
- Check WS1 quota, all five private endpoints/DNS paths, keyless identities,
  Cosmos RBAC, Service Bus Standard/Entra auth, and wired monitoring.
- Save `foundation.deployment.json` and make cleanup ownership explicit.
- Do not deploy both tracks or silently migrate earlier learner state.

**Lab 1**

- The OpenAPI contract is valid and Lab 0 references resolve without writes.
- The provided script seeds six public Azure region records and three synthetic
  support-tier records through a temporary workflow in the existing site;
  Cosmos stays private.
- The learner generates the lookup workflow from the short prompt, not a
  supplied complete solution. There is no CRUD API, website, or APIM task.
- The Logic App identity, not a shared key, accesses Cosmos DB.
- All five request fields pass through unchanged. Region and support-tier keys
  independently add lookup-derived details; no output placeholders are sent.
  Missing mappings and invalid requests return deliberate errors.

**Lab 2**

- Lab 0's site and namespace are existing references, not Lab 2-owned parents.
- The publishing student reuses Lab 0's namespace-scoped Entra Data Sender
  grant; workflow receiver grants remain subscription-scoped.
- One topic has three subscriptions with explicit filters.
- Each workflow uses its own subscription.
- A workflow failure does not prevent the other subscriptions from processing.
- Duplicate handling and dead-letter behavior are discussed before testing.

**Lab 3**

- Workbook facts cite sheets and cells; assumptions are visibly separate.
- Intermediate artifacts stay in the Lab 3 `plans/` folder; its design plan
  is a concise tab/cell mapping, message flow, and issues summary with a simple
  SVG. Review and approve the flow before IaC initialization. Local plans may
  retain original names and values; committed artifacts are scrubbed.
- Hosting, networking, RBAC, cost, and operational choices are resolved in
  Task 2 before resource implementation, not expanded into the Task 1 report.
- Selected Azure services map to confirmed requirements rather than workbook
  product names alone.
- DataWeave behavior is covered by sanitized transformation fixtures and tests.
- External systems are mocked; Task 2 confirms and tests expected success and
  failure behavior.

## Recovery strategies

- If seed execution fails, inspect the reported workflow/run and the existing
  private endpoint and system-identity grant. Do not enable public Cosmos
  access or grant account-key access as a shortcut.
- If role assignments have not propagated, inspect the principal and scope,
  wait briefly, and retry; do not replace managed identity with an account key.
- If a generated resource type is unsupported by the Terraform AzureRM
  provider, use the AzAPI provider deliberately and document why.
- If deployment is blocked, complete the preview and code-review checkpoints.
  Do not turn a workshop delay into an unsafe production pattern.

## Production-hardening discussion

The workshop uses a temporary HTTP trigger callback URL in a local test client
and is not a production architecture. Discuss an API gateway,
Microsoft Entra authorization, private endpoints, custom domains and
certificates, rate limits, WAF, centralized observability, deployment
environments, remote Terraform state, test automation, and workload-specific
disaster recovery.
