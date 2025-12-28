# crawler/crawler.py
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient
from datetime import datetime
import time
import re
from urllib.parse import urljoin

from config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION, STATE_COLLECTION
from utils import clean_wikipedia_text

class WikipediaCrawler:
    def __init__(self, base_url, start_category, max_articles=30000):
        self.base_url = base_url
        self.start_category_url = urljoin(base_url, start_category)
        self.max_articles = max_articles
        
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.articles_collection = self.db[ARTICLES_COLLECTION]
        self.state_collection = self.db[STATE_COLLECTION]
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'InfSearchBot/1.0 (https://github.com/your_repo; your_email@example.com)'
        })
        
    def _get_state(self):
        return self.state_collection.find_one({'_id': 'crawler_state'}) or {}

    def _save_state(self, state):
        self.state_collection.update_one({'_id': 'crawler_state'}, {'$set': state}, upsert=True)

    def crawl(self):
        state = self._get_state()
        
        to_visit_categories = state.get('to_visit_categories', [self.start_category_url])
        visited_categories = set(state.get('visited_categories', []))
        visited_articles = set(state.get('visited_articles', []))
        article_count = self.articles_collection.count_documents({})

        while to_visit_categories and article_count < self.max_articles:
            category_url = to_visit_categories.pop(0)
            if category_url in visited_categories:
                continue

            print(f"Crawling category: {category_url}")
            
            try:
                response = self.session.get(category_url)
                response.raise_for_status()
                time.sleep(1) # Delay between requests
            except requests.RequestException as e:
                print(f"Error fetching category {category_url}: {e}")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find articles in the current category
            for link in soup.select('#mw-pages a'):
                article_url = urljoin(self.base_url, link['href'])
                if article_url not in visited_articles and self._is_article(article_url):
                    if self.articles_collection.find_one({'url': article_url}):
                        print(f"Skipping already downloaded article: {article_url}")
                        visited_articles.add(article_url)
                        continue
                        
                    self._process_article(article_url)
                    visited_articles.add(article_url)
                    article_count += 1
                    if article_count >= self.max_articles:
                        break

            # Find subcategories
            for link in soup.select('#mw-subcategories a'):
                if link.has_attr('href'):
                    subcategory_url = urljoin(self.base_url, link['href'])
                    if subcategory_url not in visited_categories and subcategory_url not in to_visit_categories:
                        to_visit_categories.append(subcategory_url)

            visited_categories.add(category_url)
            
            # Save state periodically
            self._save_state({
                'to_visit_categories': to_visit_categories,
                'visited_categories': list(visited_categories),
                'visited_articles': list(visited_articles)
            })

        print("Crawling finished.")

    def _is_article(self, url):
        # Basic check to filter out special Wikipedia pages
        return re.match(r'.*/wiki/[^:]+$', url)

    def _process_article(self, url):
        print(f"Processing article: {url}")
        try:
            response = self.session.get(url)
            response.raise_for_status()
            time.sleep(1) # Delay between requests
        except requests.RequestException as e:
            print(f"Error fetching article {url}: {e}")
            return

        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.find('h1', {'id': 'firstHeading'}).text
        text = clean_wikipedia_text(soup)

        if not text:
            print(f"Could not extract text from {url}")
            return

        word_count = len(text.split())
        char_count = len(text)
        
        article_doc = {
            "article_id": self.articles_collection.count_documents({}) + 1,
            "title": title,
            "url": url,
            "text": text,
            "tokens": [],
            "stems": [],
            "metadata": {
                "word_count": word_count,
                "char_count": char_count,
                "download_date": datetime.utcnow()
            }
        }
        
        self.articles_collection.insert_one(article_doc)
        print(f"Saved article: {title}")

if __name__ == '__main__':
    # Example usage:
    start_category_path = '/wiki/Категория:Наука'
    crawler = WikipediaCrawler('https://ru.wikipedia.org', start_category_path, max_articles=15000) # Start with a smaller number for testing
    crawler.crawl()

