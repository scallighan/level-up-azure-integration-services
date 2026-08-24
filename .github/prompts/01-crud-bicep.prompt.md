---
description: Build the CRUD lab incrementally with Bicep
---

Read `.github/copilot-instructions.md`,
`labs/01-crud-integration/README.md`, and
`labs/01-crud-integration/contracts/openapi.yaml`.

Work only on the next incomplete checkpoint in the Bicep track. Before editing,
summarize the resource graph, identity flow, parameters, outputs, and validation
command for that checkpoint. Use modules with a subscription-scoped entry point
only when needed to create the resource group. Use managed identity for Logic
Apps access to Cosmos DB. Never output or commit a Logic App callback URL.

Implement `apiManagementMode` with allowed values `none`, `new`, and `existing`;
default it to `none`. In `new` mode create APIM. In `existing` mode require its
name and resource group, reference it as an existing resource in the current
subscription, and deploy only the workshop API and API-scoped policies. In
`none` mode deploy no APIM resources. Reject inconsistent parameter
combinations with Bicep validation decorators or deployment-time validation.

After editing, run formatting and compilation. Report remaining uncertainty
about Azure API versions or service behavior rather than guessing.
