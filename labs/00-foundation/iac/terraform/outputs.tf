output "foundation" {
  description = "Non-secret references consumed by later labs; identical field names in both tracks."
  value = {
    resource_group_name        = local.resource_group_name
    resource_group_created     = var.existing_resource_group_name == ""
    location                   = var.location
    virtual_network_id         = azurerm_virtual_network.foundation.id
    integration_subnet_id      = azurerm_subnet.foundation["logic-app"].id
    private_endpoint_subnet_id = azurerm_subnet.foundation["private-endpoints"].id
    host_storage_id            = azapi_resource.storage.id
    host_storage_identity_id   = azurerm_user_assigned_identity.host_storage.id
    service_plan_id            = azurerm_service_plan.foundation.id
    logic_app_id               = azapi_resource.logic_app.id
    logic_app_name             = azapi_resource.logic_app.name
    logic_app_principal_id     = azapi_resource.logic_app.identity[0].principal_id
    cosmos_account_id          = azurerm_cosmosdb_account.foundation.id
    cosmos_account_name        = azurerm_cosmosdb_account.foundation.name
    cosmos_account_endpoint    = azurerm_cosmosdb_account.foundation.endpoint
    cosmos_database_name       = azurerm_cosmosdb_sql_database.workshop.name
    cosmos_container_name      = azurerm_cosmosdb_sql_container.items.name
    service_bus_namespace_id   = azurerm_servicebus_namespace.foundation.id
    service_bus_namespace_name = azurerm_servicebus_namespace.foundation.name
    service_bus_fqdn           = "${azurerm_servicebus_namespace.foundation.name}.servicebus.windows.net"
    application_insights_id    = azurerm_application_insights.foundation.id
    log_analytics_workspace_id = azurerm_log_analytics_workspace.foundation.id
  }
}
