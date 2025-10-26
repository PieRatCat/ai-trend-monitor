import os
import logging
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Set
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

load_dotenv()

def get_processed_urls(container_name: str = 'analyzed-articles') -> Set[str]:
    """
    Downloads the URL registry file containing all previously processed article URLs.
    
    Args:
        container_name: The container where the URL registry is stored.
        
    Returns:
        A set of URLs that have been previously processed.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return set()

    blob_name = 'processed_urls.json'
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        try:
            downloader = blob_client.download_blob(encoding='UTF-8')
            url_list = json.loads(downloader.readall())
            logging.info(f"Loaded {len(url_list)} processed URLs from registry.")
            return set(url_list)
        except Exception:
            # File doesn't exist yet - first run
            logging.info("No existing URL registry found. Starting fresh.")
            return set()
            
    except Exception as e:
        logging.error(f"Error getting processed URLs: {e}")
        return set()

def update_processed_urls(new_urls: List[str], container_name: str = 'analyzed-articles') -> None:
    """
    Appends newly processed article URLs to the URL registry file.
    
    Args:
        new_urls: List of URLs that have been newly analyzed.
        container_name: The container where the URL registry is stored.
    """
    if not new_urls:
        logging.info("No new URLs to add to registry.")
        return

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return
        
    blob_name = 'processed_urls.json'
    
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Load existing URLs
        try:
            downloader = blob_client.download_blob(encoding='UTF-8')
            existing_urls = json.loads(downloader.readall())
        except Exception:
            existing_urls = []
        
        # Merge with new URLs and remove duplicates
        all_urls = list(set(existing_urls + new_urls))
        
        # Save back to blob (compact JSON for storage efficiency)
        json_data = json.dumps(all_urls, ensure_ascii=False)
        blob_client.upload_blob(json_data.encode('utf-8'), overwrite=True)
        
        logging.info(f"Updated URL registry: added {len(new_urls)} new URLs (total: {len(all_urls)}).")
        
    except Exception as e:
        logging.error(f"Error updating processed URLs: {e}")

def save_articles_to_blob(articles: List[Dict[str, Any]], container_name: str) -> None:
    """
    Saves a list of new articles to a timestamped JSON blob.
    Each pipeline run creates a separate file with date and time stamp.
    """
    if not articles:
        logging.info(f"No new articles to save to '{container_name}'.")
        return

    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return
        
    try:
        # Include date and time in filename
        timestamp_str = datetime.now(timezone.utc).strftime('%Y-%m-%d_%H-%M-%S')
        blob_name = f"{container_name.replace('-','_')}_{timestamp_str}.json"

        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        blob_client = container_client.get_blob_client(blob_name)
        
        # Save articles directly (compact JSON for storage efficiency)
        json_data = json.dumps(articles, ensure_ascii=False)
        blob_client.upload_blob(json_data.encode('utf-8'), overwrite=True)
        
        logging.info(f"Successfully saved {len(articles)} articles to {blob_name} in container {container_name}.")

    except Exception as e:
        logging.error(f"Error saving articles to '{container_name}': {e}")

def save_report_to_blob(report_content: str, filename: str, container_name: str = 'weekly-reports') -> str:
    """
    Saves a weekly report to Azure Blob Storage.
    
    Args:
        report_content: The markdown content of the report.
        filename: The filename (e.g., 'weekly_report_2025-10-26.md').
        container_name: The container where reports are stored.
        
    Returns:
        The full blob path (container/filename).
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("Azure connection string not found.")
        return ""
        
    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        container_client = blob_service_client.get_container_client(container_name)
        
        # Create container if it doesn't exist
        try:
            container_client.create_container()
            logging.info(f"Created container '{container_name}'")
        except Exception:
            pass  # Container already exists
        
        blob_client = container_client.get_blob_client(filename)
        
        # Upload report content
        blob_client.upload_blob(report_content.encode('utf-8'), overwrite=True)
        
        blob_path = f"{container_name}/{filename}"
        logging.info(f"Successfully saved report to {blob_path}")
        
        return blob_path

    except Exception as e:
        logging.error(f"Error saving report to '{container_name}': {e}")
        return ""