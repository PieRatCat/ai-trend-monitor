# src/data_cleaner.py

import re
import unicodedata
import html  # Import the html library
from bs4 import BeautifulSoup

def clean_article_content(html_content: str) -> str:
    """
    Cleans raw HTML, unescapes HTML entities, normalizes Unicode,
    and removes extra whitespace.
    
    1. Unescapes HTML entities (e.g., '&amp;' -> '&').
    2. Normalizes Unicode to handle different character encodings.
    3. Parses and removes all HTML tags using BeautifulSoup.
    4. Normalizes whitespace to a single space.
    
    Args:
        html_content: The raw string content of the article.
        
    Returns:
        A clean, plain-text string ready for NLP analysis.
    """
    if not html_content:
        return ""
    
    # Unescape HTML character entities (e.g., &amp;, &lt;).
    text = html.unescape(html_content)
    
    # Normalize unicode characters to a standard form.
    text = unicodedata.normalize('NFC', text)
    
    # Use BeautifulSoup to strip HTML tags.
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    
    # Replace multiple whitespace characters with a single space.
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text