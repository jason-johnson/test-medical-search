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
  kind                      = "MongoDB"
  automatic_failover_enabled  = false
  consistency_policy {
    consistency_level       = "BoundedStaleness"
    max_interval_in_seconds = 300
    max_staleness_prefix    = 100000
  }
  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

data "namep_custom_name" "cosmostable" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_table"
}

data "namep_custom_name" "mongodb" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_mongo_database"
}

resource "azurerm_cosmosdb_mongo_database" "main" {
  name                = data.namep_custom_name.mongodb.result
  resource_group_name = azurerm_cosmosdb_account.main.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  throughput          = 400
}

data "namep_custom_name" "mongocol" {
  name     = "main"
  location = var.location
  type     = "azurerm_cosmosdb_mongo_collection"
}

resource "azurerm_cosmosdb_mongo_collection" "main" {
  name                = data.namep_custom_name.mongocol.result
  resource_group_name = azurerm_cosmosdb_account.main.resource_group_name
  account_name        = azurerm_cosmosdb_account.main.name
  database_name       = azurerm_cosmosdb_mongo_database.main.name

  throughput          = 400

  index {
    keys   = ["_id"]
    unique = true
  }
}