import pymongo
from pymongo import MongoClient
import sys
import os

# Add root directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION, STATE_COLLECTION

ZIPF_COLLECTION = "zipf_stats"

def calculate_zipf_with_mongodb():
    """
    Calculates Zipf's law statistics using the MongoDB Aggregation Framework.
    This is the most efficient method.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]
    
    print("Starting Zipf analysis using MongoDB aggregation...")

    # Ensure a unique index exists on the target collection's merge key
    zipf_collection = db[ZIPF_COLLECTION]
    zipf_collection.create_index([("stem", 1)], unique=True)

    # The aggregation pipeline
    pipeline = [
        {"$unwind": "$stems"},
        {"$group": {"_id": "$stems", "frequency": {"$sum": 1}}},
        {"$sort": {"frequency": -1}},
        {
            "$setWindowFields": {
                "sortBy": {"frequency": -1},
                "output": {
                    "rank": {"$rank": {}}
                }
            }
        },
        {"$project": {
            "_id": 0,
            "stem": "$_id",
            "frequency": 1,
            "rank": 1,
            "frequency_rank_product": {"$multiply": ["$frequency", "$rank"]}
        }},
        {"$merge": {"into": ZIPF_COLLECTION, "on": "stem", "whenMatched": "replace", "whenNotMatched": "insert"}}
    ]

    # Execute the aggregation
    articles_collection.aggregate(pipeline)
    
    total_stats = db[ZIPF_COLLECTION].count_documents({})
    print(f"Aggregation complete. Results saved to '{ZIPF_COLLECTION}' collection.")
    print(f"Total unique stems found: {total_stats}")
    
    client.close()

def calculate_zipf_with_python():
    """
    Calculates Zipf's law statistics by processing data in Python.
    Less efficient, used for testing and comparison.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]
    
    print("Starting Zipf analysis using Python...")
    
    from collections import Counter
    
    stem_counts = Counter()
    cursor = articles_collection.find({}, {"stems": 1})
    
    for doc in cursor:
        stem_counts.update(doc.get("stems", []))
        
    # Sort by frequency
    sorted_stems = sorted(stem_counts.items(), key=lambda item: item[1], reverse=True)
    
    # Prepare documents for bulk insert
    zipf_docs = []
    for i, (stem, frequency) in enumerate(sorted_stems):
        rank = i + 1
        zipf_docs.append({
            "stem": stem,
            "frequency": frequency,
            "rank": rank,
            "frequency_rank_product": frequency * rank
        })
        
    # Save to MongoDB
    zipf_collection = db[ZIPF_COLLECTION]
    zipf_collection.delete_many({}) # Clear old stats
    if zipf_docs:
        zipf_collection.insert_many(zipf_docs)
        
    print(f"Python processing complete. Results saved to '{ZIPF_COLLECTION}' collection.")
    print(f"Total unique stems found: {len(zipf_docs)}")

    client.close()

