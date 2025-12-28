import pymongo
from pymongo import MongoClient, UpdateOne
from datetime import datetime
import re
import string
import nltk
from nltk.stem.snowball import SnowballStemmer
from nltk.tokenize import word_tokenize
import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add crawler directory to path to import config
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION
from .stemmer_py import cpp_stemmer

# Download necessary NLTK data if not present
import nltk
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    print("NLTK 'punkt' model not found. Downloading...")
    nltk.download('punkt')

# Fallback to NLTK if C++ stemmer is not available
if cpp_stemmer.is_loaded:
    stemmer_func = cpp_stemmer.stem
    print("Using C++ stemmer.")
else:
    from nltk.stem.snowball import SnowballStemmer
    nltk_stemmer = SnowballStemmer("russian")
    stemmer_func = nltk_stemmer.stem
    print("Using NLTK stemmer as a fallback.")

PUNCTUATION = re.escape(string.punctuation)

def create_db_index():
    """Creates an index on the 'metadata.tokenized' field."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]
    articles_collection.create_index([("metadata.tokenized", 1)])
    print("Index on 'metadata.tokenized' created successfully.")
    client.close()

def process_document(document):
    """Tokenizes and stems the text of a single document."""
    text = document.get('text', '')
    if not text:
        return None, [], []

    # Tokenize
    tokens = word_tokenize(text, language='russian')
    
    # Clean tokens: lowercase, remove punctuation and numbers
    cleaned_tokens = []
    for token in tokens:
        lowered = token.lower()
        if lowered.isalpha(): # Keep only alphabetic tokens
            cleaned_tokens.append(lowered)
    
    # Stemming
    stems = [stemmer_func(token) for token in cleaned_tokens]
    
    return document['_id'], cleaned_tokens, stems

def run_tokenizer_for_query(query, batch_size=1000, max_workers=4):
    """Processes documents matching a query in batches using multithreading."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    articles_collection = db[ARTICLES_COLLECTION]

    total_processed = 0
    cursor = articles_collection.find(query, no_cursor_timeout=True).batch_size(batch_size)
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            batch = []
            for doc in cursor:
                batch.append(doc)
                if len(batch) >= batch_size:
                    process_and_update_batch(executor, articles_collection, batch)
                    total_processed += len(batch)
                    print(f"Processed {total_processed} documents...")
                    batch = []
            
            # Process the final batch if any documents are left
            if batch:
                process_and_update_batch(executor, articles_collection, batch)
                total_processed += len(batch)
                print(f"Processed final batch of {len(batch)} documents.")

    finally:
        cursor.close()
        client.close()

    print(f"\nTokenization complete. Total documents processed: {total_processed}")

def process_and_update_batch(executor, collection, batch):
    """Submits a batch of documents to the executor and updates them in MongoDB."""
    future_to_doc = {executor.submit(process_document, doc): doc for doc in batch}
    
    updates = []
    for future in as_completed(future_to_doc):
        doc_id, tokens, stems = future.result()
        if doc_id is not None:
            update = UpdateOne(
                {'_id': doc_id},
                {'$set': {
                    'tokens': tokens,
                    'stems': stems,
                    'metadata.tokenized': True,
                    'metadata.tokenized_at': datetime.utcnow()
                }}
            )
            updates.append(update)
            
    if updates:
        collection.bulk_write(updates)

if __name__ == '__main__':
    # This is for direct execution, but the main logic is in tokenize_cli.py
    print("This script contains the core tokenization logic.")
    print("Use tokenize_cli.py to run the process.")
    # create_db_index() # Run this once if needed

