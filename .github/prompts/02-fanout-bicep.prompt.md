---
description: Create the Lab 2 Bicep starter structure and local instructions
---

Read `AGENTS.md`, `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep`,
`labs/02-topic-fanout/README.md`,
`labs/02-topic-fanout/implementation-requirements.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Initialize only `labs/02-topic-fanout/iac/bicep/` for the Bicep learner path.
Before editing, show this starter structure and briefly explain each entry:

```text
labs/02-topic-fanout/iac/bicep/
├── AGENTS.md
├── main.bicep
└── modules/
```

Create `main.bicep` as a minimal subscription-scoped entry point with only the
target scope and file-level teaching comments. Do not add parameters, resource
declarations, modules, outputs, workflow definitions, or placeholder resources.
Create `modules/` only when adding the first real module in a later lab task;
do not add a keep file.

Create the path-local `AGENTS.md` with concise instructions that:

- identify this directory as the Lab 2 Bicep track;
- require the repository instructions, implementation standards, Lab 2 README,
  implementation requirements, both event contracts, Logic App Standard
  baseline, and matching Bicep reference before changes;
- keep each learner request bounded to the named lab step or task;
- require an explicit `new` or `existing` hosting-foundation mode and preserve
  its ownership and cleanup boundary;
- preserve the host-storage user-assigned identity and subscription-scoped
  Service Bus receiver system-assigned identity boundary;
- prohibit secrets, connection strings, full event payloads, and changes to any
  `iac/.gitignore`;
- require a subscription-scoped entry point only because the deployment creates
  the Lab 2 resource group, with resource-group-scoped resources placed in
  clear modules; and
- require `az bicep format`, `az bicep build`, and the task's deployment
  `what-if` before completion.

Do not implement Step 0, Task 1, or any Azure resource. Do not create or modify
files outside the selected path. After editing, format and compile `main.bicep`.
