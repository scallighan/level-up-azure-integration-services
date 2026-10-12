locals {
  suffix = substr(sha1("${var.subscription_id}:${var.prefix}:lab00"), 0, 8)
  stem   = "${var.prefix}-lab00"
  tags = {
    workshop = "agentic-ais"
    lab      = "00"
  }
  subnets = {
    default           = { prefix = "172.22.0.0/24", delegation = null }
    container-apps    = { prefix = "172.22.1.0/24", delegation = "Microsoft.App/environments" }
    private-endpoints = { prefix = "172.22.2.0/24", delegation = null }
    logic-app         = { prefix = "172.22.3.0/24", delegation = "Microsoft.Web/serverFarms" }
  }
  storage_services = toset(["blob", "queue", "table", "file"])
  host_roles = toset([
    "Storage Blob Data Contributor",
    "Storage Queue Data Contributor",
    "Storage Table Data Contributor",
  ])
  resource_group_name = var.existing_resource_group_name == "" ? azurerm_resource_group.foundation[0].name : data.azurerm_resource_group.existing[0].name
  resource_group_id   = var.existing_resource_group_name == "" ? azurerm_resource_group.foundation[0].id : data.azurerm_resource_group.existing[0].id
}

resource "azurerm_resource_group" "foundation" {
  count = var.existing_resource_group_name == "" ? 1 : 0

  name     = "rg-${local.stem}-${var.location}"
  location = var.location
  tags     = local.tags
}

data "azurerm_resource_group" "existing" {
  count = var.existing_resource_group_name == "" ? 0 : 1
  name  = var.existing_resource_group_name
}

resource "azurerm_virtual_network" "foundation" {
  name                = "vnet-${local.stem}"
  resource_group_name = local.resource_group_name
  location            = var.location
  address_space       = ["172.22.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "foundation" {
  for_each = local.subnets

  name                              = "snet-${each.key}"
  resource_group_name               = local.resource_group_name
  virtual_network_name              = azurerm_virtual_network.foundation.name
  address_prefixes                  = [each.value.prefix]
  default_outbound_access_enabled   = false
  private_endpoint_network_policies = "Disabled"

  dynamic "delegation" {
    for_each = each.value.delegation == null ? [] : [each.value.delegation]
    content {
      name = delegation.value
      service_delegation {
        name = delegation.value
        actions = [
          delegation.value == "Microsoft.Web/serverFarms" ?
          "Microsoft.Network/virtualNetworks/subnets/action" :
          "Microsoft.Network/virtualNetworks/subnets/join/action"
        ]
      }
    }
  }
}

# AzAPI manages keyless storage without fetching access keys or using the data plane.
resource "azapi_resource" "storage" {
  type      = "Microsoft.Storage/storageAccounts@2025-01-01"
  name      = "st${var.prefix}00${local.suffix}"
  parent_id = local.resource_group_id
  location  = var.location
  tags      = local.tags
  body = {
    kind = "StorageV2"
    sku  = { name = "Standard_LRS" }
    properties = {
      accessTier               = "Hot"
      supportsHttpsTrafficOnly = true
      minimumTlsVersion        = "TLS1_2"
      allowBlobPublicAccess    = false
      allowSharedKeyAccess     = false
      publicNetworkAccess      = "Disabled"
    }
  }
}

resource "azurerm_user_assigned_identity" "host_storage" {
  name                = "id-${local.stem}-host"
  resource_group_name = local.resource_group_name
  location            = var.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "host_storage" {
  for_each = local.host_roles

  name                 = uuidv5("url", "${azapi_resource.storage.id}/${azurerm_user_assigned_identity.host_storage.id}/${each.value}")
  scope                = azapi_resource.storage.id
  role_definition_name = each.value
  principal_id         = azurerm_user_assigned_identity.host_storage.principal_id
  principal_type       = "ServicePrincipal"
}

resource "azurerm_private_dns_zone" "storage" {
  for_each = local.storage_services

  name                = "privatelink.${each.key}.core.windows.net"
  resource_group_name = local.resource_group_name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "storage" {
  for_each = local.storage_services

  name                  = "foundation"
  resource_group_name   = local.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.storage[each.key].name
  virtual_network_id    = azurerm_virtual_network.foundation.id
  registration_enabled  = false
  tags                  = local.tags
}

resource "azurerm_private_endpoint" "storage" {
  for_each = local.storage_services

  name                = "pe-${local.stem}-${each.key}"
  resource_group_name = local.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.foundation["private-endpoints"].id
  tags                = local.tags

  private_service_connection {
    name                           = each.key
    private_connection_resource_id = azapi_resource.storage.id
    subresource_names              = [each.key]
    is_manual_connection           = false
  }

  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.storage[each.key].id]
  }
}

resource "azurerm_log_analytics_workspace" "foundation" {
  name                = "log-${local.stem}"
  resource_group_name = local.resource_group_name
  location            = var.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_application_insights" "foundation" {
  name                = "appi-${local.stem}"
  resource_group_name = local.resource_group_name
  location            = var.location
  application_type    = "other"
  workspace_id        = azurerm_log_analytics_workspace.foundation.id
  tags                = local.tags
}

resource "azurerm_service_plan" "foundation" {
  name                = "plan-${local.stem}"
  resource_group_name = local.resource_group_name
  location            = var.location
  os_type             = "Windows"
  sku_name            = "WS1"
  tags                = local.tags
}

resource "azurerm_cosmosdb_account" "foundation" {
  name                          = "cosmos-${local.stem}-${local.suffix}"
  resource_group_name           = local.resource_group_name
  location                      = var.location
  offer_type                    = "Standard"
  kind                          = "GlobalDocumentDB"
  local_authentication_disabled = true
  public_network_access_enabled = false
  tags                          = local.tags

  consistency_policy {
    consistency_level = "Session"
  }
  capabilities {
    name = "EnableServerless"
  }
  geo_location {
    location          = var.location
    failover_priority = 0
    zone_redundant    = false
  }
}

resource "azurerm_cosmosdb_sql_database" "workshop" {
  name                = "workshop"
  resource_group_name = local.resource_group_name
  account_name        = azurerm_cosmosdb_account.foundation.name
}

resource "azurerm_cosmosdb_sql_container" "items" {
  name                  = "items"
  resource_group_name   = local.resource_group_name
  account_name          = azurerm_cosmosdb_account.foundation.name
  database_name         = azurerm_cosmosdb_sql_database.workshop.name
  partition_key_paths   = ["/id"]
  partition_key_version = 2

  indexing_policy {
    indexing_mode = "consistent"
    included_path {
      path = "/*"
    }
    excluded_path {
      path = "/\"_etag\"/?"
    }
  }
}

resource "azurerm_private_dns_zone" "cosmos" {
  name                = "privatelink.documents.azure.com"
  resource_group_name = local.resource_group_name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "cosmos" {
  name                  = "foundation"
  resource_group_name   = local.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.cosmos.name
  virtual_network_id    = azurerm_virtual_network.foundation.id
  registration_enabled  = false
  tags                  = local.tags
}

resource "azurerm_private_endpoint" "cosmos" {
  name                = "pe-${local.stem}-cosmos"
  resource_group_name = local.resource_group_name
  location            = var.location
  subnet_id           = azurerm_subnet.foundation["private-endpoints"].id
  tags                = local.tags

  private_service_connection {
    name                           = "cosmos"
    private_connection_resource_id = azurerm_cosmosdb_account.foundation.id
    subresource_names              = ["Sql"]
    is_manual_connection           = false
  }
  private_dns_zone_group {
    name                 = "default"
    private_dns_zone_ids = [azurerm_private_dns_zone.cosmos.id]
  }
}

resource "azurerm_servicebus_namespace" "foundation" {
  name                          = "sb-${local.stem}-${local.suffix}"
  resource_group_name           = local.resource_group_name
  location                      = var.location
  sku                           = "Standard"
  local_auth_enabled            = false
  minimum_tls_version           = "1.2"
  public_network_access_enabled = true
  tags                          = local.tags
}

# AzureRM's Standard Logic App resource requires a storage key; AzAPI preserves dual identities.
resource "azapi_resource" "logic_app" {
  type      = "Microsoft.Web/sites@2025-03-01"
  name      = "la-${local.stem}-${local.suffix}"
  parent_id = local.resource_group_id
  location  = var.location
  tags      = local.tags

  identity {
    type         = "SystemAssigned, UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.host_storage.id]
  }

  body = {
    kind = "functionapp,workflowapp"
    properties = {
      serverFarmId           = replace(azurerm_service_plan.foundation.id, "serverFarms", "serverfarms")
      httpsOnly              = true
      virtualNetworkSubnetId = azurerm_subnet.foundation["logic-app"].id
      outboundVnetRouting    = { allTraffic = true }
      siteConfig = {
        minTlsVersion    = "1.2"
        scmMinTlsVersion = "1.2"
        ftpsState        = "Disabled"
        appSettings = [
          { name = "FUNCTIONS_EXTENSION_VERSION", value = "~4" },
          { name = "FUNCTIONS_WORKER_RUNTIME", value = "dotnet" },
          { name = "AzureWebJobsStorage__credential", value = "managedidentity" },
          { name = "AzureWebJobsStorage__blobServiceUri", value = "https://${azapi_resource.storage.name}.blob.core.windows.net" },
          { name = "AzureWebJobsStorage__queueServiceUri", value = "https://${azapi_resource.storage.name}.queue.core.windows.net" },
          { name = "AzureWebJobsStorage__tableServiceUri", value = "https://${azapi_resource.storage.name}.table.core.windows.net" },
          { name = "AzureWebJobsStorage__managedIdentityResourceId", value = azurerm_user_assigned_identity.host_storage.id },
          { name = "AzureFunctionsJobHost__extensionBundle__id", value = "Microsoft.Azure.Functions.ExtensionBundle.Workflows" },
          { name = "AzureFunctionsJobHost__extensionBundle__version", value = "[1.*, 2.0.0)" },
          { name = "APP_KIND", value = "workflowApp" },
          { name = "FUNCTIONS_INPROC_NET8_ENABLED", value = "1" },
          { name = "LOGIC_APPS_POWERSHELL_VERSION", value = "7.4" },
          { name = "APPLICATIONINSIGHTS_CONNECTION_STRING", value = azurerm_application_insights.foundation.connection_string },
          { name = "AzureCosmosDB_accountEndpoint", value = azurerm_cosmosdb_account.foundation.endpoint },
          { name = "AzureCosmosDB_databaseName", value = azurerm_cosmosdb_sql_database.workshop.name },
          { name = "AzureCosmosDB_containerName", value = azurerm_cosmosdb_sql_container.items.name },
          { name = "ServiceBus_namespace", value = "${azurerm_servicebus_namespace.foundation.name}.servicebus.windows.net" },
        ]
      }
    }
  }

  depends_on = [
    azurerm_role_assignment.host_storage,
    azurerm_private_endpoint.storage,
    azurerm_private_dns_zone_virtual_network_link.storage,
    azurerm_private_endpoint.cosmos,
    azurerm_private_dns_zone_virtual_network_link.cosmos,
  ]
}

resource "azurerm_cosmosdb_sql_role_assignment" "items" {
  name                = uuidv5("url", "${azurerm_cosmosdb_sql_container.items.id}/${azapi_resource.logic_app.id}/data-contributor")
  resource_group_name = local.resource_group_name
  account_name        = azurerm_cosmosdb_account.foundation.name
  role_definition_id  = "${azurerm_cosmosdb_account.foundation.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002"
  principal_id        = azapi_resource.logic_app.identity[0].principal_id
  scope               = "${azurerm_cosmosdb_account.foundation.id}/dbs/workshop/colls/items"
}
