variable "db_administrator_login" {
  description = "Database administrator login"
  type        = string
  sensitive   = true
}

variable "db_administrator_password" {
  description = "Database administrator password"
  type        = string
  sensitive   = true
}

# Run terrafrom apply with -var="db_administrator_login=XXX" -var="db_administrator_password=XXX"
# or add Environment Variables with TF_VAR_ prefix
# export TF_VAR_db_administrator_login=XXX
# export TF_VAR_db_administrator_password=XXX

locals {
  db_administrator_login = var.db_administrator_login
  db_administrator_password = var.db_administrator_password
}

# reference: https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/postgresql_flexible_server
resource "azurerm_postgresql_flexible_server" "db" {
  name                          = "${local.resource_name_prefix}-db-${random_string.myrandom.id}"
  resource_group_name           = azurerm_resource_group.rg.name
  location                      = azurerm_resource_group.rg.location
  version                       = "16"
  public_network_access_enabled = true
  administrator_login           = local.db_administrator_login
  administrator_password        = local.db_administrator_password
  zone                          = "1"

  storage_mb   = 32768
  storage_tier = "P4"

  sku_name = "B_Standard_B1ms" #tier + name pattern
}

resource "azurerm_postgresql_flexible_server_database" "appdb" {
  name      = "appdb"
  server_id = azurerm_postgresql_flexible_server.db.id
  collation = "en_US.utf8"
  charset   = "utf8"
}

resource "azurerm_postgresql_flexible_server_firewall_rule" "rule" {
  name             = "all-traffic"
  server_id        = azurerm_postgresql_flexible_server.db.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

output "db_server_name" {
  description = "DB Server Name"
  value       = azurerm_postgresql_flexible_server.db.fqdn
}