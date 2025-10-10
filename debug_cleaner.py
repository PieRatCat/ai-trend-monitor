import json
import os

# Ensure this script can find your source modules
from src.data_cleaner import clean_article_content

def test_local_cleaning():
    """
    Loads a local JSON file, cleans the content of each article,
    and saves the result to a new file for inspection.
    """
    input_filename = 'ai-news.json'
    output_filename = 'ai-news-cleaned-4.json'

    # Check if the input file exists
    if not os.path.exists(input_filename):
        print(f"Error: The file '{input_filename}' was not found in the project root.")
        print("Please make sure you have run the pipeline and saved the file locally first.")
        return

    # Load the raw data
    with open(input_filename, 'r', encoding='utf-8') as f:
        articles = json.load(f)

    if not articles:
        print("The input file is empty. Nothing to clean.")
        return

    print(f"Loaded {len(articles)} articles from '{input_filename}'. Starting cleaning process...")

    # Clean each article's content
    for article in articles:
        raw_content = article.get('content', '')
        if raw_content:
            cleaned_content = clean_article_content(raw_content)
            article['content'] = cleaned_content

    # --- Verification Step ---
    # Print the before and after for the first article to show the difference
    print("\n--- Verifying Cleaning on First Article ---")
    print("\nOriginal Content (first 500 chars):")
    print(json.load(open(input_filename, 'r', encoding='utf-8'))[0].get('content', '')[:500])
    
    print("\nCleaned Content (first 500 chars):")
    print(articles[0].get('content', '')[:500])
    print("----------------------------------------")

    # Save the cleaned data to a new file
    with open(output_filename, 'w', encoding='utf-8') as f:
        json.dump(articles, f, indent=4, ensure_ascii=False)

    print(f"\nCleaning complete. The cleaned data has been saved to '{output_filename}'.")
    print("Please inspect this file to confirm the results.")

if __name__ == '__main__':
    test_local_cleaning()