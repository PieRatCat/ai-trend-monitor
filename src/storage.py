# src/storage.py

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

def get_all_historical_articles(container_name: str) -> List[Dict[str, Any]]:
    """
    Downloads all JSON blobs from a container and combines them into a single list.
    This is used to build a complete history for deduplication.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return []

    all_articles = []
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        
        blob_list = container_client.list_blobs()
        for blob in blob_list:
            blob_client = container_client.get_blob_client(blob.name)
            downloader = blob_client.download_blob(max_connections=1, encoding='UTF-8')
            blob_data = json.loads(downloader.readall())
            all_articles.extend(blob_data)
        
        logging.info(f"Loaded {len(all_articles)} historical articles from {len(list(blob_list))} files in '{container_name}'.")
        return all_articles
    except Exception as e:
        logging.error(f"Error getting historical articles from '{container_name}': {e}")
        return []

def save_articles_to_blob(articles: List[Dict[str, Any]], container_name: str) -> None:
    """
    Saves a list of new articles to a new, timestamped JSON blob.
    """
    if not articles:
        logging.info(f"No new articles to save to '{container_name}'.")
        return

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return
        
    try:
        # Create a unique blob name for each day's run
        today_str = datetime.utcnow().strftime('%Y-%m-%d')
        blob_name = f"{container_name}_{today_str}.json"

        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        
        # We may be adding to today's file, so download existing data first
        try:
            downloader = blob_client.download_blob(max_connections=1, encoding='UTF-8')
            existing_data = json.loads(downloader.readall())
            articles = existing_data + articles
        except Exception:
            # Blob doesn't exist yet, which is fine.
            existing_data = []

        json_data = json.dumps(articles, indent=4, ensure_ascii=False)
        blob_client.upload_blob(json_data.encode('utf-8'), overwrite=True)
        
        logging.info(f"Successfully saved/updated {len(articles)} articles to {blob_name} in container {container_name}.")

    except Exception as e:
        logging.error(f"Error saving articles to '{container_name}': {e}")