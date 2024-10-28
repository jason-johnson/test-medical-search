terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.7.0"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 2.53.0"
    }
    namep = {
      source  = "jason-johnson/namep"
      version = "~> 1.1"
    }
  }
}