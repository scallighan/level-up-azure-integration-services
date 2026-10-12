param prefix string
param location string
param tags object
param resourceGroupCreated bool

var suffix = take(uniqueString(subscription().subscriptionId, prefix, 'lab00'), 8)
var stem = '${prefix}-lab00'
var storageSuffix = environment().suffixes.storage
var storageServices = ['blob', 'queue', 'table', 'file']
var hostRoles = [
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
  '974c5e8b-45b9-4653-ba55-5f855dd0fb88'
  '0a9a7e1f-b9d0-4cc4-a60d-0319b160aaa3'
]

resource vnet 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: 'vnet-${stem}'
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: ['172.22.0.0/16']
    }
    subnets: [
      {
        name: 'snet-default'
        properties: {
          addressPrefix: '172.22.0.0/24'
          defaultOutboundAccess: false
        }
      }
      {
        name: 'snet-container-apps'
        properties: {
          addressPrefix: '172.22.1.0/24'
          defaultOutboundAccess: false
          delegations: [
            {
              name: 'Microsoft.App/environments'
              properties: {
                serviceName: 'Microsoft.App/environments'
              }
            }
          ]
        }
      }
      {
        name: 'snet-private-endpoints'
        properties: {
          addressPrefix: '172.22.2.0/24'
          defaultOutboundAccess: false
          privateEndpointNetworkPolicies: 'Disabled'
        }
      }
      {
        name: 'snet-logic-app'
        properties: {
          addressPrefix: '172.22.3.0/24'
          defaultOutboundAccess: false
          delegations: [
            {
              name: 'Microsoft.Web/serverFarms'
              properties: {
                serviceName: 'Microsoft.Web/serverFarms'
              }
            }
          ]
        }
      }
    ]
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2025-01-01' = {
  name: 'st${prefix}00${suffix}'
  location: location
  tags: tags
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    accessTier: 'Hot'
    supportsHttpsTrafficOnly: true
    minimumTlsVersion: 'TLS1_2'
    allowBlobPublicAccess: false
    allowSharedKeyAccess: false
    publicNetworkAccess: 'Disabled'
  }
}

resource hostIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-${stem}-host'
  location: location
  tags: tags
}

resource hostRbac 'Microsoft.Authorization/roleAssignments@2022-04-01' = [
  for role in hostRoles: {
    name: guid(storage.id, hostIdentity.id, role)
    scope: storage
    properties: {
      roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', role)
      principalId: hostIdentity.properties.principalId
      principalType: 'ServicePrincipal'
    }
  }
]

resource storageDns 'Microsoft.Network/privateDnsZones@2024-06-01' = [
  for service in storageServices: {
    name: 'privatelink.${service}.${storageSuffix}'
    location: 'global'
    tags: tags
  }
]

resource storageLinks 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [
  for (service, i) in storageServices: {
    parent: storageDns[i]
    name: 'foundation'
    location: 'global'
    tags: tags
    properties: {
      registrationEnabled: false
      virtualNetwork: {
        id: vnet.id
      }
    }
  }
]

resource storageEndpoints 'Microsoft.Network/privateEndpoints@2024-05-01' = [
  for service in storageServices: {
    name: 'pe-${stem}-${service}'
    location: location
    tags: tags
    properties: {
      subnet: {
        id: vnet.properties.subnets[2].id
      }
      privateLinkServiceConnections: [
        {
          name: service
          properties: {
            privateLinkServiceId: storage.id
            groupIds: [service]
          }
        }
      ]
    }
  }
]

resource storageDnsGroups 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = [
  for (service, i) in storageServices: {
    parent: storageEndpoints[i]
    name: 'default'
    properties: {
      privateDnsZoneConfigs: [
        {
          name: service
          properties: {
            privateDnsZoneId: storageDns[i].id
          }
        }
      ]
    }
  }
]

resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: 'log-${stem}'
  location: location
  tags: tags
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

resource insights 'Microsoft.Insights/components@2020-02-02' = {
  name: 'appi-${stem}'
  location: location
  tags: tags
  kind: 'other'
  properties: {
    Application_Type: 'other'
    WorkspaceResourceId: workspace.id
  }
}

resource plan 'Microsoft.Web/serverfarms@2025-03-01' = {
  name: 'plan-${stem}'
  location: location
  tags: tags
  kind: 'windows'
  sku: {
    name: 'WS1'
    tier: 'WorkflowStandard'
  }
  properties: {
    reserved: false
  }
}

resource cosmos 'Microsoft.DocumentDB/databaseAccounts@2025-04-15' = {
  name: 'cosmos-${stem}-${suffix}'
  location: location
  tags: tags
  kind: 'GlobalDocumentDB'
  properties: {
    databaseAccountOfferType: 'Standard'
    disableLocalAuth: true
    publicNetworkAccess: 'Disabled'
    consistencyPolicy: {
      defaultConsistencyLevel: 'Session'
    }
    capabilities: [
      { name: 'EnableServerless' }
    ]
    locations: [
      {
        locationName: location
        failoverPriority: 0
        isZoneRedundant: false
      }
    ]
  }
}

resource database 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases@2025-04-15' = {
  parent: cosmos
  name: 'workshop'
  properties: {
    resource: {
      id: 'workshop'
    }
  }
}

resource items 'Microsoft.DocumentDB/databaseAccounts/sqlDatabases/containers@2025-04-15' = {
  parent: database
  name: 'items'
  properties: {
    resource: {
      id: 'items'
      partitionKey: {
        paths: ['/id']
        kind: 'Hash'
        version: 2
      }
      indexingPolicy: {
        indexingMode: 'consistent'
        automatic: true
        includedPaths: [
          { path: '/*' }
        ]
        excludedPaths: [
          { path: '/"_etag"/?' }
        ]
      }
    }
  }
}

resource cosmosDns 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: 'privatelink.documents.azure.com'
  location: 'global'
  tags: tags
}

resource cosmosLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: cosmosDns
  name: 'foundation'
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    virtualNetwork: {
      id: vnet.id
    }
  }
}

resource cosmosEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: 'pe-${stem}-cosmos'
  location: location
  tags: tags
  properties: {
    subnet: {
      id: vnet.properties.subnets[2].id
    }
    privateLinkServiceConnections: [
      {
        name: 'cosmos'
        properties: {
          privateLinkServiceId: cosmos.id
          groupIds: ['Sql']
        }
      }
    ]
  }
}

resource cosmosDnsGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: cosmosEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'cosmos'
        properties: {
          privateDnsZoneId: cosmosDns.id
        }
      }
    ]
  }
}

resource serviceBus 'Microsoft.ServiceBus/namespaces@2024-01-01' = {
  name: 'sb-${stem}-${suffix}'
  location: location
  tags: tags
  sku: {
    name: 'Standard'
    tier: 'Standard'
  }
  properties: {
    disableLocalAuth: true
    minimumTlsVersion: '1.2'
    publicNetworkAccess: 'Enabled'
  }
}

resource site 'Microsoft.Web/sites@2025-03-01' = {
  name: 'la-${stem}-${suffix}'
  location: location
  tags: tags
  kind: 'functionapp,workflowapp'
  identity: {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${hostIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: plan.id
    httpsOnly: true
    virtualNetworkSubnetId: vnet.properties.subnets[3].id
    outboundVnetRouting: {
      allTraffic: true
    }
    siteConfig: {
      minTlsVersion: '1.2'
      scmMinTlsVersion: '1.2'
      ftpsState: 'Disabled'
      appSettings: [
        { name: 'FUNCTIONS_EXTENSION_VERSION', value: '~4' }
        { name: 'FUNCTIONS_WORKER_RUNTIME', value: 'dotnet' }
        { name: 'AzureWebJobsStorage__credential', value: 'managedidentity' }
        { name: 'AzureWebJobsStorage__blobServiceUri', value: 'https://${storage.name}.blob.${storageSuffix}' }
        { name: 'AzureWebJobsStorage__queueServiceUri', value: 'https://${storage.name}.queue.${storageSuffix}' }
        { name: 'AzureWebJobsStorage__tableServiceUri', value: 'https://${storage.name}.table.${storageSuffix}' }
        { name: 'AzureWebJobsStorage__managedIdentityResourceId', value: hostIdentity.id }
        {
          name: 'AzureFunctionsJobHost__extensionBundle__id'
          value: 'Microsoft.Azure.Functions.ExtensionBundle.Workflows'
        }
        { name: 'AzureFunctionsJobHost__extensionBundle__version', value: '[1.*, 2.0.0)' }
        { name: 'APP_KIND', value: 'workflowApp' }
        { name: 'FUNCTIONS_INPROC_NET8_ENABLED', value: '1' }
        { name: 'LOGIC_APPS_POWERSHELL_VERSION', value: '7.4' }
        { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', value: insights.properties.ConnectionString }
        { name: 'AzureCosmosDB_accountEndpoint', value: cosmos.properties.documentEndpoint }
        { name: 'AzureCosmosDB_databaseName', value: database.name }
        { name: 'AzureCosmosDB_containerName', value: items.name }
        { name: 'ServiceBus_namespace', value: '${serviceBus.name}.servicebus.windows.net' }
      ]
    }
  }
  dependsOn: [
    hostRbac
    storageLinks
    storageDnsGroups
    cosmosLink
    cosmosDnsGroup
  ]
}

resource cosmosRbac 'Microsoft.DocumentDB/databaseAccounts/sqlRoleAssignments@2025-04-15' = {
  parent: cosmos
  name: guid(cosmos.id, site.id, 'items-data-contributor')
  properties: {
    roleDefinitionId: '${cosmos.id}/sqlRoleDefinitions/00000000-0000-0000-0000-000000000002'
    principalId: site.identity.principalId
    scope: '${cosmos.id}/dbs/${database.name}/colls/${items.name}'
  }
}

output foundation object = {
  resource_group_name: resourceGroup().name
  resource_group_created: resourceGroupCreated
  location: location
  virtual_network_id: vnet.id
  integration_subnet_id: vnet.properties.subnets[3].id
  private_endpoint_subnet_id: vnet.properties.subnets[2].id
  host_storage_id: storage.id
  host_storage_identity_id: hostIdentity.id
  service_plan_id: plan.id
  logic_app_id: site.id
  logic_app_name: site.name
  logic_app_principal_id: site.identity.principalId
  cosmos_account_id: cosmos.id
  cosmos_account_name: cosmos.name
  cosmos_account_endpoint: cosmos.properties.documentEndpoint
  cosmos_database_name: database.name
  cosmos_container_name: items.name
  service_bus_namespace_id: serviceBus.id
  service_bus_namespace_name: serviceBus.name
  service_bus_fqdn: '${serviceBus.name}.servicebus.windows.net'
  application_insights_id: insights.id
  log_analytics_workspace_id: workspace.id
}
