## Public IP Address
output "web_vm_public_ip" {
  description = "Web VM Public Address"
  value       = azurerm_public_ip.web_vm_publicip.ip_address
}

output "web_vm_network_interface_id" {
  description = "Web VM Network Interface ID"
  value       = azurerm_network_interface.web_vm_nic.id
}

output "web_vm_network_interface_private_ip_addresses" {
  description = "Web VM Private IP Addresses"
  value       = [azurerm_network_interface.web_vm_nic.private_ip_addresses]
}

# Linux VM Outputs

output "web_vm_public_ip_address" {
  description = "Web Virtual Machine Public IP"
  value       = azurerm_linux_virtual_machine.web_vm.public_ip_address
}

output "web_vm_private_ip_address" {
  description = "Web Virtual Machine Private IP"
  value       = azurerm_linux_virtual_machine.web_vm.private_ip_address
}

output "web_vm_virtual_machine_id" {
  description = "Web Virtual Machine ID "
  value       = azurerm_linux_virtual_machine.web_vm.id
}



