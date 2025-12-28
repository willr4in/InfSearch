import sys
import os
from pymongo import MongoClient, UpdateOne, ReplaceOne
from contextlib import contextmanager

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bridge import CoreBridge
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

ZIPF_COLLECTION = "zipf_stats"

def calculate_zipf_with_cpp():
    bridge = CoreBridge()
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]
    zipf_collection = db[ZIPF_COLLECTION]

    print("Calculating Zipf stats using C++ core...")

    with bridge.managed_freq_map() as freq_map_ptr:
        cursor = articles_collection.find({"stems": {"$exists": True, "$ne": []}}, {"stems": 1})
        
        doc_count = 0
        for doc in cursor:
            stems = doc.get('stems', [])
            if stems:
                bridge.add_stems_to_freq_map(freq_map_ptr, stems)
            doc_count += 1
            if doc_count % 1000 == 0:
                print(f"Processed {doc_count} documents for Zipf stats...")
        
        print("All documents processed. Converting C++ map to array...")
        freq_list = bridge.get_freq_map_as_list(freq_map_ptr)
    
    print(f"Received {len(freq_list)} unique stems from C++. Preparing for DB update.")

    # --- Update MongoDB ---
    zipf_collection.delete_many({})
    operations = []
    for i, item in enumerate(freq_list):
        rank = i + 1
        operations.append(ReplaceOne(
            {"stem": item['stem']},
            {
                "stem": item['stem'],
                "frequency": item['frequency'],
                "rank": rank,
                "frequency_rank_product": item['frequency'] * rank
            },
            upsert=True
        ))
    
    if operations:
        zipf_collection.bulk_write(operations)

    print("Zipf stats successfully calculated and saved to MongoDB.")
    client.close()

if __name__ == '__main__':
    calculate_zipf_with_cpp()
