resource "azurerm_storage_account" "sa" {
  name                     = "${local.resource_name_prefix}appstorage${random_string.myrandom.id}"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"

  tags = local.common_tags
}

resource "azurerm_storage_container" "sc" {
  name                  = "${local.resource_name_prefix}-container"
  storage_account_id    = azurerm_storage_account.sa.id
  container_access_type = "private"
}