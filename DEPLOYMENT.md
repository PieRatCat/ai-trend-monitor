# Azure Deployment Guide - AI Trend Monitor
Not for publishing 
This guide covers deploying the AI Trend Monitor Streamlit dashboard to Azure App Service.

## Prerequisites

1. **Azure Account** with active subscription
2. **Azure CLI** installed ([Download here](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli))
3. **Git** repository with your code
4. **Environment variables** configured (see below)

## Required Azure Resources

Before deployment, ensure you have:

- ✅ **Azure Storage Account** (for article data)
- ✅ **Azure AI Language** service (for NLP analysis)
- ✅ **Azure AI Search** service (for article indexing)
- ✅ **GitHub Personal Access Token** (for GPT-4.1-mini via GitHub Models)

## Environment Variables

The Streamlit app requires these environment variables:

```bash
SEARCH_ENDPOINT=https://your-search-service.search.windows.net/
SEARCH_KEY=your_search_admin_key_here
GITHUB_TOKEN=ghp_your_github_personal_access_token_here
```

**Important**: The dashboard only needs these 3 variables. The data pipeline uses additional variables (Guardian API, Storage, Language) but those run separately.

## Deployment Options

### Option 1: Azure App Service (Recommended)

**Step 1: Login to Azure**
```bash
az login
az account set --subscription "your-subscription-id"
```

**Step 2: Create Resource Group (if needed)**
```bash
az group create --name ai-trend-monitor-rg --location eastus
```

**Step 3: Create App Service Plan**
```bash
# Free tier for testing
az appservice plan create \
  --name ai-trend-monitor-plan \
  --resource-group ai-trend-monitor-rg \
  --sku F1 \
  --is-linux

# Or production tier (B1 recommended minimum)
az appservice plan create \
  --name ai-trend-monitor-plan \
  --resource-group ai-trend-monitor-rg \
  --sku B1 \
  --is-linux
```

**Step 4: Create Web App**
```bash
az webapp create \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --plan ai-trend-monitor-plan \
  --runtime "PYTHON:3.12"
```

**Step 5: Configure Environment Variables**
```bash
az webapp config appsettings set \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --settings \
    SEARCH_ENDPOINT="https://your-search-service.search.windows.net/" \
    SEARCH_KEY="your_search_key" \
    GITHUB_TOKEN="ghp_your_token"
```

**Step 6: Configure Deployment**
```bash
# Configure GitHub deployment (recommended)
az webapp deployment source config \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --repo-url https://github.com/PieRatCat/ai-trend-monitor \
  --branch main \
  --manual-integration
```

**Step 7: Configure Startup Command**

In Azure Portal:
1. Go to your App Service
2. Configuration → General settings
3. Set **Startup Command**: `streamlit run streamlit_app/app.py --server.port=8000 --server.address=0.0.0.0`

**Step 8: Deploy**

Push your code to GitHub, then trigger deployment:
```bash
az webapp deployment source sync \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg
```

### Option 2: Azure Container Instances

**Step 1: Create Dockerfile** (in project root)
```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

**Step 2: Build and Push to Azure Container Registry**
```bash
# Create ACR
az acr create --resource-group ai-trend-monitor-rg \
  --name aitrendmonitoracr --sku Basic

# Build and push
az acr build --registry aitrendmonitoracr \
  --image ai-trend-monitor:latest .
```

**Step 3: Deploy Container**
```bash
az container create \
  --resource-group ai-trend-monitor-rg \
  --name ai-trend-monitor-container \
  --image aitrendmonitoracr.azurecr.io/ai-trend-monitor:latest \
  --dns-name-label ai-trend-monitor \
  --ports 8501 \
  --environment-variables \
    SEARCH_ENDPOINT="https://..." \
    SEARCH_KEY="..." \
    GITHUB_TOKEN="..."
```

## Post-Deployment

### Verify Deployment

1. **Check Application Logs**:
```bash
az webapp log tail --name ai-trend-monitor-app --resource-group ai-trend-monitor-rg
```

2. **Test Endpoints**:
   - Health check: `https://your-app.azurewebsites.net/_stcore/health`
   - Dashboard: `https://your-app.azurewebsites.net`

3. **Monitor Performance**:
   - Azure Portal → App Service → Monitoring → Metrics

### Configure Custom Domain (Optional)

```bash
# Add custom domain
az webapp config hostname add \
  --webapp-name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --hostname www.yourdomain.com

# Enable HTTPS
az webapp update \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --https-only true
```

## Scaling Considerations

### Recommended Pricing Tiers

- **Development/Testing**: F1 (Free) or D1 (Shared)
- **Production**: B1 (Basic) or P1V2 (Premium) - recommended for 50+ users
- **High Traffic**: P2V2 or P3V2 with auto-scaling

### Auto-Scaling Configuration

```bash
az monitor autoscale create \
  --resource-group ai-trend-monitor-rg \
  --resource ai-trend-monitor-app \
  --resource-type Microsoft.Web/serverfarms \
  --name autoscale-plan \
  --min-count 1 \
  --max-count 3 \
  --count 1
```

## Troubleshooting

### Common Issues

**1. App won't start**
- Check startup command in Configuration
- Verify Python version matches (3.12)
- Review logs: `az webapp log tail`

**2. Environment variables not working**
- Verify variables are set in App Service Configuration (not just secrets.toml)
- Restart app after changing variables

**3. Chatbot not working**
- Check `GITHUB_TOKEN` is valid
- Verify Azure AI Search credentials (`SEARCH_ENDPOINT`, `SEARCH_KEY`)
- Check if GitHub Models API is accessible from Azure

**4. Slow performance**
- Upgrade to B1 or higher tier
- Enable Application Insights for diagnostics
- Check if caching is working (`@st.cache_resource`, `@st.cache_data`)

### Enable Detailed Logging

```bash
# Enable application logging
az webapp log config \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --application-logging filesystem \
  --level verbose
```

## Cost Optimization

1. **Use Free Tier** for development (F1 plan)
2. **Start with B1** for production (£13-18/month)
3. **Enable auto-scaling** only when needed
4. **Monitor usage** with Azure Cost Management
5. **Shutdown dev environments** when not in use

## Security Best Practices

1. ✅ **Never commit secrets** to Git (use `.env.example` template)
2. ✅ **Use Azure Key Vault** for production secrets (optional)
3. ✅ **Enable HTTPS only** (`--https-only true`)
4. ✅ **Restrict network access** with firewall rules (optional)
5. ✅ **Enable managed identity** for Azure resource access (advanced)

## Continuous Deployment

### GitHub Actions Workflow

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]
  workflow_dispatch:

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    
    - name: Deploy to Azure Web App
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'ai-trend-monitor-app'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

**Setup**:
1. Download publish profile from Azure Portal
2. Add as GitHub Secret: `AZURE_WEBAPP_PUBLISH_PROFILE`
3. Push to `main` branch to trigger deployment

## Monitoring & Maintenance

### Application Insights (Recommended)

```bash
# Create Application Insights
az monitor app-insights component create \
  --app ai-trend-monitor-insights \
  --location eastus \
  --resource-group ai-trend-monitor-rg

# Link to Web App
az webapp config appsettings set \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="your-key"
```

### Health Checks

Configure health check endpoint:
```bash
az webapp config set \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --generic-configurations '{"healthCheckPath": "/_stcore/health"}'
```

## Additional Resources

- [Streamlit on Azure Documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud)
- [Azure App Service Python Docs](https://docs.microsoft.com/en-us/azure/app-service/quickstart-python)
- [Azure CLI Reference](https://docs.microsoft.com/en-us/cli/azure/)
- [GitHub Actions for Azure](https://github.com/Azure/actions)

## Support

For issues specific to this project:
- GitHub Issues: https://github.com/PieRatCat/ai-trend-monitor/issues
- Documentation: See `README.md` and `project_summary.ipynb`
