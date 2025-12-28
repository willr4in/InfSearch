import sys
import os
import time
from pymongo import MongoClient

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bridge import CoreBridge
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

INDEX_FILE_PATH = "boolean_index.bin"

class BooleanSearchEngine:
    def __init__(self):
        self.bridge = CoreBridge()
        print("Loading C++ index from file...")
        self.index_ptr = self.bridge.lib.load_index_from_file(INDEX_FILE_PATH.encode('utf-8'))
        if not self.index_ptr:
            raise IOError(f"Could not load index file: {INDEX_FILE_PATH}. Please build it first.")
        
        client = MongoClient(MONGO_URI)
        self.articles_collection = client[DB_NAME][ARTICLES_COLLECTION]
        print("Search engine initialized.")

    def __del__(self):
        # Destructor to free the C++ index memory when the object is destroyed
        if hasattr(self, 'index_ptr') and self.index_ptr:
            print("Destroying C++ index.")
            self.bridge.lib.destroy_index(self.index_ptr)

    def search(self, query: str):
        # Pre-process query: tokenize, stem, and format for C++ search
        # (e.g., "наука И технология" -> "наук AND технолог")
        tokens = self.bridge.tokenize(query)
        processed_tokens = []
        for token in tokens:
            if token.upper() in ["AND", "OR", "NOT"]:
                processed_tokens.append(token.upper())
            else:
                processed_tokens.append(self.bridge.stem_word(token))
        
        processed_query = " ".join(processed_tokens)
        print(f"Processed query: '{processed_query}'")

        start_time = time.time()
        doc_ids = self.bridge.search_index(self.index_ptr, processed_query)
        end_time = time.time()
        
        execution_time = round(end_time - start_time, 4)
        
        results_docs = list(self.articles_collection.find(
            {"article_id": {"$in": doc_ids}},
            {"title": 1, "url": 1, "_id": 0}
        ))
        
        return results_docs, execution_time

if __name__ == '__main__':
    engine = BooleanSearchEngine()
    
    while True:
        try:
            q = input("Enter search query (or 'exit'): ")
            if q.lower() == 'exit':
                break
            
            results, ex_time = engine.search(q)
            print(f"Found {len(results)} results in {ex_time}s:")
            for doc in results:
                print(f"  - {doc['title']} ({doc['url']})")

        except Exception as e:
            print(f"An error occurred: {e}")

