import logging
from dotenv import load_dotenv

# Import functions
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from src.storage import get_processed_urls, update_processed_urls, save_articles_to_blob
from src.scrapers import get_full_content
from src.data_cleaner import clean_article_content
from src.language_analyzer import analyze_articles
from src.search_indexer import index_articles

# Import configuration
from config.api_sources import API_SOURCES
from config.rss_sources import RSS_FEED_URLS
from config.query import SEARCH_QUERY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_data_pipeline():
    load_dotenv()
    raw_container = 'raw-articles'
    analyzed_container = 'analyzed-articles'

    # Step 1: Fetch article metadata (titles, links, basic content)
    logging.info("--- Starting: Fetch Articles ---")
    api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
    rss_articles = fetch_rss_feeds(RSS_FEED_URLS)
    
    newly_collected_articles = api_articles + rss_articles
    logging.info(f"Fetched {len(newly_collected_articles)} articles total.")

    # Step 2: Deduplicate against processed URLs BEFORE scraping
    logging.info("\n--- Deduplicating against processed URLs ---")
    processed_urls = get_processed_urls(analyzed_container)
    
    # Filter out articles that have already been processed
    unique_new_articles = [
        article for article in newly_collected_articles
        if article.get('link') and article.get('link') not in processed_urls
    ]
    
    num_duplicates = len(newly_collected_articles) - len(unique_new_articles)
    logging.info(f"Found and removed {num_duplicates} already-processed articles.")
    
    if not unique_new_articles:
        logging.info("No unique new articles found. Pipeline finished.")
        return
    logging.info(f"Found {len(unique_new_articles)} new unique articles to process.")
    
    # Step 3: Scrape and Clean ONLY the new articles
    logging.info(f"\n--- Scraping and cleaning {len(unique_new_articles)} new articles ---")
    for article in unique_new_articles:
        if article.get('link'):
            full_html = get_full_content(article.get('link', ''))
            if full_html:
                article['content'] = full_html
        article['content'] = clean_article_content(article.get('content', ''))
    
    # Filter out articles with empty content before expensive operations
    articles_with_content = [
        article for article in unique_new_articles
        if article.get('content') and len(article.get('content', '').strip()) > 100
    ]
    
    num_empty = len(unique_new_articles) - len(articles_with_content)
    if num_empty > 0:
        logging.warning(f"Filtered out {num_empty} articles with insufficient content (< 100 chars).")
    
    if not articles_with_content:
        logging.info("No articles with sufficient content to analyze. Pipeline finished.")
        return

    # Step 4: Save the new, clean, RAW articles (only those with content)
    logging.info(f"\n--- Saving {len(articles_with_content)} new raw articles ---")
    save_articles_to_blob(articles_with_content, raw_container)

    # Step 5: Analyze the new articles (only those with content)
    logging.info("\n--- Analyzing content with Azure AI Language ---")
    analyzed_articles = analyze_articles(articles_with_content)

    # Step 6: Save the new ANALYZED articles
    logging.info(f"\n--- Saving {len(analyzed_articles)} new analyzed articles ---")
    save_articles_to_blob(analyzed_articles, analyzed_container)
    
    # Step 7: Update the URL registry with newly processed articles
    logging.info("\n--- Updating URL registry ---")
    new_urls = [article.get('link') for article in analyzed_articles if article.get('link')]
    update_processed_urls(new_urls, analyzed_container)
    
    # Step 8: Index articles in Azure AI Search
    logging.info("\n--- Indexing articles in Azure AI Search ---")
    indexed_count = index_articles(analyzed_articles)
    logging.info(f"Indexed {indexed_count} articles in search index.")
    
    logging.info(f"\nPipeline Finished Successfully.")

if __name__ == '__main__':
    run_data_pipeline()