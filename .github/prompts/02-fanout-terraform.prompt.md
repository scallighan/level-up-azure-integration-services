---
description: Build the topic fan-out lab incrementally with Terraform
---

Read `.github/copilot-instructions.md`,
`labs/02-topic-fanout/README.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Work only on the next incomplete checkpoint in the Terraform track. First
summarize the topic, subscriptions, filters, workflow identities, RBAC scopes,
retry behavior, and validation command. Pin provider constraints and use AzAPI
only where AzureRM lacks the required workflow representation. Create one
independently deployable Logic App per subscription. Receivers must use managed
identity and peek-lock semantics; complete a message only after processing
succeeds.

After editing, format and validate the Terraform. Call out assumptions
explicitly.
