# src/language_analyzer.py

import os
import logging
from typing import List, Dict, Any
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import (
    TextAnalyticsClient,
    RecognizeEntitiesAction,
    ExtractKeyPhrasesAction,
    AnalyzeSentimentAction
)

def analyze_articles(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Analyzes a list of articles using Azure AI Language service.

    Args:
        articles: A list of article dictionaries.

    Returns:
        The same list of articles, with 'sentiment', 'key_phrases',
        and 'entities' keys added to each dictionary.
    """
    load_dotenv()
    language_key = os.getenv('LANGUAGE_KEY')
    language_endpoint = os.getenv('LANGUAGE_ENDPOINT')

    if not all([language_key, language_endpoint]):
        logging.error("Azure Language credentials not found. Skipping analysis.")
        return articles

    credential = AzureKeyCredential(language_key)
    text_analytics_client = TextAnalyticsClient(endpoint=language_endpoint, credential=credential)

    # Prepare the documents for Azure
    documents_text = [article.get('content', '')[:5120] for article in articles]
    
    # Run the analysis
    try:
        poller = text_analytics_client.begin_analyze_actions(
            documents_text,
            actions=[
                RecognizeEntitiesAction(),
                ExtractKeyPhrasesAction(),
                AnalyzeSentimentAction(),
            ],
        )
        action_results = poller.result()

        # Process and append the results back to the original articles
        for original_article, doc_actions in zip(articles, action_results):
            # Initialize results fields
            original_article['sentiment'] = {}
            original_article['key_phrases'] = []
            original_article['entities'] = []

            for action_result in doc_actions:
                if action_result.is_error:
                    logging.warning(f"Error analyzing document {original_article.get('link')}: {action_result.error.message}")
                    continue

                if action_result.kind == "SentimentAnalysis":
                    original_article['sentiment'] = {
                        'overall': action_result.sentiment,
                        'positive_score': action_result.confidence_scores.positive,
                        'neutral_score': action_result.confidence_scores.neutral,
                        'negative_score': action_result.confidence_scores.negative
                    }
                
                elif action_result.kind == "KeyPhraseExtraction":
                    original_article['key_phrases'] = action_result.key_phrases

                elif action_result.kind == "EntityRecognition":
                    original_article['entities'] = [
                        {'text': entity.text, 'category': entity.category, 'confidence': entity.confidence_score}
                        for entity in action_result.entities
                    ]
        
        logging.info(f"Successfully analyzed {len(articles)} articles.")
        return articles

    except Exception as e:
        logging.error(f"An error occurred during Azure AI Language analysis: {e}")
        return articles # Return original articles on failure