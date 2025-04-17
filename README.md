# Stage 7 - Manual Deployment

Based on the architecture of stage 6, we add 5 new resources to the infrastructure:

- Azure Function App
- Azure Application Insights
- Azure App Service Plan
- Azuer Storage Account
- Azure Key Vault

## Backend

Make sure you have added the necessary environment variables to the Azure Function App settings and Azure Key Vault.

The code of Azure Function App should be in a separate GitHub repository because it would be easier to manage the CI/CD pipeline.

Add the system-assigned managed identity of the Azure Function App to the Key Vault access policy with get and list permissions for secrets.


## CI/CD

After developing the Azure Function App code, we need to deploy it using GitHub Actions. Go to the Azure console of the function app, under Deployment, click on Deployment Center, and select GitHub as the source control. Follow the steps to authorize GitHub and select the repository and branch to deploy.

It creates a new GitHub Actions workflow file in the `.github/workflows` directory. The workflow might not work as expected, so we have to debug it. A common issue is the `module not found` error. To fix this, we need to add `--target=".python_packages/lib/site-packages"` to the `pip install` command in the GitHub Actions workflow file. Don't forget to add it to the zip command as well.

```yaml
# Docs for the Azure Web Apps Deploy action: https://github.com/azure/functions-action
# More GitHub Actions for Azure: https://github.com/Azure/actions
# More info on Python, GitHub Actions, and Azure Functions: https://aka.ms/python-webapps-actions

name: Build and deploy Python project to Azure Function App - backend-service-2025

on:
  push:
    branches:
      - stage-7-af
  workflow_dispatch:

env:
  AZURE_FUNCTIONAPP_PACKAGE_PATH: '.' # set this to the path to your web app project, defaults to the repository root
  PYTHON_VERSION: '3.9' # set this to the python version to use (supports 3.6, 3.7, 3.8)

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: read #This is required for actions/checkout

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python version
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}

      - name: Create and start virtual environment
        run: |
          python -m venv venv
          source venv/bin/activate

      - name: Install dependencies
        run: pip install -r requirements.txt --target=".python_packages/lib/site-packages"

      # Optional: Add step to run tests here

      - name: Zip artifact for deployment
        run: zip -r release.zip ./* .python_packages/*

      - name: Upload artifact for deployment job
        uses: actions/upload-artifact@v4
        with:
          name: python-app
          path: |
            release.zip


  deploy:
    runs-on: ubuntu-latest
    needs: build
    permissions:
      id-token: write #This is required for requesting the JWT
      contents: read #This is required for actions/checkout

    steps:
      - name: Download artifact from build job
        uses: actions/download-artifact@v4
        with:
          name: python-app

      - name: Unzip artifact for deployment
        run: unzip release.zip     
        
      - name: Login to Azure
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZUREAPPSERVICE_CLIENTID_F4CEAB06A1554B2FB0AC95869EFBC883 }}
          tenant-id: ${{ secrets.AZUREAPPSERVICE_TENANTID_BF32BF4BCFDB4F99AE0608CEA3D5DD88 }}
          subscription-id: ${{ secrets.AZUREAPPSERVICE_SUBSCRIPTIONID_39722340F2C249749B97A7EEA13E8EC1 }}

      - name: Set Application Settings
        run: |
          az functionapp config appsettings set --name backend-service-2025 --resource-group DemoVmSDA --settings "FUNCTIONS_WORKER_RUNTIME=python" "KEY_VAULT_NAME=sdakeyvault2025" "APPINSIGHTS_INSTRUMENTATIONKEY=azurerm_application_insights.ai.instrumentation_key"

      - name: 'Deploy to Azure Functions'
        uses: Azure/functions-action@v1
        id: deploy-to-function
        with:
          app-name: 'backend-service-2025'
          slot-name: 'Production'
          package: ${{ env.AZURE_FUNCTIONAPP_PACKAGE_PATH }}
          scm-do-build-during-deployment: true
          enable-oryx-build: true
```

## Frontend

After setting up the Azure Function App, we need to update the frontend to call the new function.

Create a new VM in a separate resource group. In the VM, set up the Conda Python environment, set up the frontend and chromadb and test the application. Add the system-assigned managed identity of the VM to the Key Vault access policy with get and list permissions for secrets. If everything works, create a new image from the VM and delete the VM.

Use the new image to create a VM in your main resource group. Don't forget to add the system-assigned managed identity of the VM to the Key Vault access policy too


```
