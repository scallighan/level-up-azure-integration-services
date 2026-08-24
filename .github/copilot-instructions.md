# Repository instructions

This repository is a half-day workshop about building Azure Integration
Services with GitHub Copilot. Favor clear teaching code over abstraction.

## Required engineering behavior

- Read the active lab README and contract files before proposing changes.
- Make one bounded change at a time and explain the intended resource graph.
- Never place credentials, connection strings, callback URLs, access keys, or
  populated local configuration in source control.
- Prefer managed identities and Azure RBAC over shared keys.
- Keep Bicep and Terraform tracks behaviorally equivalent. Equivalent means the
  same resource responsibilities, identity boundaries, API/event contracts,
  tags, and non-secret outputs; syntax does not need to mirror line by line.
- Parameterize subscription-specific values, locations, prefixes, publisher
  details, and existing resource IDs.
- Use deterministic names plus an Azure-safe unique suffix where global
  uniqueness is required.
- Apply the tags `workshop=agentic-ais` and `lab=<lab-number>`.
- In Lab 1, model API Management as `none`, `new`, or `existing`, defaulting to
  `none`. Never create an APIM instance unless `new` is explicitly selected.
- When Lab 1 uses an existing APIM instance, add only the workshop API,
  operations, and API-scoped policies. Do not change service-wide settings.
- Use current stable Azure API versions and pinned Terraform provider version
  constraints. State any uncertainty instead of inventing a property.
- Use the lowest practical workshop SKU and identify cost-bearing resources.
- Do not weaken networking, authentication, TLS, or authorization to make a
  deployment pass.

## Validation

For Bicep, run `az bicep format`, `az bicep build`, and the appropriate
`az deployment ... what-if` command before deployment.

For Terraform, run `terraform fmt -check`, `terraform validate`, and
`terraform plan` before apply. Do not commit state or plan files.

For workflow and API JSON/YAML, validate syntax and test against the committed
contract. After deployment, use Azure CLI queries and explicit test requests;
do not treat a successful provisioning operation as proof that the integration
works.

## Logic Apps

- Use workflow managed identity for Azure data-plane access.
- Make retry, timeout, duplicate, and failure behavior explicit.
- Do not emit secrets or full sensitive payloads to run history.
- Return deliberate HTTP status codes in synchronous workflows.
- In Service Bus workflows, complete a message only after successful processing
  and preserve dead-letter behavior for repeated failures.
