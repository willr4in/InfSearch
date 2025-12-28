import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient, UpdateOne
from datetime import datetime

# Add project root to path to allow importing core_bridge
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bridge import CoreBridge
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION

# Create a single instance of the bridge for this process
core_bridge = CoreBridge()

def create_db_index(collection):
    """Creates an index on the 'metadata.tokenized' field."""
    if "metadata.tokenized_1" not in collection.index_information():
        collection.create_index("metadata.tokenized")
        print("Created index on 'metadata.tokenized'.")

def process_document(document):
    """Tokenizes and stems a single document using the C++ core library."""
    text = document.get('text', '')
    if not text:
        return None, None
    
    tokens = core_bridge.tokenize(text)
    stems = [core_bridge.stem_word(token) for token in tokens]
    
    return tokens, stems

def run_tokenizer_for_query(query, batch_size=500, max_workers=4):
    """
    Finds documents matching a query and processes them in batches
    using a thread pool to tokenize and stem their text.
    """
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[ARTICLES_COLLECTION]
    
    create_db_index(collection)

    doc_ids_to_process = [doc['_id'] for doc in collection.find(query, {'_id': 1})]
    total_docs = len(doc_ids_to_process)
    print(f"Found {total_docs} documents to tokenize.")

    processed_count = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for i in range(0, total_docs, batch_size):
            batch_ids = doc_ids_to_process[i:i + batch_size]
            batch_docs = list(collection.find({'_id': {'$in': batch_ids}}))
            
            future_to_doc = {executor.submit(process_document, doc): doc for doc in batch_docs}
            
            updates = []
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    tokens, stems = future.result()
                    if tokens is not None:
                        update = UpdateOne(
                            {'_id': doc['_id']},
                            {'$set': {
                                'tokens': tokens,
                                'stems': stems,
                                'metadata.tokenized': True,
                                'metadata.tokenized_at': datetime.utcnow()
                            }}
                        )
                        updates.append(update)
                except Exception as exc:
                    print(f"Document {doc['_id']} generated an exception: {exc}")
            
            if updates:
                collection.bulk_write(updates)
                processed_count += len(updates)
                print(f"Processed batch. Total processed: {processed_count}/{total_docs}")

    print(f"\nTokenization complete. Total documents processed: {processed_count}")
    client.close()

if __name__ == '__main__':
    # Process all documents that have not been tokenized yet
    # (either the field doesn't exist or the tokens array is empty)
    untokenized_query = {
        "$or": [
            {"metadata.tokenized": {"$exists": False}},
            {"tokens": {"$exists": False}},
            {"tokens": []}
        ]
    }
    run_tokenizer_for_query(untokenized_query)
