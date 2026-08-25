# Logic App Standard infrastructure baseline

Every Logic App in this workshop must use the private-networked Logic App
Standard pattern from the following source implementations:

- [Bicep reference](https://github.com/scallighan/logic-app-doc-processing/tree/main/bicep)
- [Terraform reference](https://github.com/scallighan/logic-app-doc-processing/tree/main/terraform)

Read the matching reference implementation before generating or changing a lab
deployment. The reference repository is the source of truth for the resources,
settings, dependencies, and managed-identity wiring in the scope below. Do not
replace this pattern with a Consumption Logic App, a public host-storage
connection string, or a simplified Standard deployment.

## Required resource graph

Each lab has one shared Logic App hosting foundation:

```mermaid
flowchart LR
    PLAN[Windows WS1 Workflow Standard plan] --> LA[Logic App Standard site]
    LA -->|VNet integration and route all| LASUB[Delegated Logic App subnet]
    LA -->|user-assigned identity| SA[Host storage account]
    SA --> PEB[Blob private endpoint]
    SA --> PEQ[Queue private endpoint]
    SA --> PET[Table private endpoint]
    SA --> PEF[File private endpoint]
    PEB --> DNS[Private DNS zones linked to VNet]
    PEQ --> DNS
    PET --> DNS
    PEF --> DNS
```

The lab-specific Cosmos DB, Service Bus, APIM, Static Web App, and observability
resources extend this graph; they do not replace or weaken it.

## Reference-matched requirements

| Area | Required implementation |
|---|---|
| Virtual network | Use the reference `172.22.0.0/16` address space and its four `/24` subnets: default, Container Apps environment, private endpoints, and Logic App integration. Disable default outbound access on each subnet. Preserve the `Microsoft.App/environments` and `Microsoft.Web/serverFarms` delegations from the reference. Parameterize the address prefixes only if a lab must fit an existing network. |
| Host storage | Use a `StorageV2`, `Standard_LRS`, Hot account with HTTPS-only traffic, TLS 1.2 minimum, and blob public access disabled. Never use an account key or connection string. |
| Storage private connectivity | Create separate blob, queue, table, and file private endpoints in the private-endpoint subnet. Create the corresponding `privatelink` private DNS zones, link them to the VNet, and attach each endpoint to its zone with a private DNS zone group. |
| Host-storage identity | Create a user-assigned managed identity and grant it Storage Blob Data Contributor, Storage Queue Data Contributor, and Storage Table Data Contributor on the host storage account. |
| App Service plan | Use a Windows `WS1` Workflow Standard plan. This and the private endpoints are cost-bearing resources and must be identified before deployment. |
| Logic App | Deploy `Microsoft.Web/sites` as `functionapp,workflowapp` with both system-assigned and host-storage user-assigned identities. Attach it to the delegated Logic App subnet and route all outbound traffic through the VNet. |
| Host settings | Preserve the reference Functions v4, .NET worker, Workflows extension bundle, `APP_KIND=workflowApp`, in-process .NET 8, and PowerShell settings. Configure `AzureWebJobsStorage` with the user-assigned identity resource ID and blob, queue, and table service URIs. Lab-specific settings may be added but must not replace these host settings. |
| Dependencies | Do not create the Logic App site until the plan, host-storage RBAC assignments, and all four storage private endpoints are ready. |

Use the current stable Azure API versions and the repository's pinned Terraform
provider constraints while preserving the reference behavior. If the Bicep and
Terraform reference files differ, report the difference and keep the lab tracks
behaviorally equivalent rather than silently choosing a third design.

Private endpoints do not by themselves prove that public access is disabled.
Review the reference account properties and deployment preview explicitly; do
not invent or weaken a network-access setting.

## Lab workload private connectivity

The shared hosting baseline covers host storage. A lab-specific data service
with public network access disabled also needs a complete private data-plane
path from the Logic App integration subnet.

Lab 1 must create a Cosmos DB `Sql` private endpoint in the private-endpoint
subnet, the `privatelink.documents.azure.com` private DNS zone, a VNet link, and
a private DNS zone group. Keep Cosmos public network access and local
authentication disabled. Create this path in the backend foundation before
deploying the CRUD workflow, and verify the endpoint connection, private A
record, and VNet link after deployment. VNet integration and managed identity
alone do not make a private Cosmos account reachable.

## Identity boundaries

The user-assigned identity exists for Logic App host-storage access. Keep each
Logic App's system-assigned identity for lab workload access:

- Lab 1 grants its Logic App system identity only the required Cosmos DB
  data-plane access.
- Lab 2 grants the selected Logic App system identity receiver access
  separately at each required Service Bus subscription scope, never at
  namespace or topic scope.

Do not replace either identity boundary with shared keys or broaden the
user-assigned identity to all lab data-plane resources.

## Lab 2 shared foundation

Lab 2 must explicitly select a `new` or `existing` shared hosting foundation.
`new` creates one Lab 2-owned VNet, host storage account, four storage private
endpoints, host-storage user-assigned identity, WS1 plan, observability
foundation, and empty Logic App Standard site. `existing` references a
compatible deployed foundation and site, such as Lab 1's, without importing,
modifying, retagging, or deleting the foundation or taking ownership of the
parent site.

Audit, fulfillment, and notification remain three independently deployable
workflows in that one site. The site's system identity receives three separate
Service Bus role assignments, each scoped to one subscription. Never broaden
those assignments to the topic or namespace. The host-storage user-assigned
identity remains limited to host storage.

When Lab 1's site is reused, its system identity retains the Lab 1 Cosmos role
and gains the three Lab 2 subscription-scoped Service Bus roles. This is an
intentional workshop cost tradeoff and must be explained before deployment.
Lab 2 may manage its child workflows and role assignments, but not the existing
parent site.

Existing mode requires explicit references to the integration subnet, host
storage, host-storage identity, WS1 plan, observability resources, and Standard
site. Validate that they remain compatible with this baseline and in the
current subscription and region. Lab 2 cleanup must never remove an existing
foundation or parent site.

The shared hosting foundation does not change peek-lock, completion, retry, or
dead-letter requirements.
