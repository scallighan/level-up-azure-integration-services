---
description: Build the CRUD lab incrementally with Terraform
---

Read `.github/copilot-instructions.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/01-crud-integration/README.md`, and
`labs/01-crud-integration/contracts/openapi.yaml`.

Work only on the next incomplete checkpoint in the Terraform track. Before
editing, summarize the resource graph, identity flow, variables, outputs, and
validation command for that checkpoint. Pin provider constraints and prefer
AzureRM resources; use AzAPI only when AzureRM cannot represent the required
Logic App or API Management behavior, and document that decision. Use managed
identity for Logic Apps access to Cosmos DB. Never output or commit a callback
URL, state, or plan file.
Replicate the Terraform reference's VNet and subnet layout, host storage
account, four storage private endpoints and DNS resources, storage RBAC,
Windows WS1 plan, dual identities, VNet routing, host settings, and deployment
dependencies. Do not substitute a Consumption Logic App. Use the
system-assigned identity for Cosmos DB and the user-assigned identity for Logic
App host storage.

Implement `api_management_mode` with validated values `none`, `new`, and
`existing`; default it to `none`. In `new` mode create APIM. In `existing` mode
require its name and resource group, read it from the current subscription, and
manage only the workshop API and API-scoped policies. In `none` mode create no
APIM resources. Add variable validation or preconditions for inconsistent
inputs.

After editing, run formatting and validation. Report remaining uncertainty
rather than guessing.
