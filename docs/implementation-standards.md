# Workshop implementation standards

These standards apply to every learner request in this repository. Lab READMEs
provide the sequence of bounded tasks, while each lab's
`implementation-requirements.md` defines its resource responsibilities and
runtime behavior.

## Working boundaries

- Read the active lab README, implementation requirements, and contracts before
  proposing changes.
- Make one bounded change at a time and explain the intended resource graph
  before editing.
- Favor clear teaching code over abstraction.
- Keep Bicep and Terraform tracks behaviorally equivalent. Equivalent means the
  same resource responsibilities, identity boundaries, API or event contracts,
  tags, and non-secret outputs; syntax does not need to mirror line by line.
- Parameterize subscription-specific values, locations, prefixes, publisher
  details, and existing resource IDs.
- Use deterministic names plus an Azure-safe unique suffix where global
  uniqueness is required.
- Apply the tags `workshop=agentic-ais` and `lab=<lab-number>`.
- Use current stable Azure API versions and pinned Terraform provider version
  constraints. State uncertainty instead of inventing a property.
- Use the lowest practical workshop SKU and identify cost-bearing resources.
- Do not weaken networking, authentication, TLS, or authorization to make a
  deployment pass.

## Identity and secret handling

- Prefer managed identities and Azure RBAC over shared keys.
- Never place credentials, connection strings, callback URLs, access keys,
  populated local configuration, Terraform state, or Terraform plan files in
  source control.
- Do not expose secrets through Bicep or Terraform outputs.
- Use workflow managed identity for Azure data-plane access.
- Do not emit secrets or full sensitive payloads to Logic App run history.

## Logic App Standard

Every Logic App must use the private Logic App Standard resource graph in
[`logic-app-standard-baseline.md`](logic-app-standard-baseline.md). Before
creating or changing that infrastructure, read the baseline and its matching
implementation under
[`scallighan/logic-app-doc-processing`](https://github.com/scallighan/logic-app-doc-processing).

- Never substitute a Consumption Logic App.
- Use the reference Windows WS1 Workflow Standard plan. The plan and private
  endpoints are cost-bearing resources.
- Use the user-assigned identity only for keyless host-storage access.
- Keep the system-assigned identity for lab workload data-plane access.
- Make retry, timeout, duplicate, and failure behavior explicit.
- Return deliberate HTTP status codes in synchronous workflows.
- In Service Bus workflows, complete a message only after successful
  processing and preserve dead-letter behavior for repeated failures.

## Validation

For Bicep, run:

1. `az bicep format`
2. `az bicep build`
3. The appropriate `az deployment ... what-if` command

For Terraform, run:

1. `terraform fmt -check`
2. `terraform validate`
3. `terraform plan`

Validate workflow and API JSON or YAML syntax and test behavior against the
committed contract. After deployment, use Azure CLI queries and explicit test
requests; successful provisioning alone does not prove that the integration
works.
