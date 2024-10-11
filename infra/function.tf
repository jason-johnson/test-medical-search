data "namep_azure_name" "sa" {
  name     = "main"
  location = "westeurope"
  type     = "azurerm_storage_account"
}

resource "azurerm_storage_account" "main" {
  name                     = data.namep_azure_name.sa.result
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

data "namep_azure_name" "sp" {
  name     = "main"
  location = "westeurope"
  type     = "azurerm_app_service_plan"
}

resource "azurerm_service_plan" "main" {
  name                = data.namep_azure_name.sp.result
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = "EP1"
}

data "namep_azure_name" "fun" {
  name     = "main"
  location = "westeurope"
  type     = "azurerm_function_app"
}

resource "azurerm_linux_function_app" "main" {
  name                = data.namep_azure_name.fun.result
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key
  service_plan_id            = azurerm_service_plan.main.id

  site_config {
    application_insights_connection_string  = azurerm_application_insights.main.connection_string
    application_insights_key                = azurerm_application_insights.main.instrumentation_key
    container_registry_use_managed_identity = true
    application_stack {
      docker {
        registry_url = "https://index.docker.io/v1"
        image_name   = "jason0077/medical-search"
        image_tag    = "latest"
      }
    }

    app_service_logs {
      disk_quota_mb         = 35
      retention_period_days = 5
    }

  }

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "COSMOS_CONNECTION_STRING"            = azurerm_cosmosdb_account.main.primary_mongodb_connection_string
    "COSMOS_DATABASE_NAME"                = azurerm_cosmosdb_mongo_database.main.name
    "COSMOS_CONTAINER_NAME"               = azurerm_cosmosdb_mongo_collection.main.name
  }

  identity {
    type = "SystemAssigned"
  }
}

resource "azurerm_role_assignment" "fun2acr" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}