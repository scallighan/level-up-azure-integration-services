variable "subscription_id" {
  description = "Azure subscription for the shared workshop foundation."
  type        = string

  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "subscription_id must be an Azure subscription UUID."
  }
}

variable "prefix" {
  description = "3-12 lowercase letters or numbers, starting with a letter."
  type        = string

  validation {
    condition     = can(regex("^[a-z][a-z0-9]{2,11}$", var.prefix))
    error_message = "prefix must be 3-12 lowercase letters or numbers, starting with a letter."
  }
}

variable "location" {
  description = "Azure region with available Windows WS1 quota."
  type        = string
  default     = "westus"

  validation {
    condition     = can(regex("^[a-z][a-z0-9]+$", var.location))
    error_message = "location must be an Azure region identifier, such as westus."
  }

}

variable "existing_resource_group_name" {
  description = "Existing resource group in this subscription; leave empty to create a workshop group."
  type        = string
  default     = ""

  validation {
    condition     = var.existing_resource_group_name == trimspace(var.existing_resource_group_name)
    error_message = "existing_resource_group_name must not contain leading or trailing whitespace."
  }
}
