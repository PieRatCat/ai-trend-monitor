# AI Trend Monitor

**Status**: Phase 3 Complete (3 of 6 phases) - Beginning Phase 4  
**Last Updated**: October 15, 2025

---

## Overview

An AI-powered news monitoring system that collects, analyzes, and indexes AI-related articles from multiple sources. The system leverages Azure cloud services for storage, natural language processing, and semantic search capabilities.

## Project Phases

### ✅ Phase 1: Data Pipeline Implementation (COMPLETE)
- Multi-source data ingestion (Guardian API + 4 RSS feeds)
- Azure Blob Storage integration
- Automated content scraping and cleaning

### ✅ Phase 2: Advanced NLP Analysis (COMPLETE)
- Azure AI Language integration
- Sentiment analysis, entity recognition, key phrase extraction
- Batched processing (25 documents at a time)

### ✅ Phase 3: Knowledge Mining (COMPLETE)
- Azure AI Search index with 150 articles
- Automated pipeline integration
- Keyword search operational

### 🚧 Phase 4: Interactive Web Dashboard (IN PROGRESS)
Building Streamlit web application with:
- Search interface with filters (source, sentiment, date range)
- Trend timeline visualization
- Key topics analysis
- Sentiment breakdown charts
- Source distribution analysis
- Hosting on Azure App Service

### 📋 Phase 5: RAG-Powered Chatbot (PLANNED)
- Azure OpenAI Service integration
- Retrieval-Augmented Generation (RAG) pattern
- Natural language queries grounded in knowledge base
- Conversation history and context awareness

### 📋 Phase 6: Automated Weekly Reports (PLANNED)
- Azure Function triggered weekly
- Automated trend analysis and insights
- Report generation with Azure OpenAI
- Distribution via email or web hosting

## System Architecture

**Pipeline Stages**:
1. **Fetch** → Guardian API + RSS feeds (metadata only)
2. **Deduplicate** → Check URLs against registry
3. **Scrape** → Full article content extraction
4. **Clean** → HTML processing and text normalization
5. **Filter** → Remove insufficient content (<100 chars)
6. **Analyze** → Azure AI Language (sentiment, entities, key phrases)
7. **Store** → Save to Azure Blob Storage + Update URL registry
8. **Index** → Upload to Azure AI Search

**Azure Services**:
- **Blob Storage**: Pay-as-you-go (raw-articles, analyzed-articles containers)
- **AI Language**: Standard tier (S) - Pay-per-transaction
- **AI Search**: Free tier (F) - Keyword search, 150 articles indexed

## Key Features

- ✅ Multi-source data collection (5 sources)
- ✅ URL deduplication preventing redundant processing
- ✅ Site-specific web scraping with fallback selectors
- ✅ Azure AI Language NLP analysis
- ✅ Compact blob storage (30-40% space savings)
- ✅ Automated search index synchronization
- ✅ Comprehensive error handling and logging
- ✅ Cost-optimized operations

## Current Statistics

- **Total Articles Indexed**: 150
- **URLs in Registry**: 149
- **Data Sources**: 5 (1 API + 4 RSS feeds)

**Note**: The 1 article difference between registry (149) and index (150) is due to one test article uploaded during initial search index validation.

## Technology Stack

**Development**:
- Python 3.12.11 (trend-monitor conda environment)
- Visual Studio Code with auto-environment activation

**Libraries**:
- `azure-storage-blob` (12.26.0) - Blob storage operations
- `azure-ai-textanalytics` - Azure AI Language integration
- `azure-search-documents` (11.5.3) - Search index management
- `requests`, `feedparser`, `beautifulsoup4` - Data collection
- `python-dotenv` - Environment configuration

## Getting Started

### Prerequisites
- Python 3.12.11
- Conda environment: `trend-monitor`
- Azure account with Blob Storage, AI Language, and AI Search services

### Environment Setup
Create `.env` file with:
```
GUARDIAN_API_KEY=your_key_here
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
LANGUAGE_KEY=your_language_key
LANGUAGE_ENDPOINT=your_language_endpoint
SEARCH_ENDPOINT=your_search_endpoint
SEARCH_KEY=your_search_key
```

### Installation
```bash
conda activate trend-monitor
pip install -r requirements.txt
```

### Running the Pipeline
```bash
python run_pipeline.py
```

## Documentation

See `project_summary.ipynb` for comprehensive project documentation including:
- Detailed implementation timeline
- Performance optimizations
- Architecture decisions
- Testing and validation results
- Lessons learned
- Next steps and planning

## Next Milestone

**Phase 4 Development**: Building Streamlit interactive dashboard with search, filters, and trend visualizations. Deployment to Azure App Service for public access.

---

**Project**: AI Trend Monitor  
**Author**: Amanda Sumner  
**Repository**: [PieRatCat/ai-trend-monitor](https://github.com/PieRatCat/ai-trend-monitor)