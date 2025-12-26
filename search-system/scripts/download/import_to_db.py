#!/usr/bin/env python3
# Simple stub to import existing raw files from data/raw into DB
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('import_to_db')

RAW_DIR = Path('data/raw')


def main():
    logger.info('Scanning %s for files to import', RAW_DIR)
    for f in RAW_DIR.glob('**/*.html'):
        logger.info('Would import %s', f)


if __name__ == '__main__':
    main()
