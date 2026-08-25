---
description: Review Bicep and Terraform tracks for behavior and safety
---

Compare the active lab's Bicep and Terraform implementations. Do not focus on
line-by-line syntax. Produce a table covering resource responsibilities,
identity and RBAC, API or event contracts, naming, tags, SKU/cost, diagnostics,
retry/failure behavior, outputs, and cleanup.

Read `docs/logic-app-standard-baseline.md` and compare each track with its
linked reference implementation. Treat drift in the VNet and subnets, host
storage, four storage private endpoints and DNS zones, host-storage RBAC,
Windows WS1 plan, Logic App Standard identities, VNet routing, host settings,
or deployment dependencies as a blocking mismatch. For Lab 1, also treat drift
in the Cosmos `Sql` private endpoint, `privatelink.documents.azure.com` zone,
VNet link, DNS zone group, disabled public access, built-in managed-identity
connection shape, workflow artifact deployment, and contract-safe response
projection as blocking.

Identify behavioral drift, secret exposure, over-broad roles, destructive
changes, unpinned provider behavior, and resources that either track would
orphan. Cite exact files and propose only the smallest corrections. Do not apply
changes until the review is complete.
