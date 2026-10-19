---
description: Create the Lab 1 region lookup Terraform starter structure
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/01-crud-integration/README.md`, and
`labs/01-crud-integration/implementation-requirements.md`, and
`labs/01-crud-integration/contracts/openapi.yaml`.
Use `contracts/regions.json` and its request/response fixtures as the lookup
exercise. Do not add a CRUD workflow, website, or API Management.

Also read `labs/00-foundation/implementation-requirements.md` and the local
`foundation.deployment.json`. Require completed Lab 0. Do not infer a fallback
hosting deployment or overwrite an older learner implementation/state; resolve
any migration separately before changing existing files.

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
- reference Lab 0 using data sources or explicit IDs from its non-secret
  handoff, never imports, remote state, or managed foundation resource blocks;
- preserve shared-resource tags, parent site/group ownership, other labs'
  workflow artifacts, and app-level connection entries;
- preserve the host-storage user-assigned identity and Cosmos workload
  system-assigned identity boundary;
- use the ignored root `.env` for stable, non-secret learner inputs, map them to
  exported `TF_VAR_*` values, and keep `.env.example` as the variable-name
  template so commands do not repeat `-var` arguments;
- reuse the seed script's `lab01Cosmos` connection and existing container grant;
  add no website, API Management, or extra backend resources;
- prohibit secrets or callback URLs in `.env`, prohibit committing `.env`,
  Terraform state or plan files, populated variable files, and changes to any
  `iac/.gitignore`;
- prefer AzureRM and allow AzAPI only when AzureRM cannot represent required
  behavior, with the reason documented; and
- require `terraform fmt -check`, `terraform validate`, and the task's
  `terraform plan` before completion.

Do not implement Task 1 or any Azure resource. Do not create or modify files
outside the selected path. After editing, run Terraform formatting and
validation.
