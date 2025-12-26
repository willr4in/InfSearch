import hashlib
import logging
import os
import time
import random
from datetime import datetime

import feedparser
import requests
from bs4 import BeautifulSoup
from sqlalchemy import (Column, DateTime, Integer, String, Text, UniqueConstraint,
                        create_engine, func)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

Base = declarative_base()
logger = logging.getLogger("news_crawler")
logging.basicConfig(level=logging.INFO)

# small list of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0 Safari/537.36',
    'infsearch-crawler/1.0 (+https://example.org)'
]


class Source(Base):
    __tablename__ = 'sources'
    id = Column(Integer, primary_key=True)
    name = Column(Text)
    url = Column(Text)
    rss_feed = Column(Text)
    last_crawled = Column(DateTime)


class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True)
    title = Column(Text)
    content = Column(Text)
    content_hash = Column(String(64), unique=True, index=True)
    source_url = Column(Text, unique=True, index=True)
    publish_date = Column(DateTime)
    category = Column(Text)
    word_count = Column(Integer)
    source_id = Column(Integer)


class Token(Base):
    __tablename__ = 'tokens'
    id = Column(Integer, primary_key=True)
    token = Column(Text)
    stem = Column(Text)
    frequency = Column(Integer, default=0)


class NewsCrawler:
    def __init__(self, db_url=None, user_agent=None, timeout=15, max_retries=3):
        db_url = db_url or os.environ.get('DATABASE_URL') or \
                 f"postgresql+psycopg2://infsearch:infsearch@localhost:15432/infsearch"
        self.engine = create_engine(db_url, pool_pre_ping=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_retries = max_retries

        # prepare session with retries
        self.session = requests.Session()
        retries = Retry(total=max_retries, backoff_factor=1,
                        status_forcelist=[429, 500, 502, 503, 504],
                        allowed_methods=["HEAD", "GET", "OPTIONS"])
        adapter = HTTPAdapter(max_retries=retries)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)

    def fetch_rss(self, rss_url):
        try:
            feed = feedparser.parse(rss_url)
            return feed.entries
        except Exception as e:
            logger.exception("Failed to parse RSS %s: %s", rss_url, e)
            return []

    def fetch_article(self, url):
        # special-case arXiv abstracts (they often contain full text summary)
        if 'arxiv.org' in url and '/abs/' in url:
            try:
                headers = {'User-Agent': self.user_agent or random.choice(USER_AGENTS)}
                r = self.session.get(url, timeout=self.timeout, headers=headers)
                if r.status_code != 200:
                    return None, None
                soup = BeautifulSoup(r.content, 'html.parser')
                title = ''
                h1 = soup.find('h1', class_='title')
                if h1:
                    title = h1.get_text(strip=True).replace('Title:', '').strip()
                abstract = soup.find('blockquote', class_='abstract')
                content = abstract.get_text(strip=True).replace('Abstract:', '').strip() if abstract else ''
                return title, content
            except Exception as e:
                logger.warning('arXiv fetch failed for %s: %s', url, e)
                return None, None

        # generic fetching logic with retries and UA rotation
        headers = {
            'User-Agent': self.user_agent or random.choice(USER_AGENTS),
            'Accept-Language': 'en-US,en;q=0.9',
        }
        attempt = 0
        while attempt < max(1, self.max_retries):
            try:
                r = self.session.get(url, headers=headers, timeout=self.timeout)
                if r.status_code == 403:
                    # try alternative UA and simple referer header
                    headers['User-Agent'] = random.choice(USER_AGENTS)
                    headers['Referer'] = 'https://google.com'
                    logger.warning('403 returned for %s, retrying with alternate headers', url)
                    attempt += 1
                    time.sleep(1 + attempt)
                    continue
                if r.status_code != 200:
                    logger.warning("Non-200 for %s: %s", url, r.status_code)
                    return None, None
                soup = BeautifulSoup(r.content, 'html.parser')
                article = soup.find('article') or soup.find('main')
                if article:
                    paragraphs = article.find_all('p')
                else:
                    paragraphs = soup.find_all('p')
                text = '\n'.join([p.get_text().strip() for p in paragraphs if p.get_text().strip()])
                title_tag = soup.find('title')
                title = title_tag.get_text().strip() if title_tag else ''
                return title, text
            except requests.exceptions.RequestException as e:
                logger.warning('Request failed for %s: %s (attempt %d)', url, e, attempt + 1)
                attempt += 1
                time.sleep(min(5, 2 ** attempt))
            except Exception as e:
                logger.exception('Failed to fetch %s: %s', url, e)
                return None, None
        return None, None

    def _hash(self, text):
        return hashlib.sha256(text.encode('utf-8')).hexdigest()

    def ensure_source(self, session, source_cfg):
        src = session.query(Source).filter(func.lower(Source.url) == source_cfg.get('url').lower()).first()
        if not src:
            src = Source(name=source_cfg.get('name'), url=source_cfg.get('url'), rss_feed=source_cfg.get('rss_feed'), last_crawled=None)
            session.add(src)
            session.flush()
        return src

    def crawl_feed(self, source_cfg, limit=None):
        limit = limit or 0
        entries = self.fetch_rss(source_cfg.get('rss_feed'))
        logger.info('Found %d entries in feed %s', len(entries), source_cfg.get('name'))
        session = self.Session()
        src = self.ensure_source(session, source_cfg)
        saved = 0
        try:
            for e in entries:
                if limit and saved >= limit:
                    break
                url = e.get('link') or e.get('id')
                if not url:
                    continue
                exists = session.query(Document).filter(Document.source_url == url).first()
                if exists:
                    logger.debug('Already have %s', url)
                    continue
                title, content = self.fetch_article(url)
                if not content or len(content) < 50:
                    logger.debug('Skipping %s, content too short', url)
                    continue
                content_hash = self._hash(content)
                exists_hash = session.query(Document).filter(Document.content_hash == content_hash).first()
                if exists_hash:
                    logger.debug('Duplicate content %s', url)
                    continue
                word_count = len(content.split())
                publish_date = None
                if 'published_parsed' in e and e.published_parsed:
                    try:
                        import time as _time
                        publish_date = datetime.fromtimestamp(_time.mktime(e.published_parsed))
                    except Exception:
                        publish_date = None
                doc = Document(title=title, content=content, content_hash=content_hash, source_url=url, publish_date=publish_date, word_count=word_count, source_id=src.id)
                session.add(doc)
                session.commit()
                saved += 1
                logger.info('Saved article %s', url)
                src.last_crawled = datetime.utcnow()
                session.add(src)
                session.commit()
        finally:
            session.close()
        return saved

    def crawl_multiple(self, sources_cfg, total_limit=100):
        """Crawl multiple sources until total_limit articles are saved."""
        total = 0
        for s in sources_cfg:
            remaining = total_limit - total
            if remaining <= 0:
                break
            try:
                if s.get('name') == 'Wikipedia' and s.get('wikipedia_category'):
                    saved = self.crawl_wikipedia_category(s.get('wikipedia_category'), limit=remaining)
                else:
                    saved = self.crawl_feed(s, limit=remaining)
                total += saved
                logger.info('Saved %d articles from %s (total %d/%d)', saved, s.get('name'), total, total_limit)
            except Exception:
                logger.exception('Failed crawling source %s', s.get('name'))
        return total

    def fetch_wikipedia_category_recursive(self, category, limit=1000):
        """Recursively fetch page URLs from a Wikipedia category and its subcategories"""
        S = self.session if hasattr(self, 'session') else requests.Session()
        headers = {'User-Agent': self.user_agent or random.choice(USER_AGENTS)}
        to_visit = [category]
        seen_cats = set()
        urls = []
        base = 'https://en.wikipedia.org/w/api.php'
        while to_visit and len(urls) < limit:
            cat = to_visit.pop(0)
            if cat in seen_cats:
                continue
            seen_cats.add(cat)
            cmcontinue = None
            while True:
                params = {
                    'action': 'query',
                    'list': 'categorymembers',
                    'cmtitle': f'Category:{cat}',
                    'cmlimit': '500',
                    'format': 'json',
                }
                if cmcontinue:
                    params['cmcontinue'] = cmcontinue
                try:
                    r = S.get(base, params=params, timeout=self.timeout, headers=headers)
                except Exception as e:
                    logger.warning('Failed to fetch wiki category %s: %s', cat, e)
                    break
                if r.status_code != 200:
                    logger.warning('Non-200 from Wikipedia API for %s: %s', cat, r.status_code)
                    break
                try:
                    data = r.json()
                except Exception as e:
                    logger.warning('Failed to decode JSON from Wikipedia API for %s: %s', cat, e)
                    break
                members = data.get('query', {}).get('categorymembers', [])
                for m in members:
                    if len(urls) >= limit:
                        break
                    mns = m.get('ns')
                    title = m.get('title')
                    if not title:
                        continue
                    # ns 0 = article, ns 14 = category
                    if mns == 0:
                        urls.append(f'https://en.wikipedia.org/wiki/{title.replace(" ", "_")}')
                    elif mns == 14:
                        # subcategory
                        sub = title.replace('Category:', '')
                        to_visit.append(sub)
                cont = data.get('continue', {})
                if cont and not len(urls) >= limit:
                    cmcontinue = cont.get('cmcontinue')
                    if not cmcontinue:
                        break
                    continue
                break
        return urls

    def crawl_wikipedia_category(self, category, limit=1000):
        urls = self.fetch_wikipedia_category_recursive(category, limit=limit)
        logger.info('Wikipedia category %s (recursive): found %d pages', category, len(urls))
        session = self.Session()
        saved = 0
        try:
            for u in urls:
                if saved >= limit:
                    break
                try:
                    title, content = self.fetch_article(u)
                    if not content or len(content.split()) < 400:
                        continue
                    content_hash = self._hash(content)
                    exists_hash = session.query(Document).filter(Document.content_hash == content_hash).first()
                    if exists_hash:
                        continue
                    word_count = len(content.split())
                    doc = Document(title=title, content=content, content_hash=content_hash, source_url=u, publish_date=None, word_count=word_count)
                    session.add(doc)
                    session.commit()
                    saved += 1
                    logger.info('Saved wiki page %s', u)
                except Exception:
                    logger.exception('Failed wiki page: %s', u)
        finally:
            session.close()
        return saved
