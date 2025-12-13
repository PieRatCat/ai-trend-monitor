"""
Weekly Pipeline - Combines data collection, analysis, and report generation
Designed to run once per week on Azure Functions
"""
import logging
from dotenv import load_dotenv
from datetime import datetime

# Import existing pipeline functions
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from src.storage import get_processed_urls, update_processed_urls, save_articles_to_blob
from src.scrapers import get_full_content
from src.data_cleaner import clean_article_content
from src.language_analyzer import analyze_articles
from src.search_indexer import index_articles

# Import report generation
from src.generate_weekly_report import WeeklyReportGenerator

# Import curated content generation
from src.generate_curated_news import generate_curated_content, save_to_blob
from src.rag_chatbot import RAGChatbot

# Import configuration
from config.api_sources import API_SOURCES
from config.rss_sources import RSS_FEED_URLS
from config.query import SEARCH_QUERY

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_weekly_pipeline():
    """
    Complete weekly pipeline:
    1. Fetch and analyze new articles
    2. Generate weekly report
    3. Send email newsletter
    """
    load_dotenv()
    
    logging.info(f"=== WEEKLY PIPELINE STARTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
    
    # ========== PART 1: DATA COLLECTION & ANALYSIS ==========
    
    raw_container = 'raw-articles'
    analyzed_container = 'analyzed-articles'

    # Step 1: Fetch article metadata
    logging.info("--- Step 1: Fetch Articles ---")
    api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
    rss_articles = fetch_rss_feeds(RSS_FEED_URLS)
    
    newly_collected_articles = api_articles + rss_articles
    logging.info(f"Fetched {len(newly_collected_articles)} articles total.")

    # Step 2: Deduplicate against processed URLs
    logging.info("\n--- Step 2: Deduplicate Against Registry ---")
    processed_urls = get_processed_urls(analyzed_container)
    
    unique_new_articles = [
        article for article in newly_collected_articles
        if article.get('link') and article.get('link') not in processed_urls
    ]
    
    num_duplicates = len(newly_collected_articles) - len(unique_new_articles)
    logging.info(f"Removed {num_duplicates} already-processed articles.")
    logging.info(f"Found {len(unique_new_articles)} new unique articles to process.")
    
    # Step 3: Scrape and clean new articles
    if unique_new_articles:
        logging.info(f"\n--- Step 3: Scrape & Clean {len(unique_new_articles)} Articles ---")
        for article in unique_new_articles:
            if article.get('link'):
                full_html = get_full_content(article.get('link', ''))
                if full_html:
                    article['content'] = full_html
            article['content'] = clean_article_content(article.get('content', ''))
        
        # Filter out articles with insufficient content
        articles_with_content = [
            article for article in unique_new_articles
            if article.get('content') and len(article.get('content', '').strip()) > 100
        ]
        
        num_empty = len(unique_new_articles) - len(articles_with_content)
        if num_empty > 0:
            logging.warning(f"Filtered out {num_empty} articles with insufficient content.")
        
        if articles_with_content:
            # Step 4: Save raw articles
            logging.info(f"\n--- Step 4: Save {len(articles_with_content)} Raw Articles ---")
            save_articles_to_blob(articles_with_content, raw_container)

            # Step 5: Analyze with Azure AI Language
            logging.info("\n--- Step 5: Analyze with Azure AI Language ---")
            analyzed_articles = analyze_articles(articles_with_content)

            # Step 6: Save analyzed articles
            logging.info(f"\n--- Step 6: Save {len(analyzed_articles)} Analyzed Articles ---")
            save_articles_to_blob(analyzed_articles, analyzed_container)
            
            # Step 7: Update URL registry
            logging.info("\n--- Step 7: Update URL Registry ---")
            new_urls = [article.get('link') for article in analyzed_articles if article.get('link')]
            update_processed_urls(new_urls, analyzed_container)
            
            # Step 8: Index in Azure AI Search
            logging.info("\n--- Step 8: Index in Azure AI Search ---")
            indexed_count = index_articles(analyzed_articles)
            logging.info(f"Indexed {indexed_count} articles successfully.")
        else:
            logging.info("No articles with sufficient content to analyze.")
    else:
        logging.info("No new unique articles found this week.")
    
    # ========== PART 2: CURATED CONTENT GENERATION ==========
    
    logging.info("\n\n=== STARTING CURATED CONTENT GENERATION ===\n")
    
    try:
        # Step 9: Generate curated homepage content
        logging.info("--- Step 9: Generate Curated Homepage Content ---")
        chatbot = RAGChatbot()
        
        # Generate products section
        products_content = generate_curated_content("products", chatbot)
        if products_content:
            save_to_blob("products", products_content)
            logging.info("✓ Products section generated and saved")
        else:
            logging.warning("Failed to generate products content")
        
        # Generate industry section
        industry_content = generate_curated_content("industry", chatbot)
        if industry_content:
            save_to_blob("industry", industry_content)
            logging.info("✓ Industry section generated and saved")
        else:
            logging.warning("Failed to generate industry content")
            
    except Exception as e:
        logging.error(f"Error during curated content generation: {str(e)}")
    
    # ========== PART 3: WEEKLY REPORT GENERATION & EMAIL ==========
    
    logging.info("\n\n=== STARTING REPORT GENERATION ===\n")
    
    try:
        # Step 10: Generate weekly report
        logging.info("--- Step 10: Generate Weekly Report ---")
        generator = WeeklyReportGenerator()
        report = generator.generate_full_report()
        
        if report:
            logging.info("Report generated successfully.")
            
            # Step 11: Send email newsletter
            logging.info("\n--- Step 11: Send Email Newsletter ---")
            email_sent = generator.send_report_email(report)
            
            if email_sent:
                logging.info("✓ Email newsletter sent successfully!")
            else:
                logging.warning("Email sending failed or skipped.")
        else:
            logging.error("Report generation failed.")
    
    except Exception as e:
        logging.error(f"Error during report generation/email: {str(e)}")
    
    logging.info(f"\n=== WEEKLY PIPELINE COMPLETED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

if __name__ == '__main__':
    run_weekly_pipeline()
