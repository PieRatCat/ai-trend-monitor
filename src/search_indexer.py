"""
Azure AI Search indexing functions for the pipeline.
Handles uploading newly analyzed articles to the search index.
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
import hashlib

load_dotenv()

def generate_document_id(url: str) -> str:
    """
    Generate a unique document ID from the article URL.
    
    Args:
        url: The article URL.
        
    Returns:
        A valid Azure Search document ID (MD5 hash).
    """
    return hashlib.md5(url.encode()).hexdigest()

def transform_article_for_search(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Transform an analyzed article into the search index schema.
    
    Args:
        article: The analyzed article.
        
    Returns:
        Document formatted for Azure Search index.
    """
    # Extract sentiment data
    sentiment = article.get('sentiment', {})
    sentiment_overall = sentiment.get('overall', 'neutral')
    sentiment_positive = sentiment.get('positive_score', 0.0)
    sentiment_neutral = sentiment.get('neutral_score', 0.0)
    sentiment_negative = sentiment.get('negative_score', 0.0)
    
    # Extract key phrases - ensure it's a list of strings
    key_phrases = article.get('key_phrases', [])
    if not isinstance(key_phrases, list):
        key_phrases = []
    # Filter out any non-string values and limit length
    key_phrases = [str(phrase)[:500] for phrase in key_phrases if phrase][:100]
    
    # Extract entities and their categories
    entities = article.get('entities', [])
    if not isinstance(entities, list):
        entities = []
    entities_json = json.dumps(entities)  # Store as JSON string
    
    # Get unique entity categories for filtering
    entity_categories = list(set([
        str(entity.get('category', 'Unknown'))[:100]
        for entity in entities 
        if entity.get('category')
    ]))[:50]  # Limit to 50 unique categories
    
    # Create search document
    search_doc = {
        'id': generate_document_id(article['link']),
        'title': article.get('title', ''),
        'content': article.get('content', ''),
        'link': article.get('link', ''),
        'source': article.get('source', ''),
        'published_date': article.get('published_date', ''),
        'sentiment_overall': sentiment_overall,
        'sentiment_positive_score': float(sentiment_positive),
        'sentiment_neutral_score': float(sentiment_neutral),
        'sentiment_negative_score': float(sentiment_negative),
        'key_phrases': key_phrases,
        'entities': entities_json,
        'entity_categories': entity_categories,
        'indexed_at': datetime.now(timezone.utc).isoformat()
    }
    
    return search_doc

def index_articles(articles: List[Dict[str, Any]], index_name: str = "ai-articles-index") -> int:
    """
    Index newly analyzed articles in Azure AI Search.
    
    Args:
        articles: List of analyzed articles to index.
        index_name: Name of the search index.
        
    Returns:
        Number of articles successfully indexed.
    """
    if not articles:
        logging.info("No articles to index.")
        return 0
    
    # Get credentials
    search_endpoint = os.getenv('SEARCH_ENDPOINT')
    search_key = os.getenv('SEARCH_KEY')
    
    if not search_endpoint or not search_key:
        logging.warning("SEARCH_ENDPOINT and SEARCH_KEY not found. Skipping indexing.")
        return 0
    
    try:
        # Create search client
        credential = AzureKeyCredential(search_key)
        search_client = SearchClient(
            endpoint=search_endpoint,
            index_name=index_name,
            credential=credential
        )
        
        # Transform articles for search index
        search_documents = []
        for article in articles:
            try:
                search_doc = transform_article_for_search(article)
                search_documents.append(search_doc)
            except Exception as e:
                logging.warning(f"Failed to transform article '{article.get('title', 'Unknown')}': {e}")
        
        if not search_documents:
            logging.warning("No documents to index after transformation.")
            return 0
        
        # Upload to search index (merge_or_upload handles duplicates gracefully)
        logging.info(f"Indexing {len(search_documents)} articles to Azure AI Search...")
        result = search_client.merge_or_upload_documents(documents=search_documents)
        
        # Count successes
        succeeded = sum(1 for r in result if r.succeeded)
        failed = len(search_documents) - succeeded
        
        if failed > 0:
            logging.warning(f"  {failed} documents failed to index")
        
        logging.info(f"Successfully indexed {succeeded}/{len(search_documents)} articles")
        return succeeded
        
    except Exception as e:
        logging.error(f"Error indexing articles: {e}")
        return 0
