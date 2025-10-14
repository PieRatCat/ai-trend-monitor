import logging
from dotenv import load_dotenv

# Import functions
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from src.storage import get_all_historical_articles, save_articles_to_blob
from src.utils import deduplicate_articles
from src.scrapers import get_full_content
from src.data_cleaner import clean_article_content
from src.language_analyzer import analyze_articles

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

    # Step 1: Fetch, Scrape, and Clean new articles
    logging.info("--- Starting: Fetch, Scrape, and Clean ---")
    api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
    rss_articles = fetch_rss_feeds(RSS_FEED_URLS)
    
    for article in rss_articles:
        if article.get('link'):
            full_html = get_full_content(article.get('link', ''))
            if full_html:
                article['content'] = full_html
    
    newly_collected_articles = api_articles + rss_articles
    for article in newly_collected_articles:
        article['content'] = clean_article_content(article.get('content', ''))

    # Step 2: Deduplicate against the entire history
    logging.info("\n--- Deduplicating against historical data ---")
    historical_articles = get_all_historical_articles(raw_container)
    unique_new_articles = deduplicate_articles(newly_collected_articles, historical_articles)
    
    if not unique_new_articles:
        logging.info("No unique new articles found. Pipeline finished.")
        return
    logging.info(f"Found {len(unique_new_articles)} new unique articles.")

    # Step 3: Save the new, clean, RAW articles
    logging.info(f"\n--- Saving {len(unique_new_articles)} new raw articles ---")
    save_articles_to_blob(unique_new_articles, raw_container)

    # Step 4: Analyze the new articles
    logging.info("\n--- Analyzing content with Azure AI Language ---")
    analyzed_articles = analyze_articles(unique_new_articles)

    # Step 5: Save the new ANALYZED articles
    logging.info(f"\n--- Saving {len(analyzed_articles)} new analyzed articles ---")
    save_articles_to_blob(analyzed_articles, analyzed_container)
    
    logging.info(f"\nPipeline Finished Successfully.")

if __name__ == '__main__':
    run_data_pipeline()