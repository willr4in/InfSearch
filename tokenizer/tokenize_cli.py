import argparse
import sys
import os
from bson import ObjectId

# Add tokenizer directory to path to import its modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tokenize_batch import run_tokenizer_for_query, create_db_index

def main():
    parser = argparse.ArgumentParser(description="Tokenizer CLI for MongoDB article corpus.")
    
    # Mutually exclusive group for operations
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--all', action='store_true', help="Process all untokenized documents in the corpus.")
    group.add_argument('--id', type=str, help="Process a single document by its MongoDB ObjectId.")
    group.add_argument('--create-index', action='store_true', help="Create the necessary index in MongoDB and exit.")

    args = parser.parse_args()

    if args.create_index:
        print("Creating index...")
        create_db_index()
        return

    query = {}
    if args.all:
        print("Starting tokenization for all untokenized documents...")
        query = {"tokens": []}
    elif args.id:
        try:
            doc_id = ObjectId(args.id)
            print(f"Starting tokenization for document with ID: {doc_id}")
            query = {"_id": doc_id}
        except Exception:
            print("Error: Invalid MongoDB ObjectId provided.")
            return
    
    run_tokenizer_for_query(query)

if __name__ == '__main__':
    main()

