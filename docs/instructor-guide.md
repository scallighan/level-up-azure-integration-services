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
- manage the deployed solutions through safe previews and cleanup.

In-room helpers should also read the
[coaches guide](coaches-guide.md), which provides checkpoint questions, a hint
ladder, troubleshooting guidance, and cleanup sign-off criteria.

## Facilitation plan

| Time | Activity | Teaching point |
|---:|---|---|
| 0:00 | Welcome and architecture overview | Copilot is a collaborator, not an authority |
| 0:15 | Context and prompt demonstration | Repository instructions beat repeated prose |
| 0:30 | Lab 1 | Contract-first synchronous integration |
| 2:00 | Break | Compare direct and APIM modes |
| 2:15 | Lab 2 | Asynchronous fan-out and independent failure |
| 3:30 | Cross-track review | Compare Bicep and Terraform resource graphs |
| 3:45 | Cleanup and discussion | Cost, security, and production hardening |

## Pairing model

Pair participants using different IaC tracks when possible. At each checkpoint,
have pairs compare resource graphs and outputs rather than syntax. The deployed
behavior should match even when implementation details differ.

## Checkpoints

**Lab 1**

- The OpenAPI contract is valid before infrastructure work begins.
- The selected API mode is explicit: direct, new APIM, or existing APIM.
- APIM modes expose operations without revealing the Logic App callback URL.
- The Logic App identity, not a shared key, accesses Cosmos DB.
- Create, read, update, and delete tests each return an expected status.

**Lab 2**

- One topic has three subscriptions with explicit filters.
- Each workflow uses its own subscription.
- A workflow failure does not prevent the other subscriptions from processing.
- Duplicate handling and dead-letter behavior are discussed before testing.

## Recovery strategies

- If new APIM provisioning is slow, switch to direct mode or point the
  deployment at a prepared existing instance. Never replace or reconfigure the
  existing APIM service itself.
- If role assignments have not propagated, inspect the principal and scope,
  wait briefly, and retry; do not replace managed identity with an account key.
- If a generated resource type is unsupported by the Terraform AzureRM
  provider, use the AzAPI provider deliberately and document why.
- If deployment is blocked, complete the preview and code-review checkpoints.
  Do not turn a workshop delay into an unsafe production pattern.

## Production-hardening discussion

The lowest-cost direct mode intentionally exposes a temporary callback URL to
the browser and is not a production architecture. Discuss an API gateway,
Microsoft Entra authorization, private endpoints, custom domains and
certificates, rate limits, WAF, centralized observability, deployment
environments, remote Terraform state, test automation, and workload-specific
disaster recovery.
