#!/usr/bin/env python3
import argparse
import yaml
import logging
from pathlib import Path
import sys
import os
import importlib.util

# ensure repo root is on sys.path
script_dir = Path(__file__).resolve().parent
repo_root = script_dir.parent.parent
sys.path.insert(0, str(repo_root))

# try normal import first, otherwise load module by path
try:
    from python.crawler.news_crawler import NewsCrawler
except Exception:
    # search for news_crawler.py
    found = list(repo_root.rglob('news_crawler.py'))
    if not found:
        raise
    spec_path = str(found[0])
    spec = importlib.util.spec_from_file_location('news_crawler', spec_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    NewsCrawler = module.NewsCrawler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('download_corpus')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default='config/crawler_config.yaml')
    p.add_argument('--limit', type=int, default=100, help='Total articles to try to download')
    args = p.parse_args()

    cfg = yaml.safe_load(Path(args.config).read_text())
    sources = cfg.get('sources', [])
    total_limit = args.limit or cfg.get('max_articles', 100)

    crawler = NewsCrawler()
    total = crawler.crawl_multiple(sources, total_limit=total_limit)
    logger.info('Total saved: %d', total)


if __name__ == '__main__':
    main()
