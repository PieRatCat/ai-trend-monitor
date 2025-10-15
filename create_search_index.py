"""
Creates an Azure AI Search index for AI-analyzed news articles.
The index is optimized for semantic search with fields for content, sentiment, entities, and key phrases.
"""

import os
import logging
from dotenv import load_dotenv
from azure.core.credentials import AzureKeyCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    SimpleField,
    SearchableField,
    ComplexField,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile
)

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_search_index(index_name: str = "ai-articles-index") -> None:
    """
    Creates a search index optimized for AI-analyzed news articles.
    
    Args:
        index_name: Name of the search index to create.
    """
    
    # Get credentials from environment
    search_endpoint = os.getenv('SEARCH_ENDPOINT')
    search_key = os.getenv('SEARCH_KEY')
    
    if not search_endpoint or not search_key:
        logging.error("SEARCH_ENDPOINT and SEARCH_KEY must be set in .env file")
        return
    
    # Create search index client
    credential = AzureKeyCredential(search_key)
    index_client = SearchIndexClient(endpoint=search_endpoint, credential=credential)
    
    # Define the index schema
    fields = [
        # Primary key - using link URL as unique identifier
        SimpleField(
            name="id",
            type=SearchFieldDataType.String,
            key=True,
            filterable=True
        ),
        
        # Article metadata
        SearchableField(
            name="title",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            sortable=True,
            analyzer_name="en.microsoft"
        ),
        
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            searchable=True,
            analyzer_name="en.microsoft"
        ),
        
        SimpleField(
            name="link",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),
        
        SearchableField(
            name="source",
            type=SearchFieldDataType.String,
            searchable=True,
            filterable=True,
            facetable=True
        ),
        
        SimpleField(
            name="published_date",
            type=SearchFieldDataType.String,
            filterable=True,
            sortable=True
        ),
        
        # Sentiment analysis fields
        SimpleField(
            name="sentiment_overall",
            type=SearchFieldDataType.String,
            filterable=True,
            facetable=True
        ),
        
        SimpleField(
            name="sentiment_positive_score",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        ),
        
        SimpleField(
            name="sentiment_neutral_score",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        ),
        
        SimpleField(
            name="sentiment_negative_score",
            type=SearchFieldDataType.Double,
            filterable=True,
            sortable=True
        ),
        
        # Key phrases for topic discovery
        SearchableField(
            name="key_phrases",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            searchable=True,
            filterable=True,
            facetable=True
        ),
        
        # Named entities - stored as JSON strings for complex structure
        SearchableField(
            name="entities",
            type=SearchFieldDataType.String,
            searchable=True
        ),
        
        # Entity categories for filtering
        SearchableField(
            name="entity_categories",
            type=SearchFieldDataType.Collection(SearchFieldDataType.String),
            filterable=True,
            facetable=True
        ),
        
        # Timestamp for tracking when indexed
        SimpleField(
            name="indexed_at",
            type=SearchFieldDataType.DateTimeOffset,
            filterable=True,
            sortable=True
        )
    ]
    
    # Configure semantic search for better relevance
    semantic_config = SemanticConfiguration(
        name="ai-articles-semantic-config",
        prioritized_fields=SemanticPrioritizedFields(
            title_field=SemanticField(field_name="title"),
            content_fields=[SemanticField(field_name="content")],
            keywords_fields=[
                SemanticField(field_name="key_phrases"),
                SemanticField(field_name="source")
            ]
        )
    )
    
    semantic_search = SemanticSearch(configurations=[semantic_config])
    
    # Create the index
    index = SearchIndex(
        name=index_name,
        fields=fields,
        semantic_search=semantic_search
    )
    
    try:
        # Delete existing index if it exists
        try:
            index_client.delete_index(index_name)
            logging.info(f"Deleted existing index '{index_name}'")
        except Exception:
            pass
        
        # Create the new index
        result = index_client.create_index(index)
        logging.info(f"✅ Successfully created search index: {result.name}")
        logging.info(f"   - Total fields: {len(fields)}")
        logging.info(f"   - Searchable fields: title, content, source, key_phrases, entities")
        logging.info(f"   - Filterable fields: source, sentiment, published_date, entity_categories")
        logging.info(f"   - Semantic search: Enabled")
        logging.info(f"\nIndex endpoint: {search_endpoint}/indexes/{index_name}")
        
    except Exception as e:
        logging.error(f"Error creating search index: {e}")
        raise

if __name__ == "__main__":
    create_search_index()
