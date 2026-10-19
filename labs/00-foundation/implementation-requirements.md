# Lab 0 implementation requirements

Lab 0 is mandatory before implementing Labs 1-3. Its committed Bicep and
Terraform deployments create the same shared infrastructure. Learners configure,
review, and deploy this code rather than asking Copilot to regenerate it.

Keep the learner setup Azure-only: Bash, Azure CLI, jq, and the selected IaC
tool. Require only subscription, prefix, region, and optional existing group.
Check WS1 quota in that selected region, not a global region scan. GitHub CLI
authentication, an editor/Copilot session, frontend settings, and APIM inputs
are not prerequisites for this deployment.

Keep setup, preview, and deployment commands in `scripts/foundation.sh`;
the README invokes its actions rather than duplicating shell logic. Setup
prompts for the four inputs, preserves later-lab `.env` settings, checks access
and quota, and registers providers. Preview never deploys. Deployment preserves
Terraform confirmation and saves the non-secret handoff only after success.

Read this file with the [README](README.md), [implementation standards](../../docs/implementation-standards.md),
and [Logic App Standard baseline](../../docs/logic-app-standard-baseline.md).
Lab 1 uses `workshop/items` with partition key `/id` for region and support-tier lookups;
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

Lab 0 owns the foundation and container-scoped Cosmos grant. Lab 1 adds
lookup data and workflow artifacts. Lab 2 adds topics/subscriptions/rules,
subscription-scoped receiver roles, and workflow artifacts to the existing
namespace/site. Lab 3 references the same foundation and adds only approved
flow-specific entities, grants, artifacts, and dependencies. No later lab
imports, retags, replaces, or deletes the shared parent site or foundation.

The single system identity intentionally accumulates workload grants across
labs. This is a workshop cost tradeoff, not per-workflow identity isolation.
The host-storage identity must never receive Cosmos or Service Bus roles.

## Validation

Format/build/what-if Bicep; fmt/validate/plan Terraform. Preview both new-group
and existing-group paths. Existing mode must contain no resource-group writes.
Provisioning checks must confirm identities, WS1, private endpoint approvals,
DNS records/links, disabled storage/Cosmos public access and local auth,
Cosmos role scope, Service Bus SKU/auth, and monitoring wiring.
Later labs prove actual data access and telemetry with workflow tests.

## Cleanup

Keep this foundation for the whole workshop. First remove Lab 3, Lab 2, and
Lab 1 artifacts and their owned resources/roles. Shared resources remain tagged
`lab=00` throughout; do not change their ownership.

For manual cleanup, first load `.env` with exported variables:

```bash
set -a; source .env; set +a
```

For Terraform, review `terraform -chdir=labs/00-foundation/iac/terraform plan -destroy`,
then run `terraform -chdir=labs/00-foundation/iac/terraform destroy`.
In existing-group mode the group is a data source and cannot be deleted by
this deployment. In new-group mode,
`prevent_deletion_if_contains_resources = false` allows Azure to delete the
workshop group and **all remaining contents**, including resources Terraform
does not manage. Before destroying, review the group's resources with the
`az resource list` command below. Terraform's plan does not enumerate unmanaged
resources that will be deleted with the group. Move or preserve anything that
must survive before continuing.

For either track, list and review the resources in the handoff's group:

```bash
az resource list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$(jq -r .resource_group_name foundation.deployment.json)" \
  --query '[].{id:id,lab:tags.lab,workshop:tags.workshop}' -o table
```

For Bicep, there is no Terraform-style destroy state.
Check `resource_group_created` in the saved handoff. If Lab 0 **created** the
group and all remaining contents belong to the workshop, delete that exact
group with `az group delete --name "<reviewed-group>"` after confirmation.
If the group was **existing**, never delete it. Delete only individually
reviewed Lab 0 resource IDs: site, private endpoints, private DNS VNet links
and zones, VNet, storage/host identity, plan, Cosmos account, Service Bus
namespace, Application Insights, and workspace, in dependency order.
Use `az resource delete --ids "<reviewed-resource-id>"`; remove DNS links
before their VNet/zones. Parent service deletion removes its children and
scoped grants. Leave unrelated resources and group metadata untouched.
