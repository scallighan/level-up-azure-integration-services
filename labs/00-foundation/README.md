---
title: "Lab 0: Shared Azure foundation"
permalink: /labs/00-foundation/
---

# Lab 0: Shared Azure foundation

Deploy the shared Azure infrastructure once, then use Copilot to implement the
integrations in Labs 1-3. Choose **Bicep or Terraform**; both deployments are
provided and behaviorally equivalent. Do not generate a second foundation in
later labs.

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
Service Bus entities and receiver roles come in Lab 2. Static Web Apps comes
in Lab 1. No workflows, APIM, SQL, Key Vault, or Document Intelligence are
created here.

**Cost:** WS1, five private endpoints, storage, Cosmos usage, Service Bus
Standard, and monitoring ingestion/retention are billable. Service Bus Standard
uses its public endpoint with Entra ID, not Private Link; production private
networking calls for Premium. No NAT Gateway is required.

## 1. Prepare the workstation and inputs

Use a non-production Azure subscription. You need permission to deploy these
resources and create role assignments. New-group deployment also needs
permission to create resource groups. Bicep's subscription entry point needs
subscription deployment permission even when reusing a group.

Install Git, GitHub CLI, Azure CLI, jq, VS Code with Copilot, and Bicep
(`az bicep install`) or Terraform **1.14.4**. Sign in:

```bash
gh auth login
az login
az account set --subscription "<subscription-id-or-name>"
az account show --query '{name:name,id:id,tenantId:tenantId}' --output table
./scripts/check-prereqs.sh bicep
# or: ./scripts/check-prereqs.sh terraform
```

The check suggests a WS1 region with available quota. Set that region rather
than assuming every subscription can deploy WS1 in the sample region.

```bash
cp .env.example .env
```

Edit `.env`: set `AZURE_SUBSCRIPTION_ID`, a distinctive `WORKSHOP_PREFIX`
(3-12 lowercase letters/numbers, starting with a letter), and `AZURE_LOCATION`.
Leave `API_MANAGEMENT_MODE=none`. Keep this file local and free of credentials.

**Ask the student about the parent group before deploying:**

```bash
read -r -p "Existing Azure resource group (press Enter to create a workshop group): " EXISTING_RESOURCE_GROUP_NAME
export EXISTING_RESOURCE_GROUP_NAME
```

Copy that answer into the matching `.env` entry, leaving it empty for a new
group. Then load settings once per terminal:

```bash
set -a
source .env
set +a

[[ "$WORKSHOP_PREFIX" =~ ^[a-z][a-z0-9]{2,11}$ ]] || {
  echo "Use a 3-12 character lowercase alphanumeric prefix starting with a letter." >&2
  exit 1
}

if [[ -n "$EXISTING_RESOURCE_GROUP_NAME" ]]; then
  az group show --subscription "$AZURE_SUBSCRIPTION_ID" \
    --name "$EXISTING_RESOURCE_GROUP_NAME" --query '{name:name,id:id}' -o table || exit 1
fi
```

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

Ask Copilot to explain the committed graph, not to regenerate it:

```text
Read Lab 0's README, implementation requirements, selected IaC track, and
the Logic App Standard baseline. Ask whether I have an existing resource group;
if yes, require its name, otherwise use the new-group path. Explain ownership,
identity scopes, costs, and non-secret outputs. Help me review the deployment
preview. Do not deploy, recreate the foundation, or weaken networking or auth.
```

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
terraform -chdir=labs/00-foundation/iac/terraform test
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

```bash
# Bicep
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

# Terraform
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

Check `resource_group_created` in the saved handoff. If Lab 0 **created** the group and all remaining contents belong to the
workshop, delete that exact group with `az group delete --name "<reviewed-group>"`
after confirmation. If the group was **existing**, never delete it. Delete
only individually reviewed Lab 0 resource IDs: site, private endpoints, private
DNS VNet links and zones, VNet, storage/host identity, plan, Cosmos account,
Service Bus namespace, Application Insights, and workspace, in dependency order.
Use `az resource delete --ids "<reviewed-resource-id>"`; remove DNS links before
their VNet/zones. Parent service deletion removes its children and scoped
grants. Leave unrelated resources and group metadata untouched.
