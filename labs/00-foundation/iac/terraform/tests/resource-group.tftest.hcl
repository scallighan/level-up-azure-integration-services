mock_provider "azurerm" {
  mock_data "azurerm_resource_group" {
    defaults = {
      id       = "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/student-existing"
      location = "eastus"
      tags     = { owner = "student" }
    }
  }
}

mock_provider "azapi" {}

variables {
  subscription_id = "00000000-0000-0000-0000-000000000001"
  prefix          = "student"
  location        = "westus"
}

run "create_group_when_no_existing_name" {
  command = plan

  assert {
    condition     = length(azurerm_resource_group.foundation) == 1 && length(data.azurerm_resource_group.existing) == 0 && output.foundation.resource_group_created
    error_message = "An empty existing name must create exactly one workshop-owned group."
  }

  assert {
    condition     = azurerm_virtual_network.foundation.resource_group_name == azurerm_resource_group.foundation[0].name
    error_message = "The foundation must deploy into the newly created group."
  }
}

run "reference_existing_without_group_ownership" {
  command = plan
  variables {
    existing_resource_group_name = "student-existing"
  }

  assert {
    condition     = length(azurerm_resource_group.foundation) == 0 && length(data.azurerm_resource_group.existing) == 1 && !output.foundation.resource_group_created
    error_message = "An existing parent group must be a data source, never a managed resource."
  }

  assert {
    condition = (
      azurerm_virtual_network.foundation.resource_group_name == "student-existing" &&
      azapi_resource.storage.parent_id == data.azurerm_resource_group.existing[0].id &&
      azapi_resource.logic_app.parent_id == data.azurerm_resource_group.existing[0].id &&
      azurerm_virtual_network.foundation.location == "westus" &&
      data.azurerm_resource_group.existing[0].tags == tomap({ owner = "student" })
    )
    error_message = "Use the existing group ID without inheriting its metadata region or retagging it."
  }
}
