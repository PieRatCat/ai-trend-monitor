# AI Trend Monitor - Copilot Instructions

## Project Overview
This is an **AI news aggregation pipeline** that collects, deduplicates, analyzes, and stores AI-related articles from multiple sources. The pipeline runs as a scheduled batch job, storing results in Azure Blob Storage with Azure AI Language analysis.

## Critical Development Rules

### Environment Rule
**⚠️ ALWAYS activate the `trend-monitor` conda environment before running ANY Python scripts, terminal commands, or installations.**

When running Python scripts or commands in terminal, ensure you're in the correct environment:
- Windows PowerShell: First activate with `conda activate trend-monitor`
- All Python package installations must use: `conda activate trend-monitor ; pip install <package>`
- All script executions must use: `conda activate trend-monitor ; python <script.py>`

### UI/UX Style Rule
**❌ NO EMOJIS in Streamlit dashboard pages.**

When creating or editing Streamlit pages:
- Do NOT use emojis in titles, headers, buttons, or text
- Keep styling consistent with existing pages (News, Analytics)
- Use professional, clean typography
- Focus on clarity and readability over decorative elements

## Project Goals

This project implements a comprehensive AI-powered news monitoring system with the following objectives:

1. **Data Pipeline Implementation** ✅ *COMPLETE*
   - Build Python script to ingest news and social media data from multiple API sources and RSS feeds
   - Store all raw data in Azure Blob Storage
   - *Status*: Core pipeline implemented with Guardian API + 4 RSS feeds

2. **Advanced NLP Analysis** ✅ *COMPLETE*
   - Apply Azure AI Language services (Key Phrase Extraction, Named Entity Recognition, Sentiment Analysis)
   - *Status*: Implemented with batched processing (25 docs at a time)

3. **Knowledge Mining** ✅ *COMPLETE*
   - Use Azure AI Search to index analyzed data
   - Create searchable knowledge base
   - *Status*: 150 articles indexed with automated pipeline integration, keyword search operational

4. **Interactive Web Dashboard** ✅ *COMPLETE*
   - Streamlit web application with responsive design
   - Four pages: News, Analytics, Chat, About
   - Priority-based Analytics layout with interactive visualizations
   - Professional Claude-inspired color palette
   - Fully responsive (desktop, laptop, tablet, mobile)
   - *Status*: Production-ready with CSS externalization

5. **RAG-Powered Chatbot** ✅ *COMPLETE*
   - GitHub Models integration (GPT-4.1-mini)
   - Retrieval-Augmented Generation (RAG) pattern
   - Temporal query detection ("last 24 hours", "past week", etc.)
   - Smart token budget management
   - Conversation history support
   - *Status*: Fully functional with 15 default article retrieval

6. **Automated Weekly Reports** 🚧 *PLANNED*
   - Create weekly automated trend reports
   - Generate insights summaries with Azure OpenAI
   - Deliver comprehensive analysis of AI landscape changes

## Architecture & Data Flow

**Pipeline Stages** (see `run_pipeline.py`):
1. **Fetch** → Guardian API (with `from-date: 2025-06-01`) + RSS feeds (VentureBeat, Gizmodo, TechCrunch, Ars Technica) - metadata only
2. **Deduplicate** → Check URLs against registry BEFORE expensive scraping
3. **Scrape** → Full article content extraction (only for new articles) with site-specific selectors
4. **Clean** → HTML entity decoding, Unicode normalization, tag stripping
5. **Filter** → Remove articles with insufficient content (<100 chars) to avoid wasted Azure AI calls
6. **Analyze** → Azure AI Language (sentiment, entities, key phrases) in batches of 25, max 5120 chars/doc
7. **Store** → Save to Azure Blob Storage in timestamped compact JSON files
8. **Update Registry** → Add new URLs to processed_urls.json
9. **Index** → Upload to Azure AI Search for searchability

**Date Filtering Architecture**:
- **Guardian API**: `from-date: 2025-06-01` parameter prevents fetching old articles at source
- **Dashboard Analytics**: Client-side filtering in `get_all_articles()` to June 1, 2025+
- **Topic Trend Timeline**: Filters search results to June 1, 2025+
- **Chatbot RAG**: Temporal query detection + date filtering in `retrieve_articles()`
  - Detects phrases: "last 24 hours", "past week", "last X days", etc.
  - Uses `order_by="published_date desc"` for efficient retrieval
  - Smart token budget management (5000 tokens default, 3500 with conversation history)

Three containers: `raw-articles` (cleaned text), `analyzed-articles` (with AI insights + URL registry), and Azure AI Search index `ai-articles-index` (184 articles).

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
# SEARCH_ENDPOINT=...
# SEARCH_KEY=...
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
- **Azure AI Search**: Free tier (F) with keyword search; 262 articles indexed
- **BeautifulSoup**: HTML parsing for all scraped content (Guardian, RSS sources)
- **feedparser**: RSS feed parsing (handles various RSS/Atom formats)
- **azure-search-documents** (11.5.3): Search index management and querying

## Common Pitfalls

1. **Encoding issues**: All sources now scraped consistently; clean with `data_cleaner.clean_article_content` AFTER scraping
2. **URL registry corruption**: If `processed_urls.json` is corrupted, delete it and re-run `bootstrap_url_registry.py`
3. **Azure timeouts**: Analysis batches can take 30-60s; normal for large batches
4. **Link variations**: Some RSS feeds have tracking params; consider URL normalization for better dedup
5. **Content filtering**: Articles with <100 chars are filtered out before analysis to save costs
6. **Truncation**: Long articles (>5120 chars) are truncated for Azure AI; check warnings for affected articles
7. **Search field names**: Use `link` (not `url`), `sentiment_overall` (not `sentiment_label`) when querying index

## Current System Status

**Phases Complete**: 5 of 6
- ✅ Phase 1: Data Pipeline (Guardian API + 4 RSS feeds)
- ✅ Phase 2: NLP Analysis (Azure AI Language)
- ✅ Phase 3: Knowledge Mining (Azure AI Search with 184 articles)
- ✅ Phase 4: Streamlit Dashboard (Complete with responsive design)
- ✅ Phase 5: RAG Chatbot (Complete with GitHub Models integration + temporal query support)
- 📋 Phase 6: Automated Reports (Planned)

**Key Metrics**:
- 184 articles indexed (143 active after June 1, 2025 filter)
- 17 from latest pipeline run (Oct 16, 2025)
- Free tier Search + Standard tier Language
- Date range: June 3, 2025 - October 16, 2025

**Dashboard Status**:
- ✅ News page with curated content and article cards
- ✅ Analytics page with Priority-Based Layout (optimized Oct 16, 2025)
- ✅ Chat page with RAG-powered conversational AI (temporal queries + token management)
- ✅ Responsive design complete (desktop, laptop, tablet, mobile)
- ✅ CSS externalized to styles.css (350 lines)
- ✅ Date filtering (June 1, 2025 cutoff) applied across all pages

**Recent Improvements (October 16-21, 2025 - Sessions 36-37)**:
- Guardian API now filters articles at source (`from-date: 2025-06-01`)
- Chatbot detects temporal queries ("last 24 hours", "past week", etc.)
- Azure AI Search results ordered by date for temporal queries
- Smart token budget management prevents 413 errors
- Default article retrieval increased from 5 to 15 for comprehensive summaries
- Responsive design implementation with CSS externalization
- 4 mobile breakpoints (1200px, 1024px, 768px, 480px)
- Viewport-based font scaling with clamp()
- Complete overflow protection for metrics, buttons, tables
- Charts scale smoothly across all device sizes

## Analytics Page Layout (Priority-Based Design)

**Current Structure**:
- **Row 1**: Topic Trend Timeline (FULL WIDTH)
  - Interactive entity selection with search
  - Three visualization modes: Daily Count, Cumulative Count, Weekly Aggregation
  - Dual-axis chart: Article count (left) + Net sentiment (right)
  - 4 metrics below: Total Articles, Positive %, Negative %, Date Range
  - Chart size: 10" wide x 3.5" tall

- **Row 2**: Net Sentiment Distribution (55%) | Source Statistics & Growth (45%)
  - Left: Histogram with sentiment spectrum (-1 to +1)
    - Chart size: 6" wide x 3.5" tall
    - 8 metrics in 2 rows (Positive, Neutral, Negative, Mixed, Leaning scores, Mean, Median)
  - Right: HTML table with sentiment bars + Growth metrics
    - Table font: 16px body, 15px headers, 13px bar labels
    - Sentiment bars ordered: Negative → Neutral → Positive → Mixed
    - Growth Overview: Total Articles, Latest Month with growth stats, Date Range

- **Row 3**: Word Cloud (60%) | Top 10 Topics (40%)
  - Entity frequency visualization
  - Topic distribution table

**Design Principles Applied**:
- No wasted white space (all sections utilize available width)
- Full-width priority chart for most important visualization
- Balanced column ratios in lower rows (1.2:1 for row 2)
- Consistent font sizing (minimum 16px for body text)
- Professional color palette (`AITREND_COLOURS`: teal, tan, orange, warm beiges)
- No emojis or misleading delta indicators

## Data Filtering Strategy

**Hard Cutoff Date**: June 1, 2025

**Rationale**:
- 95.3% of articles are from June 2025 onwards (143 articles)
- Only 7 articles before June 2025 (outliers from 2023-2024)
- Creates clean 5-month dataset with meaningful trend analysis
- Removes sparse historical data that skews visualizations

**Implementation**:
- Applied in `get_all_articles()` function
- Also applied in Topic Trend Timeline search results
- Uses `dateutil.parser` for flexible date parsing
- Timezone-aware comparison with fallback handling

**Result**:
- Cleaner trend visualizations
- More accurate growth metrics
- Better representation of current AI news landscape
- Sidebar shows "Earliest Article: Jun 3, 2025"

## Dashboard Theme & Styling Guide

**Color Scheme**: `AITREND_COLOURS` (defined in `streamlit_app/app.py`)

This is our custom professional color palette, optimized for accessibility and brand consistency:

- **Primary**: Muted warm brown/tan for primary brand elements
- **Secondary**: Soft taupe for secondary accents
- **Accent**: Rich dark brown for links and emphasis
- **Positive**: Muted teal/blue for positive sentiment (color-blind safe)
- **Neutral**: Medium warm tan for neutral sentiment
- **Negative**: Warm amber/orange for negative sentiment (color-blind safe)
- **Mixed**: Deeper purple for mixed sentiment
- **Background**: Warm light beige for page backgrounds
- **Text**: Dark charcoal grey for primary text

**Key Principles**:
- Warm beige/grey tones for professional aesthetic
- Color-blind accessible (teal vs. orange for sentiment, not red/green)
- High contrast for WCAG AA compliance
- Consistent across all visualizations

**Typography**:
- **Primary**: Libre Baskerville (serif) for main headings
- **Body**: System fallback (Georgia, serif)
- **Minimum size**: 16px for readability

**When creating new visualizations or UI components**:
- Always use `AITREND_COLOURS` dictionary for color references
- Never hardcode hex values directly
- Maintain consistency with existing chart styles
- Reference `project_summary.ipynb` section 2.4 for complete styling guide
- All CSS styling now in `streamlit_app/styles.css` (350 lines)
- Use `get_responsive_figsize()` helper for chart dimensions

## Responsive Design Implementation (Session 37 - October 21, 2025)

**Status**: ✅ **COMPLETE** - Dashboard fully responsive across all devices

**Implemented Features**:
1. ✅ **CSS Externalization**: All styles moved to `streamlit_app/styles.css`
2. ✅ **Viewport-Based Font Scaling**: Using `clamp()` for smooth responsive typography
3. ✅ **Column Stacking**: Automatic on screens <1200px width
4. ✅ **Chart Responsiveness**: CSS-based scaling maintains aspect ratio
5. ✅ **Overflow Protection**: Multi-layer protection for metrics, buttons, tables
6. ✅ **Mobile Breakpoints**: 4 levels (1200px, 1024px, 768px, 480px)

**Breakpoints Implemented**:
- **1200px**: Single-column layout forced
- **1024px**: Reduced padding for tablets
- **768px**: Mobile-optimized spacing, larger touch targets (3rem button height)
- **480px**: Small phone font size adjustments

**Code Organization**:
- `streamlit_app/app.py`: 1,550 lines (Python logic only)
- `streamlit_app/styles.css`: 350 lines (all presentation)
- Helper function: `get_responsive_figsize(base_width, base_height, container_fraction=1.0)`

**Testing Results**:
- ✅ Desktop (1920px): Professional layout, optimal spacing
- ✅ Laptop (1366px): Content scales smoothly, no clipping
- ✅ Tablet (1024px): Columns stack, appropriate padding
- ✅ Mobile (768px): Single column, larger touch targets
- ✅ Small mobile (480px): Readable fonts, vertical stacking

## AI Model Strategy - Phases 5 & 6

### Model Selection: GPT-4.1-mini

**Chosen Model**: OpenAI GPT-4.1-mini (via GitHub Models initially, migrating to Azure AI Foundry for production)

**Rationale**:
- **Cost-effective**: $0.70 per 1M tokens (affordable for learning and production)
- **High quality**: 0.8066 quality index (83% better than Phi-4-mini-instruct)
- **Large context**: 1M input / 33K output tokens (essential for multi-article analysis)
- **Fast throughput**: 125 tokens/sec (3x faster than alternatives)
- **Excellent for use cases**: Long-context handling, instruction following, report generation

**Use Cases in This Project**:
1. **RAG Chatbot (Phase 5)**: Conversational queries about article content with multiple retrieved articles in context
2. **Weekly Reports (Phase 6)**: Automated trend summaries analyzing patterns across 10-20 articles simultaneously
3. **Summarization**: High-quality, nuanced text generation for professional outputs

### Development Path: GitHub Models → Azure AI Foundry

**Phase 1: Prototype with GitHub Models (FREE)**

**Benefits**:
- ✅ Free to start (no charge until hitting rate limits)
- ✅ Quick setup (GitHub Personal Access Token only)
- ✅ Single endpoint for all models: `https://models.github.ai/inference/`
- ✅ Perfect for learning, testing, and initial development
- ✅ No credit card required

**Free Tier Limitations**:
- Rate limits: ~15-60 requests/minute depending on model
- Token limits: ~150K-500K tokens/minute
- Daily limits: ~500-1000 requests/day
- Best-effort availability (no SLA guarantees)
- Suitable for development, testing, and low-traffic demos

**Use For**:
- Building and testing RAG chatbot functionality
- Validating prompts and response quality
- Generating sample weekly reports
- A/B testing different models if needed
- Initial dashboard integration

**Phase 2: Migrate to Azure AI Foundry (PAID)**

**When to Migrate**:
- 🚨 Hit rate limits (users experience 429 errors)
- 🚨 Dashboard reaches 50+ daily users
- 🚨 Need production SLA guarantees
- 🚨 Ready for public demo or deployment
- 🚨 Require predictable performance

**Migration Benefits**:
- Dedicated capacity with no rate limits (within your tier)
- 99.9% uptime SLA for production workloads
- Azure VNET integration for security
- Better monitoring and logging via Azure portal
- Support for custom fine-tuning (if needed later)

**Migration Effort**: Minimal (same OpenAI-compatible API)

```python
# GitHub Models (Development)
from openai import OpenAI
client = OpenAI(
    base_url="https://models.github.ai/inference",
    api_key=os.getenv("GITHUB_TOKEN")
)

# Azure AI Foundry (Production) - Only 2 lines change:
client = OpenAI(
    base_url="https://your-endpoint.openai.azure.com",
    api_key=os.getenv("AZURE_OPENAI_KEY")
)
# Rest of code stays identical!
```

**Production Cost Estimates (Azure AI Foundry)**:
- 100 queries/day: ~$3/month
- 500 queries/day: ~$15/month
- 1,000 queries/day: ~$30/month
- 4 weekly reports: +$0.03/month
- **Total expected**: $10-30/month for typical usage

### Alternative Considered: Phi-4-mini-instruct

**Specs**:
- Cost: $0.1312 per 1M tokens (81% cheaper)
- Quality: 0.4429 (significantly lower - nearly half of GPT-4.1-mini)
- Context: 128K input / 4K output (much smaller)
- Best for: Simple function calling, short queries, edge deployment

**Why Not Chosen**:
- ❌ Quality gap too large (0.44 vs 0.81) for public-facing dashboard
- ❌ Limited context (128K) may struggle with multi-article RAG
- ❌ Small output (4K) insufficient for comprehensive weekly reports
- ❌ Cost savings negligible at low volumes ($0.10/month difference)
- ❌ Risk of degraded user experience not worth minimal savings

**Hybrid Approach (Optional Future Optimization)**:
- Use GPT-4.1-mini for complex tasks (reports, multi-article analysis)
- Use Phi-4-mini-instruct for simple tasks (single article summaries, basic Q&A)
- Optimize cost/quality balance at scale

### Implementation Notes

**Environment Variables** (add to `.env`):
```bash
# Phase 1: GitHub Models
GITHUB_TOKEN=ghp_your_personal_access_token_here

# Phase 2: Azure AI Foundry (when migrating)
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_KEY=your_azure_openai_key_here
AZURE_OPENAI_DEPLOYMENT=gpt-4-1-mini  # Your deployment name
```

**Model ID for GitHub Models**: `openai/gpt-4.1-mini`

**Recommended Monitoring**:
- Track request counts and token usage
- Monitor response quality and latency
- Set up alerts before hitting rate limits
- Plan migration timeline based on growth

### Next Steps for Phases 5 & 6

**Phase 5 (RAG Chatbot)**:
1. Set up GitHub Models authentication with GitHub PAT
2. Integrate Azure AI Search for article retrieval
3. Build RAG pipeline with GPT-4.1-mini
4. Test conversational queries with multiple articles in context
5. Validate response quality and latency

**Phase 6 (Weekly Reports)**:
1. Design report structure and prompts
2. Use GPT-4.1-mini to generate multi-section reports
3. Integrate with Azure Functions for scheduling
4. Test with historical data (weekly trends over 4-6 weeks)
5. Implement delivery mechanism (email/dashboard)

**Migration Checkpoint**:
- Monitor usage during Phases 5-6 development
- Plan Azure AI Foundry migration when approaching GitHub Models limits
- Budget $10-30/month for production deployment

