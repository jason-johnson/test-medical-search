data "namep_azure_name" "db" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_account"
}

resource "azurerm_cosmosdb_account" "main" {
  name                      = data.namep_azure_name.db.result
  location                  = var.location
  resource_group_name       = azurerm_resource_group.main.name
  offer_type                = "Standard"
  kind                      = "GlobalDocumentDB"
  enable_automatic_failover = false
  enable_free_tier          = true
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }
  geo_location {
    location          = var.location
    failover_priority = 0
  }
  capabilities {
    name = "EnableServerless"
  }
}

data "namep_custom_name" "sql_db" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_sql_database"
}

resource "azurerm_cosmosdb_sql_database" "main" {
  name                = data.namep_custom_name.sql_db.result
  resource_group_name = azurerm_cosmosdb_account.main.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
}

data "namep_custom_name" "sql_cont" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_sql_container"
}

resource "azurerm_cosmosdb_sql_container" "main" {
  name                  = data.namep_custom_name.sql_cont.result
  resource_group_name   = azurerm_cosmosdb_account.main.resource_group_name
  account_name          = azurerm_cosmosdb_account.main.name
  database_name         = azurerm_cosmosdb_sql_database.main.name
  partition_key_path    = "/id"
  partition_key_version = 1
}