---
description: Create the Lab 3 Bicep starter structure from an approved design
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`, `docs/logic-app-standard-baseline.md`, the
current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep`,
`labs/03-workbook-to-solution/README.md`,
`labs/03-workbook-to-solution/implementation-requirements.md`, and the learner's
`labs/03-workbook-to-solution/plans/integration-design.md` and its
`integration-design.svg` visual.

Stop if the plan is missing, lacks the concise Task 1 summary, has unresolved
workbook/flow conflicts, or does not begin with `Status: approved`.
Task 1 approves the message flow, not a complete deployment specification.
Missing hosting, network, RBAC, or operational details are resolved in Task 2
before resource implementation, not by expanding the Task 1 report.

Initialize only `labs/03-workbook-to-solution/iac/bicep/`. Before editing, show
this starter structure and briefly explain each entry:

```text
labs/03-workbook-to-solution/iac/bicep/
├── AGENTS.md
├── main.bicep
└── modules/
```

Create `main.bicep` as a minimal subscription-scoped entry point with only the
target scope and file-level teaching comments. Do not add parameters, resource
declarations, modules, outputs, workflow definitions, or placeholder resources.
Create `modules/` only when adding the first real module later.

Create `AGENTS.md` with concise instructions that require all context above;
keep work bounded to the named Lab 3 task; treat the approved design as the
implementation boundary; cite workbook evidence for design changes; keep every
intermediate artifact in the Git-ignored Lab 3 `plans/` folder and do not
recreate a `contracts/` folder; allow original workbook names and values in
local plans but scrub artifacts intended for Git; preserve
the host-storage user-assigned and workload system-assigned identity boundary;
prohibit workbook payloads, secrets, callback URLs, and external credentials in
source, outputs, or telemetry; prohibit changes to any `iac/.gitignore`; place
resource-group resources in clear modules; and require `az bicep format`,
`az bicep build`, and deployment `what-if`.

Do not implement any proposal stage or modify files outside the selected path.
After editing, format and compile `main.bicep`.
