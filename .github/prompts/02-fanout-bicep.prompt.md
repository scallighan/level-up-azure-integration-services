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

Also read `labs/00-foundation/implementation-requirements.md` and the local
`foundation.deployment.json`. Require completed Lab 0; Lab 1 is not required.
There is no standalone new-foundation mode.

Initialize only `labs/02-topic-fanout/iac/bicep/` for the Bicep learner path.
Before editing, show this starter structure and briefly explain each entry:

```text
labs/02-topic-fanout/iac/bicep/
├── AGENTS.md
├── main.bicep
└── modules/
```

Create `main.bicep` as a minimal resource-group-scoped entry point with only the
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
- require explicit Lab 0 existing-resource references for hosting, monitoring,
  namespace, and site; never import, retag, manage, or delete shared parents;
- preserve other labs' workflow artifacts and app-level connection entries;
- preserve the host-storage user-assigned identity and subscription-scoped
  Service Bus receiver system-assigned identity boundary;
- use the ignored root `.env` for stable, non-secret learner inputs, require it
  to be sourced before Azure CLI commands, and keep `.env.example` as the
  variable-name template so values are not repeatedly re-entered;
- prohibit secrets, connection strings, or full event payloads in `.env`,
  prohibit committing `.env`, and prohibit changes to any `iac/.gitignore`;
- deploy into the existing Lab 0 resource group without creating or managing
  it; own only messaging children, scoped roles, and workflow artifacts; and
- require `az bicep format`, `az bicep build`, and the task's deployment
  `what-if` before completion.

Do not implement Step 0, Task 1, or any Azure resource. Do not create or modify
files outside the selected path. After editing, format and compile `main.bicep`.
