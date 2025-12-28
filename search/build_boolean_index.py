# search/build_boolean_index.py
import sys
import os
from collections import defaultdict
from pymongo import MongoClient, UpdateOne, ASCENDING

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

BOOLEAN_INDEX_COLLECTION = "boolean_index"

def build_index():
    """
    Builds an inverted index from the 'articles' collection and stores it
    in the 'boolean_index' collection.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]
    index_collection = db[BOOLEAN_INDEX_COLLECTION]

    print("Ensuring necessary indexes exist...")
    # Index for fast retrieval of articles by their custom ID
    articles_collection.create_index([("article_id", ASCENDING)], unique=True)
    # Index for fast retrieval of terms in the boolean index
    index_collection.create_index([("term", ASCENDING)], unique=True)

    print("Building in-memory index...")
    # In-memory inverted index: term -> {doc_id_1, doc_id_2, ...}
    in_memory_index = defaultdict(set)
    
    # Query for all tokenized articles
    cursor = articles_collection.find(
        {"metadata.tokenized": True},
        {"article_id": 1, "stems": 1, "_id": 0}
    )

    total_docs = 0
    for doc in cursor:
        total_docs += 1
        article_id = doc.get("article_id")
        stems = doc.get("stems", [])
        if not article_id:
            continue
            
        for stem in set(stems): # Use set to count each term once per document
            in_memory_index[stem].add(article_id)
            
    if not in_memory_index:
        print("No tokenized documents found to index.")
        return

    print(f"Processed {total_docs} documents. Found {len(in_memory_index)} unique terms.")
    print("Saving index to MongoDB...")

    # Use bulk operations for efficient updating/insertion
    operations = []
    for term, doc_ids_set in in_memory_index.items():
        doc_ids_list = sorted(list(doc_ids_set))
        operations.append(
            UpdateOne(
                {"term": term},
                {
                    "$set": {
                        "doc_ids": doc_ids_list,
                        "doc_count": len(doc_ids_list)
                    }
                },
                upsert=True
            )
        )
        
        # Write in batches to avoid large memory usage for the request
        if len(operations) >= 1000:
            index_collection.bulk_write(operations)
            operations = []

    if operations:
        index_collection.bulk_write(operations)

    print("Boolean index has been successfully built.")
    client.close()

if __name__ == '__main__':
    build_index()

