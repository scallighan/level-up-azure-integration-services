---
description: Load Terraform context for bounded fan-out lab tasks
---

Read `.github/copilot-instructions.md`,
`docs/implementation-standards.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform`,
`labs/02-topic-fanout/README.md`,
`labs/02-topic-fanout/implementation-requirements.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Use the Terraform track for the bounded outcome in the learner's current
request. Do not infer the next task from repository state or implement later
tasks. Before editing, summarize the requested resource graph, message routing,
hosting-foundation mode and ownership boundary, identity and RBAC boundaries,
retry and failure behavior, expected files, and validation commands. Stop for
approval when the learner asks for an approval boundary.

Pin provider constraints and use AzAPI only where AzureRM lacks the required
workflow representation. Follow the shared standards and lab requirements
rather than repeating or weakening them.

After editing, format and validate the Terraform. Call out assumptions
explicitly.
