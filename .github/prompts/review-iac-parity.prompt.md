---
description: Review Bicep and Terraform tracks for behavior and safety
---

Compare the active lab's Bicep and Terraform implementations. Do not focus on
line-by-line syntax. Produce a table covering resource responsibilities,
identity and RBAC, API or event contracts, naming, tags, SKU/cost, diagnostics,
retry/failure behavior, outputs, and cleanup.

Identify behavioral drift, secret exposure, over-broad roles, destructive
changes, unpinned provider behavior, and resources that either track would
orphan. Cite exact files and propose only the smallest corrections. Do not apply
changes until the review is complete.
