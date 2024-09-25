terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.3.1"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.51.0"
    }
    namep = {
      source  = "jason-johnson/namep"
      version = "~> 1.1"
    }
  }
}