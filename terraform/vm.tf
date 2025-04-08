resource "azurerm_public_ip" "web_vm_publicip" {
  name                = "${local.resource_name_prefix}-web-vm-publicip-${random_string.myrandom.id}"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = "app1-vm-${random_string.myrandom.id}"
}

resource "azurerm_network_interface" "web_vm_nic" {
  name                = "${local.resource_name_prefix}-web-vm-nic-${random_string.myrandom.id}"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  ip_configuration {
    name                          = "web-vm-ip-1"
    subnet_id                     = azurerm_subnet.websubnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.web_vm_publicip.id
  }
}

resource "azurerm_linux_virtual_machine" "web_vm" {
  name = "${local.resource_name_prefix}-web-vm-${random_string.myrandom.id}"
  #computer_name = "web-vm" # Hostname of the VM (Optional)
  resource_group_name   = azurerm_resource_group.rg.name
  location              = azurerm_resource_group.rg.location
  size                  = "Standard_B2ms"
  admin_username        = "azureuser"
  network_interface_ids = [azurerm_network_interface.web_vm_nic.id]
  custom_data = base64encode(file("${path.module}/init_script.sh"))
  admin_ssh_key {
    username   = "azureuser"
    public_key = file("${path.module}/ssh-keys/terraform-azure.pub")
  }
  os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
  }
  source_image_reference {
    publisher = "canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }
}