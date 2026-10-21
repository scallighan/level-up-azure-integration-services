targetScope = 'subscription'

@description('3-12 lowercase letters or numbers, starting with a letter.')
@minLength(3)
@maxLength(12)
param prefix string

@description('Azure region with available Windows WS1 quota.')
param location string = 'westus'

@description('Existing resource group in this subscription; leave empty to create a workshop group.')
param existingResourceGroupName string = ''

@description('Confirmed signed-in student user object ID; receives namespace-scoped Service Bus Data Sender.')
@minLength(36)
@maxLength(36)
param publisherPrincipalId string

var resourceGroupName = empty(existingResourceGroupName)
  ? 'rg-${prefix}-lab00-${toLower(replace(location, ' ', ''))}'
  : existingResourceGroupName
var tags = {
  workshop: 'agentic-ais'
  lab: '00'
}

resource foundation 'Microsoft.Resources/resourceGroups@2024-03-01' = if (empty(existingResourceGroupName)) {
  name: resourceGroupName
  location: location
  tags: tags
}

module resources 'resources.bicep' = {
  scope: resourceGroup(resourceGroupName)
  name: 'foundation'
  params: {
    prefix: prefix
    location: location
    tags: tags
    resourceGroupCreated: empty(existingResourceGroupName)
    publisherPrincipalId: publisherPrincipalId
  }
  dependsOn: [foundation]
}

output foundation object = resources.outputs.foundation
