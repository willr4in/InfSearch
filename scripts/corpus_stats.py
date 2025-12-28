# scripts/corpus_stats.py
import pymongo
from pymongo import MongoClient
import sys
import os

# Add crawler directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

def get_stats():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]

    total_docs = articles_collection.count_documents({})
    
    if total_docs == 0:
        print("No documents found in the corpus.")
        return

    pipeline = [
        {
            "$group": {
                "_id": None,
                "avg_word_count": {"$avg": "$metadata.word_count"},
                "avg_char_count": {"$avg": "$metadata.char_count"}
            }
        }
    ]
    
    stats = list(articles_collection.aggregate(pipeline))
    
    avg_word_count = stats[0]['avg_word_count'] if stats else 0
    avg_char_count = stats[0]['avg_char_count'] if stats else 0

    print("Corpus Statistics:")
    print("------------------")
    print(f"Total documents: {total_docs}")
    print(f"Average word count: {avg_word_count:.2f}")
    print(f"Average character count: {avg_char_count:.2f}")

    client.close()

if __name__ == "__main__":
    get_stats()

