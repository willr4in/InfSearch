# tests/integration/test_integration.py
import pytest
import sys
import os
from unittest.mock import patch

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from crawler.config import ARTICLES_COLLECTION
from tokenizer.tokenize_batch import run_tokenizer_for_query
from search.build_boolean_index import build_index
from search.boolean_search import BooleanSearchEngine

@pytest.mark.integration
def test_full_pipeline(loaded_test_db):
    """
    Tests the entire pipeline: tokenization -> index building -> search.
    """
    # 1. Run Tokenization on the loaded data
    # We need to temporarily patch the config to use the test DB
    with patch('tokenizer.tokenize_batch.MONGO_URI', new=f"mongodb://localhost:27017/"), \
         patch('tokenizer.tokenize_batch.DB_NAME', new='test_ir_corpus'):
        run_tokenizer_for_query(query={"tokens": []}, batch_size=10, max_workers=1)

    # Verify that tokenization worked
    articles_collection = loaded_test_db[ARTICLES_COLLECTION]
    doc_count = articles_collection.count_documents({})
    tokenized_count = articles_collection.count_documents({"metadata.tokenized": True})
    assert doc_count == tokenized_count
    
    # 2. Build the boolean index
    with patch('search.build_boolean_index.MONGO_URI', new=f"mongodb://localhost:27017/"), \
         patch('search.build_boolean_index.DB_NAME', new='test_ir_corpus'):
        build_index()

    # 3. Perform a search
    # We need a new engine instance connected to the test DB
    with patch('search.boolean_search.MONGO_URI', new=f"mongodb://localhost:27017/"), \
         patch('search.boolean_search.DB_NAME', new='test_ir_corpus'):
        engine = BooleanSearchEngine()
        
        # Search for a term that exists in article 1 and 3 ("информации" / "информационный")
        # The stem should be "информац" or similar
        results, _ = engine.search("информации") 
        
        assert len(results) == 2
        
        result_titles = {res['title'] for res in results}
        assert "Теория информации" in result_titles
        assert "Информационный поиск" in result_titles
        
        engine.close()

