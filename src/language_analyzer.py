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
    Analyzes a list of articles in batches using Azure AI Language service.
    """
    load_dotenv()
    language_key = os.getenv('LANGUAGE_KEY')
    language_endpoint = os.getenv('LANGUAGE_ENDPOINT')

    if not all([language_key, language_endpoint]):
        logging.error("Azure Language credentials not found. Skipping analysis.")
        return articles

    credential = AzureKeyCredential(language_key)
    text_analytics_client = TextAnalyticsClient(endpoint=language_endpoint, credential=credential)

    analyzed_articles_list = []
    
    # Process the articles in batches of 25.
    batch_size = 25
    max_chars = 5120  # Azure AI Language limit
    
    for i in range(0, len(articles), batch_size):
        batch = articles[i:i + batch_size]
        
        # Prepare documents and log truncations
        documents_text = []
        for article in batch:
            content = article.get('content', '')
            if len(content) > max_chars:
                logging.warning(
                    f"Truncating article '{article.get('title', 'Unknown')[:50]}...' "
                    f"from {len(content)} to {max_chars} characters for Azure AI analysis."
                )
            documents_text.append(content[:max_chars])
        
        logging.info(f"Analyzing batch of {len(batch)} articles...")

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

            for original_article, doc_actions in zip(batch, action_results):
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
                
                analyzed_articles_list.append(original_article)

        except Exception as e:
            logging.error(f"An error occurred during Azure AI Language analysis batch: {e}")
            # Add original articles to results even if analysis fails for this batch
            analyzed_articles_list.extend(batch)
            
    return analyzed_articles_list