import json
import os
from dotenv import load_dotenv

from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import (
    TextAnalyticsClient,
    RecognizeEntitiesAction,
    ExtractKeyPhrasesAction,
    AnalyzeSentimentAction
)

def run_azure_language_test():
    """
    Connects to Azure AI Language, sends a sample of cleaned data,
    and prints the analysis results based on current Microsoft documentation.
    """
    try:
        # 1. Load credentials
        load_dotenv()
        language_key = os.getenv('LANGUAGE_KEY')
        language_endpoint = os.getenv('LANGUAGE_ENDPOINT')

        if not language_key or not language_endpoint:
            print("❌ ERROR: Make sure LANGUAGE_KEY and LANGUAGE_ENDPOINT are set in your .env file.")
            return

        # 2. Authenticate the client
        credential = AzureKeyCredential(language_key)
        text_analytics_client = TextAnalyticsClient(endpoint=language_endpoint, credential=credential)
        print("✅ Successfully authenticated with Azure AI Language service.")

        # 3. Load and prepare a sample of your cleaned data
        with open('ai-news.json', 'r', encoding='utf-8') as f:
            articles = json.load(f)

        # Use a small, stable sample for testing
        sample_articles = articles[:3]
        
        # Per documentation, prepare a simple list of the text content
        documents_text = [article.get('content', '')[:5120] for article in sample_articles]

        print(f"\n📄 Prepared {len(documents_text)} documents for analysis.")

        # 4. Submit the analysis job to Azure
        poller = text_analytics_client.begin_analyze_actions(
            documents_text, # Pass the simple list of strings
            actions=[
                RecognizeEntitiesAction(),
                ExtractKeyPhrasesAction(),
                AnalyzeSentimentAction(),
            ],
        )

        print("🚀 Analysis job submitted to Azure. Waiting for results...")
        action_results = poller.result()

        # 5. Process and display the results
        print("\n--- ANALYSIS RESULTS ---")
        
        # Iterate through the original articles and the results list together
        for original_article, doc_actions in zip(sample_articles, action_results):
            # Use link or title as a unique identifier for display
            doc_id = original_article.get('link') or original_article.get('title', 'Unknown Article')
            print(f"\n📝 RESULTS FOR DOCUMENT (ID: {doc_id})")
            
            # The result for each document contains a list of action results
            for action_result in doc_actions:
                if action_result.is_error:
                    print(f"  ❌ ERROR for this action: {action_result.error.code} - {action_result.error.message}")
                    continue

                if action_result.kind == "EntityRecognition":
                    print("\n  Named Entities:")
                    for entity in action_result.entities:
                        print(f"    - Entity: '{entity.text}', Category: '{entity.category}', Confidence: {entity.confidence_score:.2f}")
                
                elif action_result.kind == "KeyPhraseExtraction":
                    print("\n  Key Phrases:")
                    print(f"    - {', '.join(action_result.key_phrases)}")

                elif action_result.kind == "SentimentAnalysis":
                    print("\n  Sentiment:")
                    print(f"    - Overall sentiment: {action_result.sentiment}")
                    print(f"    - Scores: Positive={action_result.confidence_scores.positive:.2f}, "
                          f"Neutral={action_result.confidence_scores.neutral:.2f}, "
                          f"Negative={action_result.confidence_scores.negative:.2f}")

    except FileNotFoundError:
        print("\n❌ ERROR: The file 'ai-news.json' was not found. Please ensure it is in the root of your project.")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")

if __name__ == '__main__':
    run_azure_language_test()