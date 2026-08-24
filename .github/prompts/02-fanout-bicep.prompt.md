---
description: Build the topic fan-out lab incrementally with Bicep
---

Read `.github/copilot-instructions.md`,
`docs/logic-app-standard-baseline.md`, the current files under
`https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep`,
`labs/02-topic-fanout/README.md`, and both files in
`labs/02-topic-fanout/contracts/`.

Work only on the next incomplete checkpoint in the Bicep track. First summarize
the topic, subscriptions, filters, workflow identities, RBAC scopes, retry
behavior, and validation command. Create one independently deployable Logic App
per subscription. Receivers must use managed identity and peek-lock semantics;
complete a message only after processing succeeds.

Replicate the Bicep reference with one shared VNet, host storage account, four
storage private endpoints and DNS resources, host-storage user-assigned
identity, and Windows WS1 plan. Create three separate Logic App Standard sites
on that plan. Each site uses the shared host-storage identity and its own
system-assigned identity for its assigned Service Bus subscription. Preserve
the reference VNet routing, host settings, and deployment dependencies. Never
substitute Consumption Logic Apps.

After editing, format and compile the Bicep. Call out assumptions explicitly.
