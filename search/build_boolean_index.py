import sys
import os
from pymongo import MongoClient

# Add project root to path to allow importing 'core'
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bridge import CoreBridge
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

INDEX_FILE_PATH = "boolean_index.bin"

def build_index():
    """
    Builds the inverted index using the C++ core library and saves it to a file.
    """
    bridge = CoreBridge()
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]

    print(f"Starting index build using C++ Core v{bridge.get_version()}...")
    
    # Use the context manager to ensure the index is always destroyed
    with bridge.managed_index() as index_ptr:
        print("C++ index created in memory.")
        
        # We need documents that have stems
        cursor = articles_collection.find(
            {"stems": {"$exists": True, "$ne": []}},
            {"article_id": 1, "stems": 1}
        )

        doc_count = 0
        for doc in cursor:
            doc_id = doc.get('article_id')
            stems = doc.get('stems')

            if doc_id is None or not stems:
                continue

            bridge.add_document_to_index(index_ptr, doc_id, stems)
            doc_count += 1
            if doc_count % 1000 == 0:
                print(f"Processed {doc_count} documents...")

        print(f"Finished processing {doc_count} documents.")

        print(f"Saving index to '{INDEX_FILE_PATH}'...")
        result = bridge.save_index(index_ptr, INDEX_FILE_PATH)
        if result == 0:
            print("Index saved successfully (Note: C++ save is a placeholder).")
        else:
            print("Failed to save index (Note: C++ save is a placeholder, this is expected).")

    print("Index build process complete.")
    client.close()

if __name__ == '__main__':
    build_index()
