# crawler/utils.py
import re
from bs4 import BeautifulSoup, NavigableString, Tag

def clean_wikipedia_text(soup: BeautifulSoup) -> str:
    """
    Cleans the HTML content of a Wikipedia article to extract plain text.
    """
    # Remove tables, navigation boxes, and other non-content elements
    for element in soup.find_all(['table', 'div.navbox', 'div.reflist', 'div.thumb', 'div.metadata', 'div.catlinks']):
        element.decompose()
    
    # Get the main content div
    content_div = soup.find('div', {'id': 'mw-content-text'})
    if not content_div:
        return ""

    text_parts = []
    for element in content_div.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li']):
        text_parts.append(element.get_text())

    full_text = "\n".join(text_parts)
    
    # Remove citation brackets like [1], [2], etc.
    full_text = re.sub(r'\[\d+\]', '', full_text)
    # Remove edit links
    full_text = re.sub(r'\[править \| править код\]', '', full_text)
    # Normalize whitespace
    full_text = re.sub(r'\s+', ' ', full_text).strip()
    
    return full_text

