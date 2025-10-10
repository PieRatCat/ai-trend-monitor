import re
import unicodedata
from bs4 import BeautifulSoup

def clean_article_content(html_content: str) -> str:
    """
    Cleans raw HTML, normalizes Unicode, and removes extra whitespace.
    
    1. Normalizes Unicode to handle different character encodings consistently.
    2. Parses and removes all HTML tags using BeautifulSoup.
    3. Normalizes whitespace, removing extra newlines and spaces.
    
    Args:
        html_content: The raw string content of the article.
        
    Returns:
        A clean, plain-text string ready for NLP analysis.
    """
    if not html_content:
        return ""
      
    text = unicodedata.normalize('NFC', html_content)
    
    soup = BeautifulSoup(text, "html.parser")
    text = soup.get_text()
    
    # Replace multiple whitespace characters with a single space.
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text