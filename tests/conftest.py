# tests/conftest.py
import pytest
from pymongo import MongoClient
import json
import os
import sys

# Add root directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, ARTICLES_COLLECTION

TEST_DB_NAME = "test_ir_corpus"

@pytest.fixture(scope="function")
def mongo_client():
    """Function-scoped MongoDB client for tests that need it."""
    client = MongoClient(MONGO_URI)
    yield client
    client.close()

@pytest.fixture(scope="function")
def test_db(mongo_client):
    """Function-scoped test database that is cleared after each test."""
    db = mongo_client[TEST_DB_NAME]
    yield db
    # Teardown: drop the entire test database
    mongo_client.drop_database(TEST_DB_NAME)

@pytest.fixture(scope="function")
def loaded_test_db(test_db):
    """Loads sample data into the test database."""
    data_path = os.path.join(os.path.dirname(__file__), 'data', 'sample_articles.json')
    with open(data_path, 'r', encoding='utf-8') as f:
        articles_data = json.load(f)
    
    for article in articles_data:
        if "metadata" not in article:
            article["metadata"] = {}

    test_db[ARTICLES_COLLECTION].insert_many(articles_data)
    return test_db
