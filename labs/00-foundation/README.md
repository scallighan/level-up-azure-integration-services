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

```bash
[[ -f .env ]] || cp .env.example .env
read -r -p "Existing Azure resource group (press Enter to create a workshop group): " EXISTING_RESOURCE_GROUP_NAME
```

Edit only these four inputs in `.env`, using the resource-group answer above:

| Input | Value |
|---|---|
| `AZURE_SUBSCRIPTION_ID` | Your subscription ID |
| `WORKSHOP_PREFIX` | 3-12 lowercase letters/numbers, starting with a letter |
| `AZURE_LOCATION` | Region identifier, such as `westus` |
| `EXISTING_RESOURCE_GROUP_NAME` | Existing group name, or empty to create one |

Leave the Terraform mappings unchanged. Ignore the later-lab settings for now.
Keep `.env` local and free of credentials. Load it and select your subscription:

```bash
set -a
source .env
set +a
az login
az account set --subscription "$AZURE_SUBSCRIPTION_ID"

[[ "$WORKSHOP_PREFIX" =~ ^[a-z][a-z0-9]{2,11}$ ]] || {
  echo "Use a 3-12 character lowercase alphanumeric prefix starting with a letter." >&2
  exit 1
}

if [[ -n "$EXISTING_RESOURCE_GROUP_NAME" ]]; then
  az group show --subscription "$AZURE_SUBSCRIPTION_ID" \
    --name "$EXISTING_RESOURCE_GROUP_NAME" --query '{name:name,id:id}' -o table || exit 1
fi
```

Check **only your selected track** and region:

```bash
./scripts/check-prereqs.sh bicep "$AZURE_LOCATION"
# Or, for Terraform:
./scripts/check-prereqs.sh terraform "$AZURE_LOCATION"
```

The check verifies the deployment tools, Azure sign-in, and available WS1
quota in that region. If quota is unavailable, choose another region or request
quota, update `.env`, and repeat the check.

An existing group must exist in the selected subscription. Its tags, metadata,
and unrelated resources remain untouched. Check for name collisions, including
the fixed private DNS zones; do not share one group across multiple foundations.

Register required providers (registration may require subscription permissions):

```bash
for provider in Microsoft.Network Microsoft.Storage Microsoft.ManagedIdentity \
  Microsoft.Web Microsoft.DocumentDB Microsoft.ServiceBus Microsoft.Insights \
  Microsoft.OperationalInsights; do
  az provider register --subscription "$AZURE_SUBSCRIPTION_ID" \
    --namespace "$provider" --wait
done
```

## 2. Review and preview your selected track

**Bicep**

```bash
az bicep format --file labs/00-foundation/iac/bicep/main.bicep
az bicep format --file labs/00-foundation/iac/bicep/resources.bicep
az bicep build --file labs/00-foundation/iac/bicep/main.bicep --stdout >/dev/null
az deployment sub what-if \
  --subscription "$AZURE_SUBSCRIPTION_ID" --location "$AZURE_LOCATION" \
  --template-file labs/00-foundation/iac/bicep/main.bicep \
  --parameters prefix="$WORKSHOP_PREFIX" location="$AZURE_LOCATION" \
    existingResourceGroupName="$EXISTING_RESOURCE_GROUP_NAME"
```

**Terraform**

```bash
terraform -chdir=labs/00-foundation/iac/terraform init
terraform -chdir=labs/00-foundation/iac/terraform fmt -check
terraform -chdir=labs/00-foundation/iac/terraform validate
terraform -chdir=labs/00-foundation/iac/terraform plan
```

Terraform reads the exported `TF_VAR_*` values in `.env`. Keep its local state
and plan files untracked. Do not change tracks after deploying, import resources
into another lab's state, or apply both tracks to the same group.

**Review gate:** the preview creates only the graph above. Existing-group mode
does not create, update, retag, or delete the resource group. No unrelated
resource may be changed. Storage and Cosmos public access are disabled, both
identities are present, and the output contains no secrets.

## 3. Deploy and save the handoff

Only after reviewing the preview, run your selected track:

**Bicep**

```bash
az deployment sub create \
  --subscription "$AZURE_SUBSCRIPTION_ID" --name "foundation-$WORKSHOP_PREFIX" \
  --location "$AZURE_LOCATION" \
  --template-file labs/00-foundation/iac/bicep/main.bicep \
  --parameters prefix="$WORKSHOP_PREFIX" location="$AZURE_LOCATION" \
    existingResourceGroupName="$EXISTING_RESOURCE_GROUP_NAME" \
  --output none
az deployment sub show \
  --subscription "$AZURE_SUBSCRIPTION_ID" --name "foundation-$WORKSHOP_PREFIX" \
  --query properties.outputs.foundation.value -o json > foundation.deployment.json
```

**Terraform**

```bash
terraform -chdir=labs/00-foundation/iac/terraform apply
terraform -chdir=labs/00-foundation/iac/terraform output -json foundation \
  > foundation.deployment.json
```

Run **only one** of these paths. `foundation.deployment.json` is ignored and
contains only the explicit non-secret references needed by later labs.
Copy its `resource_group_name` to `FOUNDATION_RESOURCE_GROUP_NAME` in `.env`,
then source `.env` again. Keep the group selection and input values stable.

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

For Terraform, review `terraform -chdir=labs/00-foundation/iac/terraform plan -destroy`,
then run `terraform -chdir=labs/00-foundation/iac/terraform destroy`.
In existing-group mode the group is a data source and cannot be deleted by
this deployment. In new-group mode the provider refuses group deletion while
unmanaged resources remain; investigate rather than disabling this safeguard.

For Bicep, there is no Terraform-style destroy state. List and review the
resources in the handoff's group:

```bash
az resource list --subscription "$AZURE_SUBSCRIPTION_ID" \
  --resource-group "$FOUNDATION_RESOURCE_GROUP_NAME" \
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
