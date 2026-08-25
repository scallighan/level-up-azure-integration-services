---
description: Create the Lab 1 Terraform starter structure and local instructions
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/01-crud-integration/README.md`, and
`labs/01-crud-integration/implementation-requirements.md`, and
`labs/01-crud-integration/contracts/openapi.yaml`.

Initialize only `labs/01-crud-integration/iac/terraform/` for the Terraform
learner path. Before editing, show this starter structure and briefly explain
each file:

```text
labs/01-crud-integration/iac/terraform/
├── AGENTS.md
├── main.tf
├── outputs.tf
├── providers.tf
├── variables.tf
└── versions.tf
```

Create minimal base files only. Pin the Terraform and AzureRM provider
constraints in `versions.tf`; configure the AzureRM provider with its required
features block in `providers.tf`; and add short file-level teaching comments to
`main.tf`, `variables.tf`, and `outputs.tf`. Do not add variables, resources,
data sources, locals, outputs, backend configuration, or placeholder blocks.

Create the path-local `AGENTS.md` with concise instructions that:

- identify this directory as the Lab 1 Terraform track;
- require the repository instructions, implementation standards, Lab 1 README,
  implementation requirements, OpenAPI contract, Logic App Standard baseline,
  and matching Terraform reference before changes;
- keep each learner request bounded to the named lab task;
- preserve the host-storage user-assigned identity and Cosmos workload
  system-assigned identity boundary;
- prohibit secrets, callback URLs, Terraform state or plan files, populated
  variable files, and changes to any `iac/.gitignore`;
- prefer AzureRM and allow AzAPI only when AzureRM cannot represent required
  behavior, with the reason documented; and
- require `terraform fmt -check`, `terraform validate`, and the task's
  `terraform plan` before completion.

Do not implement Task 1 or any Azure resource. Do not create or modify files
outside the selected path. After editing, run Terraform formatting and
validation.
