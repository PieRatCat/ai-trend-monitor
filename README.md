# AI Trend Monitor

**An intelligent news aggregation and analysis platform for AI trends**

[![Python](https://img.shields.io/badge/Python-3.12.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Azure](https://img.shields.io/badge/Azure-Cloud-0078D4.svg)](https://azure.microsoft.com/)
[![Live Demo](https://img.shields.io/badge/Live-Demo-success.svg)](https://trends.goblinsen.se/)

**Status**: ✅ Production Deployed - All Features Complete  
**Live Demo**: [https://trends.goblinsen.se/](https://trends.goblinsen.se/)  
**Last Updated**: October 28, 2025

---

## Overview

AI Trend Monitor is a comprehensive news intelligence platform that automatically collects, analyzes, and visualizes AI-related news from multiple trusted sources. Built with Azure cloud services and powered by advanced NLP, it provides real-time insights into AI industry trends, sentiment patterns, and emerging topics through an interactive web dashboard, conversational AI interface, and automated weekly email newsletters.

**[Try the Live Dashboard →](https://trends.goblinsen.se/)**

## Core Features

### Automated Data Collection
- **Multi-source aggregation**: API + RSS feeds
- **Smart deduplication**: URL-based tracking prevents redundant processing
- **Intelligent scraping**: Site-specific content extraction with fallback strategies
- **Date filtering**: Focused on recent trends (June 2025 onwards)

### Advanced NLP Analysis
- **Sentiment analysis**: Positive, negative, neutral, and mixed sentiment classification with confidence scores
- **Entity recognition**: Organizations, people, products, and technologies mentioned
- **Key phrase extraction**: Automatic topic and theme identification
- **Powered by**: Azure AI Language with batched processing for efficiency

### Semantic Search
- **Indexed knowledge base**: 500+ articles searchable by keywords, entities, and phrases
- **Multi-filter search**: Filter by source, sentiment, date range, and topics
- **Fast retrieval**: Azure AI Search with keyword matching and ranking
- **Date-filtered**: Focused on June 2025 onwards for relevant trends

### Interactive Analytics Dashboard
Built with Streamlit, fully responsive across all devices:

**News Page**
- Curated news summaries
- Article cards with sentiment indicators and key topics
- Advanced search with multiple filters

**Analytics Page**
- **Topic Trend Timeline**: Interactive entity selection with temporal analysis
- **Sentiment Distribution**: Histogram showing overall article sentiment spectrum
- **Source Statistics**: Article count and sentiment breakdown by publication
- **Top Topics**: Ranked list of trending themes
- **Word Cloud**: Visual representation of most-mentioned entities


**Chat Page** (RAG-Powered AI Assistant)
- Natural language queries about AI trends
- Grounded responses with article citations
- Temporal query detection ("last 24 hours", "past week", etc.)
- Conversation history and context awareness
- Powered by GPT-4.1-mini via GitHub Models

**Subscribe Page**
- Email newsletter subscription with double opt-in
- GDPR-compliant subscriber management
- Unsubscribe links in all emails
- Azure Table Storage for secure data handling

**About Page**
- Project information and technology stack
- Development journey and phase completion

### Professional Design
- Custom color palette (warm beiges, teal, orange)
- Responsive design (desktop, laptop, tablet, mobile)
- Accessibility-focused (color-blind safe, high contrast)
- CSS externalized for maintainability

### Automated Weekly Newsletter
- **AI-generated reports**: GPT-4.1-mini creates comprehensive weekly summaries from 200+ analyzed articles
- **Three-section format**:
  - Executive Summary (150-200 word narrative of key developments)
  - Models and Research (3-4 paragraphs on LLM updates and technical breakthroughs)
  - Tools and Platforms (2-3 paragraphs on developer tools, APIs, and integrations)
- **GPT-based entity extraction**: Automatically identifies 24+ companies, products, and technologies mentioned
- **Interactive entity links**: 45+ clickable links to dashboard search (e.g., OpenAI, ChatGPT, Anthropic, GPT-4)
- **Dashboard integration**: Links open `trends.goblinsen.se` with pre-populated search and auto-results
- **Scheduled delivery**: Every Friday at 9:00 AM UTC via Azure Functions
- **HTML email template**: Mobile-responsive with styled links and unsubscribe functionality
- **Azure Communication Services**: Reliable email delivery with GDPR compliance
- **[View sample newsletter →](https://htmlpreview.github.io/?https://github.com/PieRatCat/ai-trend-monitor/blob/main/sample-newsletter-2025-10-28.html)**

## Technology Stack

**Cloud Infrastructure**
- Azure Blob Storage (data persistence)
- Azure AI Language (NLP analysis)
- Azure AI Search (semantic search index)
- Azure Communication Services (email delivery)
- Azure Table Storage (subscriber management)
- Azure Functions (automated scheduling)
- Azure App Service (web hosting)

**Backend**
- Python 3.12.11
- Beautiful Soup (web scraping)
- Feedparser (RSS parsing)

**AI & ML**
- OpenAI GPT-4.1-mini (conversational AI)
- GitHub Models (development)
- Azure AI Language (sentiment, entities, key phrases)

**Frontend**
- Streamlit (web dashboard)
- Plotly & Matplotlib (data visualization)
- Custom responsive CSS (externalized styling)

## Live Demo

**Access the dashboard**: [https://trends.goblinsen.se/](https://trends.goblinsen.se/)

**Features you can try**:
- **News**: Browse 500+ analyzed AI articles with sentiment indicators
- **Analytics**: Explore interactive visualizations of AI trends and sentiment patterns
- **Chat**: Ask the AI assistant questions like "What are the latest AI models?" or "Show me articles from last week about ChatGPT"
- **Subscribe**: Sign up for weekly AI trend digest emails (GDPR compliant)

## Quick Start

### For Local Development

#### Prerequisites
- Python 3.12.11
- Conda environment manager
- Azure account (Blob Storage, AI Language, AI Search, Communication Services)
- GitHub Personal Access Token (for chatbot)
- Guardian API Key (optional, for news fetching)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/PieRatCat/ai-trend-monitor.git
   cd ai-trend-monitor
   ```

2. **Set up conda environment**
   ```bash
   conda create -n trend-monitor python=3.12.11
   conda activate trend-monitor
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   
   Create `.env` file:
   ```
   # Data Collection
   GUARDIAN_API_KEY=your_guardian_api_key
   
   # Azure Storage & AI Services
   AZURE_STORAGE_CONNECTION_STRING=your_connection_string
   LANGUAGE_KEY=your_azure_language_key
   LANGUAGE_ENDPOINT=your_azure_language_endpoint
   SEARCH_ENDPOINT=your_azure_search_endpoint
   SEARCH_KEY=your_azure_search_key
   
   # AI Chatbot
   GITHUB_TOKEN=your_github_personal_access_token
   
   # Email Newsletter (optional for local development)
   AZURE_COMMUNICATION_CONNECTION_STRING=your_communication_connection_string
   EMAIL_SENDER=DoNotReply@yourdomain.com
   EMAIL_RECIPIENT=your_test_email@example.com
   STREAMLIT_APP_URL=http://localhost:8501
   ```

### Usage

**Run the data pipeline** (collect and analyze articles):
```bash
conda activate trend-monitor
python run_pipeline.py
```

**Launch the dashboard locally**:
```bash
conda activate trend-monitor
streamlit run streamlit_app/app.py
```

Then open your browser to `http://localhost:8501`

**Or visit the live production site**: [https://trends.goblinsen.se/](https://trends.goblinsen.se/)

## Project Structure

```
ai-trend-monitor/
├── config/                  # Data source configurations
│   ├── api_sources.py      # Guardian API settings
│   ├── rss_sources.py      # RSS feed URLs (7 sources)
│   └── query.py            # Search query terms
├── src/                     # Core pipeline modules
│   ├── api_fetcher.py      # Guardian API integration
│   ├── rss_fetcher.py      # RSS feed parsing
│   ├── scrapers.py         # Web scraping with fallbacks
│   ├── data_cleaner.py     # HTML processing
│   ├── language_analyzer.py # Azure AI Language integration
│   ├── storage.py          # Azure Blob Storage operations
│   ├── search_indexer.py   # Azure AI Search indexing
│   ├── rag_chatbot.py      # RAG conversational AI
│   ├── generate_weekly_report.py  # GPT-4.1-mini report generator
│   ├── confirmation_email.py      # Double opt-in email system
│   └── subscriber_manager.py      # Azure Table Storage subscribers
├── streamlit_app/          # Web dashboard
│   ├── .streamlit/         # Streamlit configuration
│   │   └── config.toml     # Theme and server settings
│   ├── app.py              # Main dashboard (News, Analytics, Chat, Subscribe, About)
│   └── styles.css          # Responsive design styles (350 lines)
├── function_app.py         # Azure Functions timer trigger
├── host.json               # Azure Functions configuration
├── run_pipeline.py         # Main orchestration script
├── run_weekly_pipeline.py  # Weekly newsletter pipeline
└── requirements.txt        # Python dependencies
```

## Documentation

Comprehensive project report available in:
- **Project Report**: [`PROJECT_REPORT.ipynb`](./PROJECT_REPORT.ipynb) - Complete technical documentation, architecture overview, and development insights


## Architecture Highlights

**Data Pipeline**
- Fetch → Deduplicate → Scrape → Clean → Analyze → Store → Index
- Automated URL registry prevents redundant processing
- Batched NLP analysis (25 documents at a time)
- Compact JSON storage (30-40% space savings)

**RAG Chatbot**
- Retrieval-Augmented Generation for grounded responses
- Temporal query detection with smart date filtering
- Token budget management (prevents API errors)
- Context-aware conversation history

**Cost Optimization**
- Early deduplication saves ~2 minutes per run
- Content filtering prevents wasted API calls
- Free tier Azure AI Search (sufficient for 10,000+ articles)
- Standard tier Azure AI Language (pay-per-use, optimized batching)

## License

This project is available for educational and demonstration purposes.

## Author

**Amanda Sumner**  
[GitHub](https://github.com/PieRatCat) | [Project Repository](https://github.com/PieRatCat/ai-trend-monitor)

---
