# AI Trend Monitor - Copilot Instructions

## Project Overview
This is an **AI news aggregation pipeline** that collects, deduplicates, analyzes, and stores AI-related articles from multiple sources. The pipeline runs as a scheduled batch job, storing results in Azure Blob Storage with Azure AI Language analysis.

## Project Goals

This project implements a comprehensive AI-powered news monitoring system with the following objectives:

1. **Data Pipeline Implementation** ✅ *Current Focus*
   - Build Python script to ingest news and social media data from multiple API sources and RSS feeds
   - Store all raw data in Azure Blob Storage
   - *Status*: Core pipeline implemented with Guardian API + 4 RSS feeds

2. **Advanced NLP Analysis** ✅ *Current Focus*
   - Apply Azure AI Language services (Key Phrase Extraction, Named Entity Recognition, Sentiment Analysis)
   - *Status*: Implemented with batched processing (25 docs at a time)

3. **Knowledge Mining** 🚧 *Planned*
   - Use Azure AI Search to index analyzed data
   - Create semantically searchable knowledge base

4. **Agentic Solution** 🚧 *Planned*
   - Build chatbot/agent using Azure OpenAI Service
   - Ground responses in the knowledge base

5. **Dynamic Web Interface** 🚧 *Planned*
   - Design responsive webpage (Azure App Service or Static Web Apps + Functions)
   - Display latest trends, headlines, and key statistics

6. **Final Output** 🚧 *Planned*
   - Comprehensive Jupyter Notebook
   - Live Azure webpage URL
   - Presentation documenting methodology, results, and insights

## Architecture & Data Flow

**Pipeline Stages** (see `run_pipeline.py`):
1. **Fetch** → Guardian API + RSS feeds (VentureBeat, Gizmodo, TechCrunch, Ars Technica) - metadata only
2. **Deduplicate** → Check URLs against registry BEFORE expensive scraping
3. **Scrape** → Full article content extraction (only for new articles) with site-specific selectors
4. **Clean** → HTML entity decoding, Unicode normalization, tag stripping
5. **Filter** → Remove articles with insufficient content (<100 chars) to avoid wasted Azure AI calls
6. **Analyze** → Azure AI Language (sentiment, entities, key phrases) in batches of 25, max 5120 chars/doc
7. **Store** → Save to Azure Blob Storage in timestamped compact JSON files
8. **Update Registry** → Add new URLs to processed_urls.json

Two containers: `raw-articles` (cleaned text) and `analyzed-articles` (with AI insights).

## Key Conventions

### Article Data Structure
All articles use this standardized schema across the pipeline:
```python
{
    'title': str,
    'link': str,              # Primary deduplication key
    'content': str,           # HTML initially, plain text after cleaning
    'source': str,            # e.g., 'The Guardian', 'venturebeat.com'
    'published_date': str,
    # After analysis:
    'sentiment': {...},
    'key_phrases': [...],
    'entities': [...]
}
```

### Source Configuration Pattern
All data sources are configured in `config/`:
- `api_sources.py` → API endpoint URLs (Guardian API)
- `rss_sources.py` → RSS feed URLs list
- `query.py` → Search query string (AI-related terms)

**To add new sources**: Update the appropriate config file and ensure the fetcher returns standardized article dicts.

**Note**: Guardian API no longer fetches body field during initial fetch; all sources now scraped consistently in Step 3.

### Web Scraping Strategy
`src/scrapers.py` uses a **prioritized selector fallback system**:
1. Check `SCRAPERS` dict for site-specific CSS selector (e.g., `venturebeat.com: 'div.article-body'`)
2. Try generic `FALLBACK_SELECTORS` list (`article`, `main`, common content divs)
3. Return empty string if all fail (logged as warning)

**Rate limiting**: Exponential backoff for 429 errors (1, 2, 4, 8 seconds over 4 attempts).
**Size limit**: HTML pages >5MB are skipped to prevent parsing issues.

**Supported sites**: VentureBeat, Gizmodo, TechCrunch, Ars Technica, The Guardian.

### Storage Patterns
- **URL registry deduplication** (`get_processed_urls`, `update_processed_urls`): Single `processed_urls.json` file tracks all analyzed article URLs for efficient deduplication
- **Timestamped files** (`save_articles_to_blob`): Filename format `{container}_YYYY-MM-DD_HH-MM-SS.json`, creates separate file for each pipeline run
- **Compact JSON**: No indentation in stored files to save 30-40% storage space
- All Azure operations use `AZURE_STORAGE_CONNECTION_STRING` from `.env`
- URL registry stored in `analyzed-articles` container to track what's been processed by Azure AI Language

### Error Handling Philosophy
- **Fail gracefully**: Empty list returns allow pipeline to continue (e.g., if Guardian API fails, RSS still runs)
- **Log extensively**: Use `logging.info` for progress, `.warning` for recoverable issues, `.error` for failures
- **No partial data**: Analysis batch failures return original articles without AI fields
- **Content validation**: Articles with <100 chars filtered before analysis; oversized HTML (>5MB) skipped
- **Truncation warnings**: Articles >5120 chars are truncated for Azure AI with logged warnings

## Performance Optimizations

**Cost & Efficiency Improvements** (implemented Oct 2025):

1. **Early URL Deduplication** → URLs checked against registry BEFORE scraping (saves ~2 min/run when no new articles)
2. **Compact JSON Storage** → No indentation in blob files (30-40% storage space savings)
3. **Content Filtering** → Articles with <100 chars skipped before Azure AI analysis (prevents wasted API calls)
4. **Truncation Logging** → Warns when articles >5120 chars are truncated for Azure AI
5. **HTML Size Limits** → Pages >5MB skipped to prevent parsing hangs
6. **Consistent Scraping** → Guardian API no longer fetches body field; all sources scraped uniformly

**Result**: Significant reduction in Azure costs, faster execution, no wasted processing.

## Development Workflow

### Environment Setup
**Conda Environment**: This project uses the `trend-monitor` conda environment.

```bash
# Activate the environment
conda activate trend-monitor

# Install dependencies (if needed)
pip install -r requirements.txt

# Create .env with:
# GUARDIAN_API_KEY=...
# AZURE_STORAGE_CONNECTION_STRING=...
# LANGUAGE_KEY=...
# LANGUAGE_ENDPOINT=...
```

### Running the Pipeline
```bash
python run_pipeline.py
```
**Expected output**: Log messages for each stage + final count of articles saved.

### Testing Individual Components
Import functions directly in Python/notebook:
```python
from src.rss_fetcher import fetch_rss_feeds
from config.rss_sources import RSS_FEED_URLS
articles = fetch_rss_feeds(RSS_FEED_URLS)
```

### Adding New RSS Feeds
1. Add URL to `config/rss_sources.py`
2. Test manually: `feedparser.parse('URL')`
3. Add site-specific selector to `src/scrapers.SCRAPERS` (domain as key, CSS selector as value)
4. Test scraping with a sample article URL

## Critical Dependencies

- **Azure Blob Storage**: Primary data persistence; compact JSON for efficiency
- **Azure AI Language**: Batched analysis (25 docs/request, 5120 char limit per doc, truncation logged)
- **BeautifulSoup**: HTML parsing for all scraped content (Guardian, RSS sources)
- **feedparser**: RSS feed parsing (handles various RSS/Atom formats)

## Common Pitfalls

1. **Encoding issues**: All sources now scraped consistently; clean with `data_cleaner.clean_article_content` AFTER scraping
2. **URL registry corruption**: If `processed_urls.json` is corrupted, delete it and re-run `bootstrap_url_registry.py`
3. **Azure timeouts**: Analysis batches can take 30-60s; normal for large batches
4. **Link variations**: Some RSS feeds have tracking params; consider URL normalization for better dedup
5. **Content filtering**: Articles with <100 chars are filtered out before analysis to save costs
6. **Truncation**: Long articles (>5120 chars) are truncated for Azure AI; check warnings for affected articles
