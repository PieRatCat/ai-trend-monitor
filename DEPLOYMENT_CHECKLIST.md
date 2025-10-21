# Azure Deployment Checklist
Not for publishing 
Use this checklist to ensure your AI Trend Monitor Streamlit dashboard is ready for Azure deployment.

## ✅ Pre-Deployment Checklist

### 1. Code Preparation
- [x] Updated `.gitignore` to allow `.streamlit/config.toml` (but ignore secrets.toml)
- [x] Created `requirements.txt` with all dependencies
- [x] Added `python-dateutil` to requirements (used by app but was missing)
- [x] Removed `ipykernel` comment (dev-only, not needed in production)
- [x] Updated color scheme from `CLAUDE_COLORS` to `AITREND_COLOURS` throughout codebase

### 2. Environment Variables
- [x] Created `.env.example` template for documentation
- [x] Created `.streamlit/secrets.toml.example` template
- [x] Updated `app.py` to support both `.env` and Streamlit secrets
- [x] Updated `rag_chatbot.py` to use consistent environment variable handling
- [x] Added helpful error messages when credentials are missing

### 3. Configuration Files
- [x] `.streamlit/config.toml` - Theme and server settings (ready to push)
- [x] `.streamlit/secrets.toml.example` - Template for secrets
- [x] `.env.example` - Template for environment variables

### 4. Documentation
- [x] Created comprehensive `DEPLOYMENT.md` guide
- [x] Updated `streamlit_app/README.md` with deployment info
- [x] Updated `.streamlit/config.toml` comment (removed Claude reference)

### 5. Security
- [x] `.env` file is git-ignored
- [x] `.streamlit/secrets.toml` is git-ignored
- [x] Example files provided for documentation
- [x] No hardcoded secrets in code

## 📋 Required Environment Variables

The Streamlit dashboard needs these 3 variables:

```bash
SEARCH_ENDPOINT=https://your-search-service.search.windows.net/
SEARCH_KEY=your_search_admin_key_here
GITHUB_TOKEN=ghp_your_github_personal_access_token
```

**Note**: The data pipeline uses additional variables (Guardian API, Storage, Language) but those are NOT needed for the dashboard - they run separately.

## 🚀 Deployment Steps

### Option A: Azure App Service (Recommended)

1. **Push to GitHub**:
```bash
git add .
git commit -m "Prepare for Azure deployment"
git push origin main
```

2. **Create Azure resources**:
```bash
# Login
az login

# Create resource group
az group create --name ai-trend-monitor-rg --location eastus

# Create app service plan (B1 recommended for production)
az appservice plan create \
  --name ai-trend-monitor-plan \
  --resource-group ai-trend-monitor-rg \
  --sku B1 \
  --is-linux

# Create web app
az webapp create \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --plan ai-trend-monitor-plan \
  --runtime "PYTHON:3.12"
```

3. **Configure environment variables**:
```bash
az webapp config appsettings set \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --settings \
    SEARCH_ENDPOINT="https://ai-trends-search.search.windows.net/" \
    SEARCH_KEY="your_key_here" \
    GITHUB_TOKEN="ghp_your_token_here"
```

4. **Set startup command**:

Go to Azure Portal:
- App Service → Configuration → General settings
- Startup Command: `streamlit run streamlit_app/app.py --server.port=8000 --server.address=0.0.0.0`

5. **Configure deployment**:
```bash
az webapp deployment source config \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --repo-url https://github.com/PieRatCat/ai-trend-monitor \
  --branch main \
  --manual-integration

# Trigger initial deployment
az webapp deployment source sync \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg
```

6. **Verify deployment**:
```bash
# Check logs
az webapp log tail --name ai-trend-monitor-app --resource-group ai-trend-monitor-rg

# Open in browser
az webapp browse --name ai-trend-monitor-app --resource-group ai-trend-monitor-rg
```

### Option B: Manual Deployment via ZIP

```bash
# Create deployment package
zip -r deploy.zip . -x "*.git*" "*.env" "*__pycache__*" "utilities/*"

# Deploy
az webapp deployment source config-zip \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --src deploy.zip
```

## 🧪 Post-Deployment Testing

1. **Health Check**:
   - Visit: `https://your-app.azurewebsites.net/_stcore/health`
   - Should return: `ok`

2. **Dashboard Pages**:
   - [ ] News page loads
   - [ ] Search functionality works
   - [ ] Analytics page displays charts
   - [ ] Chatbot page initializes
   - [ ] About page displays

3. **Functionality Tests**:
   - [ ] Search returns results
   - [ ] Filters work (source, sentiment, date)
   - [ ] Charts render correctly
   - [ ] Chatbot responds to queries
   - [ ] Article links are clickable

## 🔧 Troubleshooting

### App won't start
```bash
# Check logs for errors
az webapp log tail --name ai-trend-monitor-app --resource-group ai-trend-monitor-rg

# Common issues:
# - Wrong Python version (should be 3.12)
# - Missing environment variables
# - Incorrect startup command
```

### Environment variables not working
```bash
# Verify they're set
az webapp config appsettings list \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg

# Restart app after changing
az webapp restart \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg
```

### Chatbot fails to initialize
- Check `GITHUB_TOKEN` is valid
- Verify Azure AI Search credentials (`SEARCH_ENDPOINT`, `SEARCH_KEY`)
- Test GitHub Models API accessibility

### Slow performance
- Upgrade to B1 or higher tier
- Enable Application Insights for diagnostics
- Check Azure Search service tier

## 📊 Monitoring

### Enable Application Insights

```bash
# Create Application Insights
az monitor app-insights component create \
  --app ai-trend-monitor-insights \
  --location eastus \
  --resource-group ai-trend-monitor-rg

# Get instrumentation key
INSTRUMENTATION_KEY=$(az monitor app-insights component show \
  --app ai-trend-monitor-insights \
  --resource-group ai-trend-monitor-rg \
  --query instrumentationKey -o tsv)

# Add to app settings
az webapp config appsettings set \
  --name ai-trend-monitor-app \
  --resource-group ai-trend-monitor-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY="$INSTRUMENTATION_KEY"
```

### View Metrics

- Azure Portal → App Service → Monitoring
- Track: Response time, Requests, Errors, CPU, Memory

## 💰 Cost Estimation

### Development
- **F1 (Free)**: $0/month - Good for testing
- Limited to 60 CPU minutes/day

### Production
- **B1 (Basic)**: £13-18/month - Recommended minimum
  - 1 vCPU, 1.75 GB RAM
  - Suitable for 50-100 daily users
  
- **P1V2 (Premium)**: £58-70/month - High traffic
  - 1 vCPU, 3.5 GB RAM
  - Auto-scaling support
  - Better performance for 100+ users

**Total estimated cost**: £15-30/month (B1 App Service + existing Azure resources)

## 🔄 Continuous Deployment

### Option: GitHub Actions

Create `.github/workflows/azure-deploy.yml`:

```yaml
name: Deploy to Azure

on:
  push:
    branches: [ main ]

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
      run: pip install -r requirements.txt
    
    - name: Deploy to Azure
      uses: azure/webapps-deploy@v2
      with:
        app-name: 'ai-trend-monitor-app'
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
```

**Setup**:
1. Download publish profile from Azure Portal
2. Add as GitHub Secret: `AZURE_WEBAPP_PUBLISH_PROFILE`
3. Push to main branch triggers deployment

## ✅ Final Checklist Before Going Live

- [ ] All environment variables configured in Azure
- [ ] Startup command set correctly
- [ ] Application logs enabled
- [ ] Health check endpoint responding
- [ ] All dashboard pages tested
- [ ] Chatbot functionality verified
- [ ] Performance acceptable
- [ ] Custom domain configured (optional)
- [ ] HTTPS enabled
- [ ] Monitoring/Application Insights enabled
- [ ] Budget alerts configured

## 📚 Additional Resources

- [Complete Deployment Guide](./DEPLOYMENT.md)
- [Streamlit App README](./streamlit_app/README.md)
- [Azure App Service Python Docs](https://docs.microsoft.com/en-us/azure/app-service/quickstart-python)
- [Streamlit Deployment Docs](https://docs.streamlit.io/deploy)

## 🆘 Support

For issues:
- Check logs: `az webapp log tail`
- Review [DEPLOYMENT.md](./DEPLOYMENT.md) troubleshooting section
- GitHub Issues: https://github.com/PieRatCat/ai-trend-monitor/issues
