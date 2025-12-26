#!/usr/bin/env python3
# Verify basic corpus statistics
import logging
from sqlalchemy import create_engine, text
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('verify_corpus')


def main():
    db_url = os.environ.get('DATABASE_URL') or 'postgresql+psycopg2://infsearch:infsearch@localhost:15432/infsearch'
    engine = create_engine(db_url)
    with engine.connect() as conn:
        r = conn.execute(text('SELECT COUNT(*) FROM documents'))
        cnt = r.scalar()
        logger.info('Documents count: %s', cnt)


if __name__ == '__main__':
    main()
