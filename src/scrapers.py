from bs4 import BeautifulSoup
import requests
import logging
import time
from urllib.parse import urlparse
from typing import Dict, List

# Site-specific selectors
SCRAPERS: Dict[str, Dict[str, str]] = {
    # Existing sources
    'venturebeat.com': {'selector': 'div.article-body'},
    'gizmodo.com': {'selector': 'div.entry-content'},
    'techcrunch.com': {'selector': 'div.entry-content'},
    'arstechnica.com': {'selector': 'div.post-content'},
    'theguardian.com': {'selector': 'div.article-body-commercial-selector'},
    'www.theguardian.com': {'selector': 'div.article-body-commercial-selector'},
    
    # New event & product launch sources
    'www.theverge.com': {'selector': 'div.duet--article--article-body-component'},
    'theverge.com': {'selector': 'div.duet--article--article-body-component'},
    'www.anandtech.com': {'selector': 'div.articleContent'},
    'anandtech.com': {'selector': 'div.articleContent'},
    'forums.anandtech.com': {'selector': 'div.articleContent'},  # AnandTech RSS redirects here
    'www.tomsguide.com': {'selector': 'div#article-body'},
    'tomsguide.com': {'selector': 'div#article-body'},
    'www.infoworld.com': {'selector': 'div.article-body'},
    'infoworld.com': {'selector': 'div.article-body'},
    'spectrum.ieee.org': {'selector': 'div.article-content'},
    
    # European & Swedish sources
    'go.theregister.com': {'selector': 'div#body'},
    'www.theregister.com': {'selector': 'div#body'},
    'theregister.com': {'selector': 'div#body'},
    'sifted.eu': {'selector': 'div.entry-content'},
    'www.sifted.eu': {'selector': 'div.entry-content'},
    'www.breakit.se': {'selector': 'div.article-body'},
    'breakit.se': {'selector': 'div.article-body'},
    'www.di.se': {'selector': 'article.article'},
    'di.se': {'selector': 'article.article'},
    'arcticstartup.com': {'selector': 'div.entry-content'},
    'www.arcticstartup.com': {'selector': 'div.entry-content'},
}

# Generic selectors to try when there is no site-specific scraper
FALLBACK_SELECTORS: List[str] = [
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
    replacements = {
        'â€™': "'",
        'â€"': "—",
        'â€œ': '"',
        'â€': '"',
    }
    for bad_char, good_char in replacements.items():
        text = text.replace(bad_char, good_char)
    return text

def get_full_content(url: str) -> str:
    """
    Scrape full article text for a URL with a robust retry mechanism.
    """
    source_domain = urlparse(url).netloc
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/125.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Cache-Control': 'max-age=0'
    }
    
    response = None
    # --- Start of retry logic ---
    for attempt in range(4): # Try up to 4 times
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            break # Success, exit the loop
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** attempt # Exponential backoff: 1, 2, 4, 8 seconds
                logging.warning(
                    "Rate limited for %s. Retrying in %s seconds...", url, wait_time
                )
                time.sleep(wait_time)
            else:
                logging.error("HTTP Error fetching %s: %s", url, e)
                return "" # For other HTTP errors, fail immediately
        except requests.exceptions.RequestException as e:
            logging.error("Error fetching %s: %s", url, e)
            return "" # For other network errors, fail immediately
    
    if response is None:
        logging.error("Failed to fetch %s after multiple retries.", url)
        return ""
    # --- End of new retry logic ---

    response.encoding = response.apparent_encoding or 'utf-8'
    
    # Limit HTML size to prevent parsing issues with huge pages
    max_html_size = 5 * 1024 * 1024  # 5 MB limit
    if len(response.content) > max_html_size:
        logging.warning(
            f"HTML too large for {url} ({len(response.content)} bytes). Skipping scrape."
        )
        return ""
    
    soup = BeautifulSoup(response.text, 'html.parser')    
    
    # Create a prioritized list of selectors to try
    selectors_to_try = []
    site_specific_selector = SCRAPERS.get(source_domain, {}).get('selector')
    
    if site_specific_selector:
        selectors_to_try.append(site_specific_selector)
    
    # Add fallbacks, ensuring no duplicates
    for fs in FALLBACK_SELECTORS:
        if fs not in selectors_to_try:
            selectors_to_try.append(fs)
            
    content_text = ""
    for selector in selectors_to_try:
        element = soup.select_one(selector)
        if element:
            content_text = element.get_text(separator=' ', strip=True)
            if content_text:
                logging.info("Successfully extracted content for %s using selector '%s'", url, selector)
                break # Stop after the first success

    if not content_text:
        logging.warning("Could not extract article content for %s", url)
        return ""

    return fix_encoding_issues(content_text)