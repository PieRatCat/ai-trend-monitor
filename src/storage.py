import os
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

def get_all_historical_articles(container_name: str) -> List[Dict[str, Any]]:
    """
    Downloads all JSON blobs from a container and combines them into a single list.
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
        blob_count = 0
        for blob in blob_list:
            blob_count += 1
            blob_client = container_client.get_blob_client(blob.name)
            downloader = blob_client.download_blob(max_connections=1, encoding='UTF-8')
            blob_data = json.loads(downloader.readall())
            all_articles.extend(blob_data)
        
        if blob_count > 0:
            logging.info(f"Loaded {len(all_articles)} historical articles from {blob_count} files in '{container_name}'.")
        else:
            logging.info(f"Container '{container_name}' is empty. No historical articles loaded.")
        
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
        today_str = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        blob_name = f"{container_name.replace('-','_')}_{today_str}.json"

        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        
        blob_client = container_client.get_blob_client(blob_name)
        
        try:
            downloader = blob_client.download_blob(max_connections=1, encoding='UTF-8')
            existing_data = json.loads(downloader.readall())
            articles_to_upload = existing_data + articles
        except Exception:
            articles_to_upload = articles

        json_data = json.dumps(articles_to_upload, indent=4, ensure_ascii=False)
        blob_client.upload_blob(json_data.encode('utf-8'), overwrite=True)
        
        logging.info(f"Successfully saved/updated {len(articles_to_upload)} articles to {blob_name} in container {container_name}.")

    except Exception as e:
        logging.error(f"Error saving articles to '{container_name}': {e}")
        