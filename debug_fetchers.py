import json
from dotenv import load_dotenv

# Import the functions and configs you want to test
from src.api_fetcher import fetch_guardian_api
from src.rss_fetcher import fetch_rss_feeds
from config.api_sources import API_SOURCES
from config.rss_sources import RSS_FEED_URLS
from config.query import SEARCH_QUERY

def run_tests():
    """
    Runs an isolated test for each data fetcher and prints the output.
    """
    # Make sure to load your API keys
    load_dotenv()
    
    print("--- 1. Testing The Guardian API Fetcher ---")
    try:
        api_articles = fetch_guardian_api(API_SOURCES['guardian'], SEARCH_QUERY)
        
        if api_articles:
            print(f"SUCCESS: Fetched {len(api_articles)} articles from the API.")
            print("--- First API Article (raw data): ---")
            # Pretty-print the first article to see its structure
            print(json.dumps(api_articles[0], indent=4))
        else:
            print("FAILURE: The API fetcher returned no articles.")
            
    except Exception as e:
        print(f"ERROR: An exception occurred while testing the API fetcher: {e}")

    print("\n" + "="*50 + "\n")

    print("--- 2. Testing the RSS Feed Fetcher ---")
    try:
        rss_articles = fetch_rss_feeds(RSS_FEED_URLS)
        
        if rss_articles:
            print(f"SUCCESS: Fetched {len(rss_articles)} articles from RSS feeds.")
            print("--- First RSS Article (raw data): ---")
            # Pretty-print the first article to see its structure
            print(json.dumps(rss_articles[0], indent=4))
        else:
            print("FAILURE: The RSS fetcher returned no articles.")
            
    except Exception as e:
        print(f"ERROR: An exception occurred while testing the RSS fetcher: {e}")

if __name__ == '__main__':
    run_tests()