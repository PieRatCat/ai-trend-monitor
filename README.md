# AI Trend Monitor

**An intelligent news aggregation and analysis platform for AI trends**

[![Python](https://img.shields.io/badge/Python-3.12.11-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red.svg)](https://streamlit.io/)
[![Azure](https://img.shields.io/badge/Azure-Cloud-0078D4.svg)](https://azure.microsoft.com/)

**Status**: Production Ready (5 of 6 phases complete)  
**Last Updated**: October 21, 2025

---

## Overview

AI Trend Monitor is a comprehensive news intelligence platform that automatically collects, analyzes, and visualizes AI-related news from multiple trusted sources. Built with Azure cloud services and powered by advanced NLP, it provides real-time insights into AI industry trends, sentiment patterns, and emerging topics through an interactive web dashboard and conversational AI interface.

## Core Features

### 📰 Automated Data Collection
- **Multi-source aggregation**: Guardian API + 4 RSS feeds (TechCrunch, VentureBeat, Ars Technica, Gizmodo)
- **Smart deduplication**: URL-based tracking prevents redundant processing
- **Intelligent scraping**: Site-specific content extraction with fallback strategies
- **Date filtering**: Focused on recent trends (June 2025 onwards)

### 🧠 Advanced NLP Analysis
- **Sentiment analysis**: Positive, negative, neutral, and mixed sentiment classification with confidence scores
- **Entity recognition**: Organizations, people, products, and technologies mentioned
- **Key phrase extraction**: Automatic topic and theme identification
- **Powered by**: Azure AI Language with batched processing for efficiency

### 🔍 Semantic Search
- **Indexed knowledge base**: 200+ articles searchable by keywords, entities, and phrases
- **Multi-filter search**: Filter by source, sentiment, date range, and topics
- **Fast retrieval**: Azure AI Search with keyword matching and ranking

### 📊 Interactive Analytics Dashboard
Built with Streamlit, fully responsive across all devices:

**News Page**
- Curated recent developments and upcoming events
- Article cards with sentiment indicators and key topics
- Advanced search with multiple filters

**Analytics Page**
- **Topic Trend Timeline**: Interactive entity selection with temporal analysis
- **Sentiment Distribution**: Histogram showing overall article sentiment spectrum
- **Source Statistics**: Article count and sentiment breakdown by publication
- **Word Cloud**: Visual representation of most-mentioned entities
- **Top Topics**: Ranked list of trending themes

**Chat Page** (RAG-Powered AI Assistant)
- Natural language queries about AI trends
- Grounded responses with article citations
- Conversation history and context awareness
- Powered by GPT-4.1-mini via GitHub Models

**About Page**
- Project information and technology stack

### 🎨 Professional Design
- Custom color palette (warm beiges, teal, orange)
- Responsive design (desktop, laptop, tablet, mobile)
- Accessibility-focused (color-blind safe, high contrast)

### 🔮 Coming Soon
- **Automated Weekly Reports**: AI-generated trend summaries and insights delivered via email

## Technology Stack

**Cloud Infrastructure**
- Azure Blob Storage (data persistence)
- Azure AI Language (NLP analysis)
- Azure AI Search (semantic search index)

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
- Custom responsive CSS

## Quick Start

### Prerequisites
- Python 3.12.11
- Conda environment manager
- Azure account (Blob Storage, AI Language, AI Search)
- GitHub Personal Access Token (for chatbot)

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
   GUARDIAN_API_KEY=your_guardian_api_key
   AZURE_STORAGE_CONNECTION_STRING=your_connection_string
   LANGUAGE_KEY=your_azure_language_key
   LANGUAGE_ENDPOINT=your_azure_language_endpoint
   SEARCH_ENDPOINT=your_azure_search_endpoint
   SEARCH_KEY=your_azure_search_key
   GITHUB_TOKEN=your_github_personal_access_token
   ```

### Usage

**Run the data pipeline** (collect and analyze articles):
```bash
conda activate trend-monitor
python run_pipeline.py
```

**Launch the dashboard**:
```bash
conda activate trend-monitor
streamlit run streamlit_app/app.py
```

Then open your browser to `http://localhost:8501`

## Project Structure

```
ai-trend-monitor/
├── config/                  # Data source configurations
│   ├── api_sources.py      # Guardian API settings
│   ├── rss_sources.py      # RSS feed URLs
│   └── query.py            # Search query terms
├── src/                     # Core pipeline modules
│   ├── api_fetcher.py      # Guardian API integration
│   ├── rss_fetcher.py      # RSS feed parsing
│   ├── scrapers.py         # Web scraping with fallbacks
│   ├── data_cleaner.py     # HTML processing
│   ├── language_analyzer.py # Azure AI Language integration
│   ├── storage.py          # Azure Blob Storage operations
│   ├── search_indexer.py   # Azure AI Search indexing
│   └── rag_chatbot.py      # RAG conversational AI
├── streamlit_app/          # Web dashboard
│   ├── .streamlit/         # Streamlit configuration
│   │   └── config.toml     # Theme and server settings
│   ├── app.py              # Main dashboard application
│   └── styles.css          # Responsive design styles
├── run_pipeline.py         # Main orchestration script
└── requirements.txt        # Python dependencies
```

## Documentation

Comprehensive project documentation available in: (coming soon)


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

## Acknowledgments

- Azure AI Services for NLP capabilities
- OpenAI for GPT-4.1-mini model access via GitHub Models
- GitHub Copilot for AI-assisted development and code optimization
- The Guardian, TechCrunch, VentureBeat, Ars Technica, and Gizmodo for news content
- Streamlit for rapid dashboard development

---
