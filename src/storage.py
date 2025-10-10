import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from azure.storage.blob import BlobServiceClient, BlobClient
from azure.core.exceptions import ResourceNotFoundError
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_existing_articles(container_name: str, blob_name: str) -> List[Dict[str, Any]]:
    """
    Downloads and reads a JSON blob from Azure Blob Storage.
    Returns an empty list if the blob does not exist.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')
    if not connect_str:
        logging.error("AZURE_STORAGE_CONNECTION_STRING not found in environment variables.")
        return []

    try:
        blob_client = BlobClient.from_connection_string(connect_str, container_name, blob_name)
        if blob_client.exists():
            blob_data = blob_client.download_blob().readall()
            logging.info(f"Successfully downloaded existing data from {blob_name}.")
            # Decode the data from bytes to a string and then load as JSON
            return json.loads(blob_data.decode('utf-8'))
        else:
            logging.info(f"Blob {blob_name} does not exist. Starting with an empty list of articles.")
            return []
    except ResourceNotFoundError:
        logging.warning(f"Container '{container_name}' or blob '{blob_name}' does not exist.")
        return []
    except Exception as e:
        logging.error(f"Error getting existing articles from Blob Storage: {e}")
        return []

def save_to_blob_storage(articles: List[Dict[str, Any]], container_name: str, blob_name: str) -> None:
    """
    Saves a list of articles as a JSON file to Azure Blob Storage.
    """
    connect_str = os.getenv('AZURE_STORAGE_CONNECTION_STRING')

    if not connect_str:
        logging.error("AZURE_STORAGE_CONNECTION_STRING not found in environment variables.")
        return

    try:
        blob_service_client = BlobServiceClient.from_connection_string(connect_str)
        
        json_data = json.dumps(articles, indent=4)
        
        blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)
        blob_client.upload_blob(json_data, overwrite=True)

        logging.info(f"Successfully uploaded data to {blob_name} in container {container_name}.")
    
    except Exception as e:
        logging.error(f"An error occurred during upload to Azure Blob Storage: {e}")