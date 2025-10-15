import feedparser
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any

def fetch_rss_feeds(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches article metadata from a list of RSS feed URLs.
    Does NOT scrape full content - that happens later after deduplication.

    Args:
        urls: A list of RSS feed URLs.

    Returns:
        A list of standardized article dictionaries with metadata only.
    """
    logging.info("Fetching data from RSS feeds...")
    articles = []
    for url in urls:
        source_name = urlparse(url).netloc
        logging.info(f"  -> Parsing {source_name}...")
        try:
            feed = feedparser.parse(url)
            if feed.entries:
                for entry in feed.entries:
                    articles.append({
                        'title': entry.get('title', 'No Title'),
                        'link': entry.get('link'),
                        'content': entry.get('summary', '') or '',  # RSS summary only, not full scrape
                        'source': source_name,
                        'published_date': entry.get('published')
                    })
            else:
                logging.warning(f"  -> No entries found in feed from {url}")
        except Exception as e:
            logging.error(f"  -> Error parsing {url}: {e}")
    logging.info(f"Successfully fetched {len(articles)} articles from RSS feeds.")
    return articles
