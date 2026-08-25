---
description: Create the Lab 2 Terraform starter structure and local instructions
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/02-topic-fanout/README.md`,
`labs/02-topic-fanout/implementation-requirements.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Initialize only `labs/02-topic-fanout/iac/terraform/` for the Terraform learner
path. Before editing, show this starter structure and briefly explain each file:

```text
labs/02-topic-fanout/iac/terraform/
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

- identify this directory as the Lab 2 Terraform track;
- require the repository instructions, implementation standards, Lab 2 README,
  implementation requirements, both event contracts, Logic App Standard
  baseline, and matching Terraform reference before changes;
- keep each learner request bounded to the named lab step or task;
- require an explicit `new` or `existing` hosting-foundation mode and preserve
  its ownership and cleanup boundary;
- preserve the host-storage user-assigned identity and subscription-scoped
  Service Bus receiver system-assigned identity boundary;
- prohibit secrets, connection strings, full event payloads, Terraform state or
  plan files, populated variable files, and changes to any `iac/.gitignore`;
- prefer AzureRM and allow AzAPI only when AzureRM cannot represent required
  behavior, with the reason documented; and
- require `terraform fmt -check`, `terraform validate`, and the task's
  `terraform plan` before completion.

Do not implement Step 0, Task 1, or any Azure resource. Do not create or modify
files outside the selected path. After editing, run Terraform formatting and
validation.
