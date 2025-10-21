# AI Trend Monitor - Streamlit Dashboard

Interactive web dashboard for exploring AI news trends with advanced analytics and RAG-powered chatbot.

## Features

- **News Page**: Search and browse AI articles with filters (source, sentiment, date)
- **Analytics Page**: 
  - Topic Trend Timeline with dual-axis visualization
  - Net Sentiment Distribution histogram
  - Source statistics with growth metrics
  - Word cloud and top topics analysis
- **Chatbot Page**: RAG-powered conversational AI using GPT-4.1-mini via GitHub Models
- **About Page**: Project information and technology stack

## Local Development

### Prerequisites

- Python 3.12+
- Azure AI Search service with indexed articles
- GitHub Personal Access Token (for chatbot)

### Setup

1. **Activate conda environment**:
```bash
conda activate trend-monitor
```

2. **Install dependencies**:
```bash
pip install -r ../requirements.txt
```

3. **Configure environment variables**:

Create `.env` file in project root:
```bash
SEARCH_ENDPOINT=https://your-search-service.search.windows.net/
SEARCH_KEY=your_search_admin_key
GITHUB_TOKEN=ghp_your_github_token
```

Or create `.streamlit/secrets.toml` in this directory:
```toml
SEARCH_ENDPOINT = "https://your-search-service.search.windows.net/"
SEARCH_KEY = "your_search_admin_key"
GITHUB_TOKEN = "ghp_your_github_token"
```

4. **Run the dashboard**:
```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Azure Deployment

### Quick Deploy Summary

1. Create Azure App Service (Python 3.12)
2. Configure environment variables in Application Settings
3. Set startup command: `streamlit run streamlit_app/app.py --server.port=8000 --server.address=0.0.0.0`
4. Deploy from GitHub repository

### Required Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SEARCH_ENDPOINT` | Azure AI Search service endpoint | Yes |
| `SEARCH_KEY` | Azure AI Search admin key | Yes |
| `GITHUB_TOKEN` | GitHub Personal Access Token for GPT-4.1-mini | Yes (for chatbot) |

## Configuration

### Theme Customization

Edit `.streamlit/config.toml` to customize colors, fonts, and server settings.

Current theme: **AITREND_COLOURS** - Warm beiges and dark greys with color-blind accessible sentiment colors.

## Project Structure

```
streamlit_app/
├── app.py                      # Main Streamlit application
├── .streamlit/
│   ├── config.toml             # Theme and server configuration
│   └── secrets.toml.example    # Example secrets file
└── README.md                   # This file
```

## Troubleshooting

### "Azure Search credentials not found"
- Ensure `.env` file exists in project root with correct variables
- Or check `.streamlit/secrets.toml` exists in this directory

### "GITHUB_TOKEN not found"
- Create token at: https://github.com/settings/tokens
- Add to `.env` or secrets.toml

### Dashboard loads slowly
- Clear cache: Top-right menu → "Clear cache"
- Upgrade Azure Search tier for better performance
