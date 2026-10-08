---
description: Create the Lab 3 Terraform starter structure from an approved design
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`, `docs/logic-app-standard-baseline.md`, the
current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/03-workbook-to-solution/README.md`,
`labs/03-workbook-to-solution/implementation-requirements.md`, and the learner's
`labs/03-workbook-to-solution/plans/integration-design.md`.

Stop if the plan is missing, incomplete, has unresolved blocking questions,
or does not begin with `Status: approved`.

Initialize only `labs/03-workbook-to-solution/iac/terraform/`. Before editing,
show this starter structure and briefly explain each file:

```text
labs/03-workbook-to-solution/iac/terraform/
├── AGENTS.md
├── main.tf
├── outputs.tf
├── providers.tf
├── variables.tf
└── versions.tf
```

Create minimal base files only. Pin Terraform and AzureRM provider constraints
in `versions.tf`; configure AzureRM with its required features block in
`providers.tf`; and add short file-level teaching comments to `main.tf`,
`variables.tf`, and `outputs.tf`. Do not add variables, resources, data sources,
locals, outputs, backend configuration, or placeholders.

Create `AGENTS.md` with concise instructions that require all context above;
keep work bounded to the named Lab 3 task; treat the approved design as the
implementation boundary; cite workbook evidence for design changes; keep every
intermediate artifact in the Git-ignored Lab 3 `plans/` folder and do not
recreate a `contracts/` folder; preserve
the host-storage user-assigned and workload system-assigned identity boundary;
prohibit workbook payloads, secrets, callback URLs, external credentials,
Terraform state, plans, and populated variable files in source control;
prohibit changes to any `iac/.gitignore`; prefer AzureRM and document necessary
AzAPI use; and require `terraform fmt -check`, `terraform validate`, and
`terraform plan`.

Do not implement any proposal stage or modify files outside the selected path.
After editing, run Terraform formatting and validation.
