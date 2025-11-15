# deploy.ps1 — Run in PowerShell

Write-Host "Deploying DocuBot to Azure..." -ForegroundColor Green

# 1. Create resource group
az group create --name docubot-rg --location eastus2 --output none

# 2. Deploy app
az webapp up `
  --name docubot2-app `
  --resource-group docubot-rg `
  --runtime "PYTHON:3.11" `
  --sku B1

Write-Host "LIVE AT: https://docubot2-app.azurewebsites.net" -ForegroundColor Green
Write-Host "Logs: az webapp log tail --name docubot2-app --resource-group docubot-rg" -ForegroundColor Yellow
