terraform {
  backend "azurerm" {}
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

provider "namep" {
  slice_string                 = "ZI DEV"
  default_location             = var.location
  default_nodash_name_format   = "#{SLUG}#{TOKEN_1}#{TOKEN_2}#{SHORT_LOC}#{NAME}#{BRANCH}"
  default_resource_name_format = "#{SLUG}-#{TOKEN_1}-#{TOKEN_2}-#{SHORT_LOC}-#{NAME}#{-BRANCH}"

  extra_tokens = {
    branch = var.branch
  }

  azure_resource_formats = {
    azurerm_key_vault = "#{SLUG}-gath-#{TOKEN_2}-#{SHORT_LOC}-#{NAME}#{-BRANCH}"
  }

  custom_resource_formats = {
    azuread_application_registration = "app-#{TOKEN_1}-#{TOKEN_2}-#{SHORT_LOC}-#{NAME}#{-BRANCH}"
    azurerm_cosmosdb_sql_database = "#{TOKEN_1}"
    azurerm_cosmosdb_sql_container = "#{TOKEN_1}-container"
  }
}

data "azuread_client_config" "current" {}

data "azurerm_client_config" "current" {}