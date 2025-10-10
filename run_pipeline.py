import logging
import json
from dotenv import load_dotenv

# Import functions from your separate scripts
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from src.storage import get_existing_articles, save_to_blob_storage
from src.utils import deduplicate_articles

# Import configuration
from config.api_sources import API_SOURCES
from config.rss_sources import RSS_FEED_URLS
from config.query import SEARCH_QUERY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_data_pipeline():
    """
    Runs the data collection, deduplication, and storage pipeline.
    It populates the 'content' field directly from the 'summary'.
    """
    load_dotenv()
    container_name = 'ai-news'
    blob_name = 'ai-news.json'

    logging.info("--- Pipeline Starting: Data Collection ---")

    # 1. Fetch data from all sources
    api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
    rss_articles = fetch_rss_feeds(RSS_FEED_URLS)
    
    newly_collected_articles = api_articles + rss_articles

    # 2. **Baseline Step**: Create the 'content' field directly from the 'summary'
    for article in newly_collected_articles:
        article['content'] = article.get('summary', '')

    logging.info(f"Total articles collected and processed: {len(newly_collected_articles)}")

    # 3. Get existing articles for deduplication
    logging.info("\n--- Checking for existing articles in Blob Storage ---")
    existing_articles = get_existing_articles(container_name, blob_name)

    # 4. Deduplicate the new articles
    unique_new_articles = deduplicate_articles(newly_collected_articles, existing_articles)
    
    if not unique_new_articles:
        logging.info("No unique new articles found. Pipeline finished.")
        return

    logging.info(f"Found {len(unique_new_articles)} new unique articles.")

    # 5. Combine and save
    all_articles = existing_articles + unique_new_articles
    logging.info("\n--- Saving combined data to Azure Blob Storage ---")
    save_to_blob_storage(all_articles, container_name, blob_name)
    
    logging.info(f"\nPipeline Finished. Total articles saved: {len(all_articles)}")

if __name__ == '__main__':
    run_data_pipeline()