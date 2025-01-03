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

resource "azurerm_storage_container" "images" {
  name                  = "journal-images"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
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
        registry_url = "https://index.docker.io"
        image_name   = "jason0077/medical-search"
        image_tag    = "latest"
      }
    }

    app_service_logs {
      disk_quota_mb         = 35
      retention_period_days = 5
    }

  }

  ftp_publish_basic_authentication_enabled       = false
  webdeploy_publish_basic_authentication_enabled = false

  app_settings = {
    "WEBSITES_ENABLE_APP_SERVICE_STORAGE" = "false"
    "COSMOS_CONNECTION_STRING"            = azurerm_cosmosdb_account.main.primary_mongodb_connection_string
    "COSMOS_DATABASE_NAME"                = azurerm_cosmosdb_mongo_database.main.name
    "COSMOS_COLLECTION_NAME"              = azurerm_cosmosdb_mongo_collection.main.name
    "AZURE_FORM_RECOGNIZER_ENDPOINT"      = azurerm_cognitive_account.di.endpoint
    "AZURE_FORM_RECOGNIZER_KEY"           = azurerm_cognitive_account.di.primary_access_key
    "OPENAI_API_KEY"                      = azurerm_cognitive_account.openai.primary_access_key
    "OPENAI_AZURE_ENDPOINT"               = azurerm_cognitive_account.openai.endpoint
    "OPENAI_API_VERSION"                  = "2024-08-01-preview"
    "OPENAI_DEPLOYMENT_NAME"              = azurerm_cognitive_deployment.main["gpt-4"].model[0].name
    "AZURE_STORAGE_ACCOUNT_URL"           = azurerm_storage_account.main.primary_blob_endpoint
    "AZURE_STORAGE_CONTAINER_NAME"        = azurerm_storage_container.images.name
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

resource "azurerm_role_assignment" "sa_admin_blob_contrib" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}