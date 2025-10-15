import os
import requests
import json
import logging
from typing import List, Dict, Any

def fetch_guardian_api(source_details: Dict[str, Any], query_string: str) -> List[Dict[str, Any]]:
    """
    Fetches articles from the Guardian Open Platform API.

    Args:
        source_details: A dictionary containing the API URL.
        query_string: The query string for the API request.

    Returns:
        A list of standardized article dictionaries.
    """
    api_key = os.getenv('GUARDIAN_API_KEY')
    if not api_key:
        logging.error("GUARDIAN_API_KEY not found in environment variables.")
        return []

    logging.info("Fetching data from The Guardian API...")

    params = {
        'api-key': api_key,
        'q': query_string,
        # Removed 'show-fields': 'body' - will scrape content later like RSS feeds
        'page-size': 50  # Max articles per request
    }

    try:
        response = requests.get(source_details['url'], params=params)
        response.raise_for_status()
        data = response.json()

        articles = [
            {
                'title': article.get('webTitle'),
                'content': '',  # Empty initially, will be scraped later
                'source': 'The Guardian',
                'published_date': article.get('webPublicationDate'),
                'link': article.get('webUrl')
            }
            for article in data.get('response', {}).get('results', [])
        ]

        logging.info(f"Successfully fetched {len(articles)} articles from The Guardian.")
        return articles
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data from The Guardian: {e}")
        return []
    except json.JSONDecodeError as e:
        logging.error(f"Error decoding JSON from The Guardian response: {e}")
        return []
