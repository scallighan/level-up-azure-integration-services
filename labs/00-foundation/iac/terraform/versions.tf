terraform {
  required_version = "= 1.14.4"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "= 4.52.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "= 2.8.0"
    }
  }
}
