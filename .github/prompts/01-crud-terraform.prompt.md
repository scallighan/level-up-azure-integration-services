---
description: Load Terraform context for bounded CRUD lab tasks
---

Read `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/01-crud-integration/README.md`, and
`labs/01-crud-integration/implementation-requirements.md`, and
`labs/01-crud-integration/contracts/openapi.yaml`.

Use the Terraform track for the bounded outcome in the learner's current
request. Do not infer the next task from repository state or implement later
tasks. Before editing, summarize the resource graph, identity flow, variables,
non-secret outputs, expected files, and validation commands for the requested
outcome. Stop for approval when the learner asks for an approval boundary.

Pin provider constraints and prefer AzureRM resources. Use AzAPI only when
AzureRM cannot represent required behavior, and document that decision. Follow
the shared standards and lab requirements rather than repeating or weakening
them.

After editing, run formatting and validation. Report remaining uncertainty
rather than guessing.
