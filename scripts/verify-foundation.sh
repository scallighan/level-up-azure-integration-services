#!/usr/bin/env bash
set -euo pipefail

handoff="${1:-foundation.deployment.json}"
[[ -s "$handoff" ]] || {
  echo "Missing foundation handoff: $handoff" >&2
  exit 1
}

require() {
  local json="$1" expression="$2" message="$3"
  shift 3
  if ! jq "$@" -e "$expression" >/dev/null <<<"$json"; then
    echo "Foundation check failed: $message" >&2
    exit 1
  fi
}

foundation="$(jq -e 'select(type == "object")' "$handoff")"
require "$foundation" '
  [.resource_group_name, .location, .publisher_principal_id, .virtual_network_id, .integration_subnet_id,
   .private_endpoint_subnet_id, .host_storage_id, .host_storage_identity_id,
   .service_plan_id, .logic_app_id, .logic_app_name, .logic_app_principal_id,
   .cosmos_account_id, .cosmos_account_name, .cosmos_account_endpoint,
   .cosmos_database_name, .cosmos_container_name, .service_bus_namespace_id,
   .service_bus_namespace_name, .service_bus_fqdn, .application_insights_id,
   .log_analytics_workspace_id] | all(.[]; type == "string" and length > 0)
' "handoff must contain every non-secret foundation reference"
require "$foundation" '.resource_group_created | type == "boolean"' \
  "handoff must record parent resource-group ownership"

rg="$(jq -r .resource_group_name <<<"$foundation")"
site_id="$(jq -r .logic_app_id <<<"$foundation")"
site_name="$(jq -r .logic_app_name <<<"$foundation")"
storage_id="$(jq -r .host_storage_id <<<"$foundation")"
identity_id="$(jq -r .host_storage_identity_id <<<"$foundation")"
cosmos_id="$(jq -r .cosmos_account_id <<<"$foundation")"
plan_id="$(jq -r .service_plan_id <<<"$foundation")"
bus_id="$(jq -r .service_bus_namespace_id <<<"$foundation")"
insights_id="$(jq -r .application_insights_id <<<"$foundation")"
workspace_id="$(jq -r .log_analytics_workspace_id <<<"$foundation")"
vnet_id="$(jq -r .virtual_network_id <<<"$foundation")"
subnet_id="$(jq -r .integration_subnet_id <<<"$foundation")"
principal_id="$(jq -r .logic_app_principal_id <<<"$foundation")"
echo "Checking Azure subscription and handoff (Azure queries may take several minutes)..."
subscription_id="$(az account show --query id -o tsv)"
require "$foundation" '
  [.virtual_network_id, .integration_subnet_id, .private_endpoint_subnet_id,
   .host_storage_id, .host_storage_identity_id, .service_plan_id, .logic_app_id,
   .cosmos_account_id, .service_bus_namespace_id, .application_insights_id,
   .log_analytics_workspace_id] |
  all(.[]; ascii_downcase | startswith(
    ("/subscriptions/" + $subscription + "/resourceGroups/" + $rg + "/") | ascii_downcase))
' "select the subscription and group recorded in the handoff" \
  --arg subscription "$subscription_id" --arg rg "$rg"

echo "Checking Logic App site, identities and routing..."
site="$(az resource show --ids "$site_id" --api-version 2025-03-01 -o json)"
require "$site" '
  (.kind | contains("functionapp") and contains("workflowapp")) and
  (.identity.type | contains("SystemAssigned") and contains("UserAssigned")) and
  .identity.principalId == $principal and
  (.identity.userAssignedIdentities | keys |
    any(.[]; ascii_downcase == ($identity | ascii_downcase))) and
  (.properties.serverFarmId | ascii_downcase) == ($plan | ascii_downcase) and
  (.properties.virtualNetworkSubnetId | ascii_downcase) == ($subnet | ascii_downcase) and
  .properties.httpsOnly == true and .properties.outboundVnetRouting.allTraffic == true
' "Standard site, dual identities, HTTPS, plan, VNet integration and route-all" \
  --arg principal "$principal_id" --arg identity "$identity_id" \
  --arg plan "$plan_id" --arg subnet "$subnet_id"

echo "Checking Windows WS1 plan..."
plan="$(az resource show --ids "$plan_id" --api-version 2025-03-01 -o json)"
require "$plan" '.sku.name == "WS1" and .properties.reserved == false' "Windows WS1 plan"

echo "Checking VNet, subnets and delegations..."
vnet="$(az network vnet show --ids "$vnet_id" -o json)"
require "$vnet" '
  .addressSpace.addressPrefixes == ["172.22.0.0/16"] and
  (.subnets | length == 4) and
  all(.subnets[]; .defaultOutboundAccess == false) and
  any(.subnets[]; .name == "snet-logic-app" and
    any(.delegations[]; .serviceName == "Microsoft.Web/serverFarms")) and
  any(.subnets[]; .name == "snet-container-apps" and
    any(.delegations[]; .serviceName == "Microsoft.App/environments"))
' "reference VNet, private subnets and delegations"

echo "Checking private host storage..."
storage="$(az resource show --ids "$storage_id" --api-version 2025-01-01 -o json)"
require "$storage" '
  .kind == "StorageV2" and .sku.name == "Standard_LRS" and
  .properties.accessTier == "Hot" and .properties.supportsHttpsTrafficOnly == true and
  .properties.minimumTlsVersion == "TLS1_2" and .properties.allowBlobPublicAccess == false and
  .properties.allowSharedKeyAccess == false and .properties.publicNetworkAccess == "Disabled"
' "private, keyless, HTTPS-only host storage"

echo "Checking host-storage identity and roles..."
host_principal="$(az identity show --ids "$identity_id" --query principalId -o tsv)"
roles="$(az role assignment list --scope "$storage_id" -o json)"
for role in ba92f5b4-2d11-453d-a403-e96b0029c9fe \
  974c5e8b-45b9-4653-ba55-5f855dd0fb88 0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3; do
  require "$roles" '
    any(.[]; .principalId == $principal and
      (.scope | ascii_downcase) == ($storage | ascii_downcase) and
      (.roleDefinitionId | endswith($role)))
  ' "host-storage identity role $role" \
    --arg principal "$host_principal" --arg storage "$storage_id" --arg role "$role"
done

echo "Checking Cosmos DB, container and workload role..."
cosmos="$(az resource show --ids "$cosmos_id" --api-version 2025-04-15 -o json)"
require "$cosmos" '
  .properties.publicNetworkAccess == "Disabled" and .properties.disableLocalAuth == true and
  any(.properties.capabilities[]; .name == "EnableServerless")
' "private serverless Cosmos with local authentication disabled"

cosmos_name="$(jq -r .cosmos_account_name <<<"$foundation")"
container="$(az cosmosdb sql container show -g "$rg" -a "$cosmos_name" \
  -d workshop -n items -o json)"
require "$container" '.resource.partitionKey.paths == ["/id"]' "items partition key /id"
cosmos_roles="$(az cosmosdb sql role assignment list -g "$rg" -a "$cosmos_name" -o json)"
require "$cosmos_roles" '
  any(.[]; .principalId == $principal and
    (.scope | endswith("/dbs/workshop/colls/items")) and
    (.roleDefinitionId | endswith("/00000000-0000-0000-0000-000000000002")))
' "site system identity Cosmos contributor at container scope" --arg principal "$principal_id"

echo "Checking private endpoints..."
endpoints="$(az network private-endpoint list -g "$rg" -o json)"
for service in blob queue table file Sql; do
  echo "Checking $service private endpoint and DNS..."
  target_id="$storage_id"
  zone="privatelink.${service}.core.windows.net"
  if [[ "$service" == "Sql" ]]; then
    target_id="$cosmos_id"
    zone="privatelink.documents.azure.com"
  fi
  endpoint="$(jq --arg id "$target_id" --arg service "$service" '
    [.[] | select(any(.privateLinkServiceConnections[];
      (.privateLinkServiceId | ascii_downcase) == ($id | ascii_downcase) and
      (.groupIds | index($service)) != null))] |
    if length == 1 then .[0] else error("Expected exactly one private endpoint for " + $service) end
  ' <<<"$endpoints")"
  require "$endpoint" '
    .provisioningState == "Succeeded" and
    all(.privateLinkServiceConnections[]; .privateLinkServiceConnectionState.status == "Approved")
  ' "approved $service private endpoint"
  endpoint_name="$(jq -r .name <<<"$endpoint")"
  groups="$(az network private-endpoint dns-zone-group list -g "$rg" \
    --endpoint-name "$endpoint_name" -o json)"
  require "$groups" '
    any(.[]; any(.privateDnsZoneConfigs[]; .privateDnsZoneId | endswith("/" + $zone)))
  ' "$service endpoint private DNS zone group" --arg zone "$zone"
  links="$(az network private-dns link vnet list -g "$rg" -z "$zone" -o json)"
  require "$links" '
    any(.[]; (.virtualNetwork.id | ascii_downcase) == ($vnet | ascii_downcase) and
      .provisioningState == "Succeeded" and .registrationEnabled == false)
  ' "$service DNS VNet link" --arg vnet "$vnet_id"
  records="$(az network private-dns record-set a list -g "$rg" -z "$zone" -o json)"
  record_name="$(jq -r .name <<<"$storage")"
  [[ "$service" != "Sql" ]] || record_name="$cosmos_name"
  require "$records" '
    any(.[]; .name == $record and (.aRecords | length > 0))
  ' "$service private DNS A record" --arg record "$record_name"
done

echo "Checking Service Bus authorization..."
bus="$(az resource show --ids "$bus_id" --api-version 2024-01-01 -o json)"
require "$bus" '
  .sku.name == "Standard" and .properties.disableLocalAuth == true and
  .properties.minimumTlsVersion == "1.2" and .properties.publicNetworkAccess == "Enabled"
' "Service Bus Standard with Entra-only authorization"

echo "Checking student publisher access..."
publisher_roles="$(az role assignment list --scope "$bus_id" -o json)"
require "$publisher_roles" '
  any(.[]; (.principalId | ascii_downcase) == ($principal | ascii_downcase) and
    .principalType == "User" and
    (.scope | ascii_downcase) == ($namespace | ascii_downcase) and
    (.roleDefinitionId | endswith("/69a216fc-b8fb-44d8-bc22-1f3c2cd27a39")))
' "confirmed student user Data Sender at namespace scope" \
  --arg principal "$(jq -r .publisher_principal_id <<<"$foundation")" --arg namespace "$bus_id"

echo "Checking Application Insights and monitoring workspace..."
insights="$(az resource show --ids "$insights_id" --api-version 2020-02-02 -o json)"
require "$insights" '
  (.properties.WorkspaceResourceId | ascii_downcase) == ($workspace | ascii_downcase)
' "Application Insights workspace link" --arg workspace "$workspace_id"
workspace="$(az resource show --ids "$workspace_id" --api-version 2023-09-01 -o json)"
require "$workspace" '.properties.retentionInDays == 30' "30-day monitoring retention"

echo "Checking Logic App host settings..."
settings="$(az webapp config appsettings list --resource-group "$rg" --name "$site_name" \
  --query "[?starts_with(name, 'AzureWebJobsStorage__') || name=='FUNCTIONS_EXTENSION_VERSION' || name=='FUNCTIONS_WORKER_RUNTIME' || name=='APP_KIND' || name=='FUNCTIONS_INPROC_NET8_ENABLED' || name=='LOGIC_APPS_POWERSHELL_VERSION' || starts_with(name, 'AzureFunctionsJobHost__extensionBundle__')].{name:name,value:value}" -o json)"
require "$settings" '
  (map({key: .name, value: .value}) | from_entries) as $s |
  $s.AzureWebJobsStorage__credential == "managedidentity" and
  $s.AzureWebJobsStorage__managedIdentityResourceId == $identity and
  $s.AzureWebJobsStorage__blobServiceUri == ("https://" + $storage + ".blob.core.windows.net") and
  $s.AzureWebJobsStorage__queueServiceUri == ("https://" + $storage + ".queue.core.windows.net") and
  $s.AzureWebJobsStorage__tableServiceUri == ("https://" + $storage + ".table.core.windows.net") and
  $s.FUNCTIONS_EXTENSION_VERSION == "~4" and $s.FUNCTIONS_WORKER_RUNTIME == "dotnet" and
  $s.APP_KIND == "workflowApp" and $s.FUNCTIONS_INPROC_NET8_ENABLED == "1" and
  $s.LOGIC_APPS_POWERSHELL_VERSION == "7.4" and
  $s.AzureFunctionsJobHost__extensionBundle__id == "Microsoft.Azure.Functions.ExtensionBundle.Workflows" and
  $s.AzureFunctionsJobHost__extensionBundle__version == "[1.*, 2.0.0)"
' "reference host settings and identity-based storage URIs" \
  --arg identity "$identity_id" --arg storage "$(jq -r .name <<<"$storage")"
echo "Checking Logic App telemetry setting..."
monitoring_count="$(az webapp config appsettings list --resource-group "$rg" --name "$site_name" \
  --query "length([?name=='APPLICATIONINSIGHTS_CONNECTION_STRING' && value!=''])" -o tsv)"
[[ "$monitoring_count" == 1 ]] || {
  echo "Foundation check failed: missing Application Insights host setting" >&2
  exit 1
}

echo "Foundation provisioning checks passed. Later labs must still test workflow data access and telemetry."
