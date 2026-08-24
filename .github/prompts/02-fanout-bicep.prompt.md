---
description: Build the topic fan-out lab incrementally with Bicep
---

Read `.github/copilot-instructions.md`,
`labs/02-topic-fanout/README.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Work only on the next incomplete checkpoint in the Bicep track. First summarize
the topic, subscriptions, filters, workflow identities, RBAC scopes, retry
behavior, and validation command. Create one independently deployable Logic App
per subscription. Receivers must use managed identity and peek-lock semantics;
complete a message only after processing succeeds.

After editing, format and compile the Bicep. Call out assumptions explicitly.
