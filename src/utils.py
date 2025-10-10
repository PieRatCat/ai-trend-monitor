import logging
from typing import List, Dict, Any

def deduplicate_articles(new_articles: List[Dict[str, Any]], existing_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters out articles that have already been collected.
    """
    existing_links = {article.get('link') for article in existing_articles if article.get('link')}

    unique_new_articles = [
        article for article in new_articles
        if article.get('link') and article.get('link') not in existing_links
    ]

    num_duplicates = len(new_articles) - len(unique_new_articles)
    logging.info(f"Found and removed {num_duplicates} duplicate articles.")

    return unique_new_articles