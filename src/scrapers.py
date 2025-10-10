from bs4 import BeautifulSoup
import requests
import logging
import time
from urllib.parse import urlparse
from typing import Dict

# Site-specific selectors
SCRAPERS: Dict[str, Dict[str, str]] = {
    'venturebeat.com': {'selector': 'div.article-body'},
    'gizmodo.com': {'selector': 'div.entry-content'},
    'techcrunch.com': {'selector': 'div.entry-content'},
    'arstechnica.com': {'selector': 'div.post-content'},
}

# Generic selectors to try when there is no site-specific scraper
FALLBACK_SELECTORS = [
    'article',
    'main',
    'div.article-body',
    'div.entry-content',
    'div.post-content',
    'div[itemprop="articleBody"]',
]

def fix_encoding_issues(text: str) -> str:
    """
    A failsafe function to clean up common UTF-8 vs. Windows-1252 mojibake.
    """
    # Fix common garbled characters resulting from encoding mismatches.
    # This is a targeted fix for the issue seen with Gizmodo.
    replacements = {
        'â€™': "'",  # Replaces the garbled apostrophe
        'â€"': "—",  # Replaces the garbled em dash
        'â€œ': '"',  # Replaces garbled opening quote
        'â€': '"',  # Replaces garbled closing quote
    }
    for bad_char, good_char in replacements.items():
        text = text.replace(bad_char, good_char)
    return text

def get_full_content(url: str) -> str:
    """Scrape full article text for a URL.

    Behavior:
    - If a site-specific selector exists in `SCRAPERS`, use it.
    - Otherwise, try a set of sensible fallback selectors.
    - Explicitly decodes response text to handle encoding issues.
    - Returns empty string on failure.
    """
    source_domain = urlparse(url).netloc
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        )
    }
    time.sleep(1)

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # --> ENHANCED ENCODING HANDLING <--
        # Let requests detect the encoding, but fall back to UTF-8 if it's uncertain.
        response.encoding = response.apparent_encoding or 'utf-8'
        
        # Use response.text which is now properly decoded.
        soup = BeautifulSoup(response.text, 'html.parser')

    except requests.exceptions.RequestException as e:
        logging.error("Error fetching %s: %s", url, e)
        return ""

    content_text = ""
    # Try site-specific selector first
    selector = None
    if source_domain in SCRAPERS:
        selector = SCRAPERS[source_domain].get('selector')

    if selector:
        element = soup.select_one(selector)
        if element:
            content_text = element.get_text(separator=' ', strip=True)
        else:
            logging.debug(
                "Site-specific selector did not match for %s (selector=%s)", url, selector
            )

    # Fallback: try generic selectors if the first attempt failed
    if not content_text:
        for sel in FALLBACK_SELECTORS:
            element = soup.select_one(sel)
            if element:
                logging.info("Using fallback selector '%s' for %s", sel, source_domain)
                content_text = element.get_text(separator=' ', strip=True)
                break # Stop after the first successful fallback

    if not content_text:
        logging.warning("Could not extract article content for %s (domain=%s)", url, source_domain)
        return ""

    # --> ADDED: FINAL CLEANUP STEP <--
    # Apply the encoding fix as a final polish before returning.
    return fix_encoding_issues(content_text)