data "namep_azure_name" "di" {
  name     = "di-mvp"
  location = var.location
  type     = "azurerm_cognitive_account"
}

resource "azurerm_cognitive_account" "di" {
  name                          = data.namep_azure_name.di.result
  location                      = azurerm_resource_group.main.location
  resource_group_name           = azurerm_resource_group.main.name
  kind                          = "FormRecognizer"
  custom_subdomain_name         = data.namep_azure_name.di.result
  public_network_access_enabled = true

  sku_name = "S0"

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = "Allow"
    ip_rules       = []
  }
}

data "namep_azure_name" "oai" {
  name     = "openai"
  location = var.location
  type     = "azurerm_cognitive_account"
}

resource "azurerm_cognitive_account" "openai" {
  name                          = data.namep_azure_name.oai.result
  location                      = "swedencentral"
  resource_group_name           = azurerm_resource_group.main.name
  kind                          = "OpenAI"
  custom_subdomain_name         = data.namep_azure_name.oai.result
  public_network_access_enabled = true

  sku_name = "S0"

  identity {
    type = "SystemAssigned"
  }

  network_acls {
    default_action = "Allow"
    ip_rules       = []
  }
}

resource "azurerm_cognitive_deployment" "main" {
  for_each             = { for model in var.openai_embedding_models : model.name => model }
  name                 = each.key
  cognitive_account_id = azurerm_cognitive_account.openai.id
  model {
    format  = "OpenAI"
    name    = each.key
    version = each.value.version
  }

  sku {
    name     = "Standard"
    capacity = each.value.capacity
  }
}
