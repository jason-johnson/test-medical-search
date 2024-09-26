terraform {
//  backend "azurerm" {}
  backend "local" { }
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
    azurerm_key_vault = "#{SLUG}-ZI-#{TOKEN_2}-#{SHORT_LOC}-#{NAME}#{-BRANCH}"
  }

  custom_resource_formats = {
    azurerm_cosmosdb_mongo_database = "#{TOKEN_1}"
    azurerm_cosmosdb_mongo_collection = "#{TOKEN_1}-collection"
    azurerm_cosmosdb_table = "#{TOKEN_1}"
  }
}

data "azuread_client_config" "current" {}

data "azurerm_client_config" "current" {}