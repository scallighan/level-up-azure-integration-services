# Lab 0 implementation requirements

Lab 0 is mandatory before implementing Labs 1-3. Its committed Bicep and
Terraform deployments create the same shared infrastructure. Learners configure,
review, and deploy this code rather than asking Copilot to regenerate it.

Keep the learner setup Azure-only: Bash, Azure CLI, jq, and the selected IaC
tool. Require only subscription, prefix, region, and optional existing group.
Check WS1 quota in that selected region, not a global region scan. GitHub CLI
authentication, an editor/Copilot session, frontend settings, and APIM inputs
are not prerequisites for this deployment.

Read this file with the [README](README.md), [implementation standards](../../docs/implementation-standards.md),
and [Logic App Standard baseline](../../docs/logic-app-standard-baseline.md).
The Lab 1 OpenAPI contract defines `workshop/items` with partition key `/id`;
Lab 2's event contract is implemented later, not in this foundation.

## Resource graph and ownership

| Resource | Lab 0 responsibility |
|---|---|
| Resource group | Ask whether the learner has an existing group. An empty input creates a workshop group; a supplied name references a group in the selected subscription without changing or owning it. |
| VNet | `172.22.0.0/16`, four reference `/24` subnets and delegations, default outbound access disabled |
| Host storage | StorageV2, Standard LRS, Hot, HTTPS/TLS 1.2, public network and shared-key access disabled |
| Host storage connectivity | Four private endpoints (blob, queue, table, file), DNS zones, links, and zone groups |
| Host identity | User-assigned identity with Blob, Queue, and Table Data Contributor on host storage only |
| Hosting plan | Windows WS1 Workflow Standard |
| Logic App | One empty `functionapp,workflowapp` Standard site, both identities, delegated-subnet integration, all outbound traffic routed through VNet |
| Cosmos DB | Single-region serverless NoSQL account, Session consistency, local authentication and public access disabled |
| Cosmos data | Database `workshop`, container `items`, partition key `/id`, consistent indexing |
| Cosmos connectivity | `Sql` private endpoint, `privatelink.documents.azure.com`, VNet link, zone group |
| Cosmos RBAC | Site system identity: built-in data contributor scoped to `workshop/items` |
| Service Bus | Standard namespace, TLS 1.2, local/SAS authentication disabled, public endpoint |
| Monitoring | Dedicated 30-day Log Analytics workspace, workspace-based Application Insights, site telemetry setting |

All taggable new resources use `workshop=agentic-ais`, `lab=00`. Do not retag
an existing parent resource group. A resource group's metadata location does not
have to match the selected deployment region. Reject a missing existing group;
never silently fall back to creating one.

There is only one foundation per parent group because private DNS zone names
are fixed. Review collisions before deployment; never adopt unrelated existing
resources. An existing group is not permission to modify everything inside it.

## Reference boundary

The hosting graph and settings follow both reference tracks at
`scallighan/logic-app-doc-processing`, revision
`6bfb4281008bf56b21584e29ef04566ceabf0f14`.
Preserve the Functions v4/.NET worker, Workflows bundle, in-process .NET 8,
PowerShell 7.4, identity-based storage URIs, and identity resource ID.
The site waits for host RBAC, all storage endpoints/DNS, and Cosmos private DNS.

Deliberate workshop adaptations:

- Create a dedicated workspace instead of assuming the reference's hardcoded
  default workspace exists.
- Make both tracks disable host-storage public and shared-key access. The
  reference storage account does not explicitly disable these.
- Use `outboundVnetRouting.allTraffic` with the stable Web `2025-03-01` API in
  both tracks. The reference Bicep uses the older `vnetRouteAllEnabled` shape;
  its Terraform uses `outboundVnetRouting`.
- Add Cosmos, Service Bus, and wired Application Insights. Do not copy the
  reference SQL, Key Vault, Document Intelligence, or Office 365 resources.
- Use pinned Terraform/AzureRM/AzAPI versions matching the workshop's tested
  toolchain. AzAPI avoids fetching storage keys and represents a keyless
  dual-identity Standard site that AzureRM's Logic App resource cannot.

Keep direct VNet-to-internet routing; do not require a NAT Gateway. VNet
integration is outbound connectivity, not private inbound access: the Standard
site remains reachable for the later HTTP workshop. Storage and Cosmos use
private endpoints. Service Bus Standard cannot use Private Link; retain its
public endpoint with Entra ID authorization. Premium is recommended for
production private networking, not substituted into this cost-sensitive lab.

## Inputs and handoff

Both tracks accept subscription, prefix, location, and optional existing parent
group. Use a 3-12 character lowercase alphanumeric prefix starting with a letter
and a region identifier such as `westus`. Keep inputs in ignored root `.env`.
Global names have deterministic, track-specific safe suffixes; switching tracks
does not adopt or import an existing deployment.

Both tracks output one `foundation` object with identical snake_case field
names. It records `resource_group_created` for cleanup ownership and contains
resource names/IDs, region, site principal ID, and non-secret
service endpoints. No keys, callback URLs, observability connection strings,
or credentials may be outputs. Save it locally as `foundation.deployment.json`
for explicit later-lab references; never depend on Terraform remote state from
another lab.

Lab 0 owns the foundation and container-scoped Cosmos grant. Lab 1 adds its
frontend and workflow artifacts. Lab 2 adds topics/subscriptions/rules,
subscription-scoped receiver roles, and workflow artifacts to the existing
namespace/site. Lab 3 references the same foundation and adds only approved
flow-specific entities, grants, artifacts, and dependencies. No later lab
imports, retags, replaces, or deletes the shared parent site or foundation.

The single system identity intentionally accumulates workload grants across
labs. This is a workshop cost tradeoff, not per-workflow identity isolation.
The host-storage identity must never receive Cosmos or Service Bus roles.

## Validation and cleanup

Format/build/what-if Bicep; fmt/validate/plan Terraform. Preview both new-group
and existing-group paths. Existing mode must contain no resource-group writes.
Provisioning checks must confirm identities, WS1, private endpoint approvals,
DNS records/links, disabled storage/Cosmos public access and local auth,
Cosmos role scope, Service Bus SKU/auth, and monitoring wiring.
Later labs prove actual data access and telemetry with workflow tests.

Remove later-lab artifacts and roles before destroying Lab 0. In an existing
group, remove only Lab 0-owned resources, never the group or unrelated contents.
In a newly created group, delete the group only after reviewing its contents
and confirming that all remaining resources belong to the workshop.
