import logging
from dotenv import load_dotenv

# Import all necessary functions
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from src.storage import get_existing_articles, save_to_blob_storage
from src.utils import deduplicate_articles
from src.scrapers import get_full_content
from src.data_cleaner import clean_article_content

# Import configuration
from config.api_sources import API_SOURCES
from config.rss_sources import RSS_FEED_URLS
from config.query import SEARCH_QUERY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_data_pipeline():
    """
    Runs the full data collection, scraping, cleaning, deduplication, and storage pipeline.
    """
    load_dotenv()
    container_name = 'ai-news'
    blob_name = 'ai-news.json'

    logging.info("--- Pipeline Starting: Data Collection & Scraping ---")

    # 1. Fetch data from sources
    api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
    rss_articles = fetch_rss_feeds(RSS_FEED_URLS)

    # 2. Scrape full content for RSS articles
    logging.info(f"Scraping content for {len(rss_articles)} RSS articles...")
    for article in rss_articles:
        if article.get('link'):
            try:
                full_html = get_full_content(article['link'])
                if full_html:
                    article['content'] = full_html # Overwrite summary with full content
            except Exception as e:
                logging.warning(f"Scraping failed for {article.get('link')}: {e}. Using summary.")

    # 3. Combine and Clean All Articles
    newly_collected_articles = api_articles + rss_articles
    logging.info(f"\n--- Cleaning {len(newly_collected_articles)} total articles ---")
    
    # --> THIS IS THE FIX <--
    # Loop through the combined list and clean every article.
    for article in newly_collected_articles:
        raw_content = article.get('content', '')
        article['content'] = clean_article_content(raw_content)

    logging.info("All articles have been cleaned.")

    # 4. Deduplicate against existing articles
    logging.info("\n--- Checking for existing articles in Blob Storage ---")
    existing_articles = get_existing_articles(container_name, blob_name)
    unique_new_articles = deduplicate_articles(newly_collected_articles, existing_articles)
    
    if not unique_new_articles:
        logging.info("No unique new articles found. Pipeline finished.")
        return

    logging.info(f"Found {len(unique_new_articles)} new unique articles.")

    # 5. Combine and save the final list
    all_articles = existing_articles + unique_new_articles
    logging.info("\n--- Saving combined data to Azure Blob Storage ---")
    save_to_blob_storage(all_articles, container_name, blob_name)
    
    logging.info(f"\nPipeline Finished. Total articles saved: {len(all_articles)}")

if __name__ == '__main__':
    run_data_pipeline()