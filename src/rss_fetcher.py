import feedparser
import logging
from urllib.parse import urlparse
from typing import List, Dict, Any
from .scrapers import get_full_content

def fetch_rss_feeds(urls: List[str]) -> List[Dict[str, Any]]:
    """
    Fetches articles from a list of RSS feed URLs.

    Args:
        urls: A list of RSS feed URLs.

    Returns:
        A list of standardized article dictionaries.
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
                    # Check if a link exists to scrape
                    link = entry.get('link')
                    if link:
                        try:
                            full_content = get_full_content(link)
                        except Exception as e:
                            logging.warning(f"    -> Failed to scrape full content for {link}: {e}")
                            full_content = entry.get('summary', '') or ''
                    else:
                        full_content = entry.get('summary', '') or ''

                    articles.append({
                        'title': entry.get('title', 'No Title'),
                        'link': link,
                        'content': full_content,
                        'source': source_name,
                        'published_date': entry.get('published')
                    })
            else:
                logging.warning(f"  -> No entries found in feed from {url}")
        except Exception as e:
            logging.error(f"  -> Error parsing {url}: {e}")
    logging.info(f"Successfully fetched {len(articles)} articles from RSS feeds.")
    return articles
