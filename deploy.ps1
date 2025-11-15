# deploy.ps1 — FIXED VERSION (With Restart + Logs)

Write-Host "Logging in to Azure..." -ForegroundColor Yellow
az login  # If needed

Write-Host "Cleaning previous deploy..." -ForegroundColor Yellow
az webapp delete --name docubot2-app --resource-group docubot-rg --yes  # Delete old app

Write-Host "Creating fresh app..." -ForegroundColor Yellow
az webapp create `
  --name docubot2-app `
  --resource-group docubot-rg `
  --plan docubot-plan `
  --sku B1 `
  --runtime "PYTHON|3.11"

Write-Host "Deploying files..." -ForegroundColor Yellow
az webapp up `
  --name docubot2-app `
  --resource-group docubot-rg

Write-Host "Setting startup command..." -ForegroundColor Yellow
az webapp config appsettings set `
  --resource-group docubot-rg `
  --name docubot2-app `
  --settings STARTUP_COMMAND="bash run.sh"

Write-Host "Restarting app..." -ForegroundColor Yellow
az webapp restart --name docubot2-app --resource-group docubot-rg

Write-Host "LIVE AT: https://docubot2-app.azurewebsites.net" -ForegroundColor Green
Write-Host "Tail logs: az webapp log tail --name docubot2-app --resource-group docubot-rg" -ForegroundColor Cyan