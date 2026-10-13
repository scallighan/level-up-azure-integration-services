---
title: "Lab 0: Shared Azure foundation"
permalink: /labs/00-foundation/
---

# Lab 0: Shared Azure foundation

Deploy the shared Azure infrastructure once using the provided **Bicep or
Terraform** code. Later labs reuse it to build integrations.

**Time:** 30-45 minutes plus Azure provisioning and RBAC propagation.

Read [implementation requirements](implementation-requirements.md) and the
[Logic App Standard baseline](../../docs/logic-app-standard-baseline.md).

## What you deploy

```text
New or existing resource group
  VNet (four reference subnets)
    Logic App integration -> private host storage (blob/queue/table/file + DNS)
                          -> private Cosmos DB (Sql endpoint + DNS)
                          -> Service Bus Standard public endpoint (Entra ID)
  Windows WS1 plan -> empty Logic App Standard (system + host-storage identities)
  Cosmos DB serverless -> workshop/items (/id)
  Log Analytics <- Application Insights <- Logic App telemetry
```

The user-assigned identity accesses host storage only. The system-assigned
identity receives Cosmos data contributor at the `items` container scope.
Workflows, frontend resources, and messaging entities are added in later labs.

**Cost:** WS1, five private endpoints, storage, Cosmos usage, Service Bus
Standard, and monitoring ingestion/retention are billable. Service Bus Standard
uses its public endpoint with Entra ID, not Private Link; production private
networking calls for Premium. No NAT Gateway is required.

## 1. Configure and check Azure access

Use a non-production Azure subscription. You need permission to deploy these
resources and create role assignments. New-group deployment also needs
permission to create resource groups. Bicep's subscription entry point needs
subscription deployment permission even when reusing a group.

From the repository root, use **Bash**, **Azure CLI**, **jq**, and either
**Bicep** (`az bicep install`) or **Terraform 1.14.4**. No GitHub CLI login,
editor, or Copilot session is needed for this lab.

Run setup for **only your selected track**:

```bash
bash scripts/foundation.sh setup bicep
# Or: bash scripts/foundation.sh setup terraform
```

The helper prompts for four inputs and saves them in ignored root `.env`,
preserving later-lab settings and using existing values as defaults:

| Input | Value |
|---|---|
| `AZURE_SUBSCRIPTION_ID` | Your subscription ID |
| `WORKSHOP_PREFIX` | 3-12 lowercase letters/numbers, starting with a letter |
| `AZURE_LOCATION` | Region identifier, such as `westus` |
| `EXISTING_RESOURCE_GROUP_NAME` | Existing group name, or empty to create one |

Setup signs in to Azure if needed, selects the subscription, validates an
existing group, runs `check-prereqs.sh` for the selected track/region, and
registers the required resource providers. Registration may require subscription
permissions. If WS1 quota is unavailable, choose another region or request
quota and rerun setup. Keep `.env` local and free of credentials.

An existing group must exist in the selected subscription. Its tags, metadata,
and unrelated resources remain untouched. Check for name collisions, including
the fixed private DNS zones; do not share one group across multiple foundations.

## 2. Review and preview your selected track

```bash
bash scripts/foundation.sh preview bicep
# Or: bash scripts/foundation.sh preview terraform
```

The helper loads `.env`, formats/builds Bicep and runs what-if, or initializes
Terraform and runs fmt/validate/plan. Keep Terraform state and plan files
untracked. Do not change tracks after deploying, import resources into another
lab's state, or apply both tracks to the same group.

**Review gate:** the preview creates only the graph above. Existing-group mode
does not create, update, retag, or delete the resource group. No unrelated
resource may be changed. Storage and Cosmos public access are disabled, both
identities are present, and the output contains no secrets.

## 3. Deploy and save the handoff

Only after reviewing the preview, run your selected track:

```bash
bash scripts/foundation.sh deploy bicep
# Or: bash scripts/foundation.sh deploy terraform
```

The helper deploys the selected track and saves `foundation.deployment.json`.
Terraform still asks for apply confirmation. Run **only one** of these paths.
The handoff is ignored and contains only the explicit non-secret references
needed by later labs.
Copy its `resource_group_name` to `FOUNDATION_RESOURCE_GROUP_NAME` in `.env`,
then load `.env` when starting later labs. Keep the group selection and input
values stable; helpers load `.env` themselves.

## 4. Verify readiness

```bash
bash scripts/verify-foundation.sh foundation.deployment.json
```

The check fails explicitly if a hosting, auth, endpoint, DNS, Cosmos RBAC, or
monitoring check fails. If RBAC is still propagating, inspect the exact scope
and principal and retry; never enable keys or public Cosmos access as a fix.
No empty-site provisioning check proves a workflow can access data: Lab 1
tests Cosmos operations; Lab 2 tests Service Bus receive and settlement.

**Done when:** the check passes, the site has no workflows, the handoff is saved,
and resource-group ownership is clear. Continue to [Lab 1](../01-crud-integration/README.md)
or [Lab 2](../02-topic-fanout/README.md); neither requires the other to provision
hosting.

## Cleanup after all labs

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
this deployment. In new-group mode the provider refuses group deletion while
unmanaged resources remain; investigate rather than disabling this safeguard.

For Bicep, there is no Terraform-style destroy state. List and review the
resources in the handoff's group:

```bash
az resource list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$(jq -r .resource_group_name foundation.deployment.json)" \
  --query '[].{id:id,lab:tags.lab,workshop:tags.workshop}' -o table
```

Check `resource_group_created` in the saved handoff. If Lab 0 **created** the
group and all remaining contents belong to the workshop, delete that exact
group with `az group delete --name "<reviewed-group>"`
after confirmation. If the group was **existing**, never delete it. Delete
only individually reviewed Lab 0 resource IDs: site, private endpoints, private
DNS VNet links and zones, VNet, storage/host identity, plan, Cosmos account,
Service Bus namespace, Application Insights, and workspace, in dependency order.
Use `az resource delete --ids "<reviewed-resource-id>"`; remove DNS links before
their VNet/zones. Parent service deletion removes its children and scoped
grants. Leave unrelated resources and group metadata untouched.
