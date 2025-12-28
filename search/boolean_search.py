# search/boolean_search.py
import sys
import os
from datetime import datetime
import time
from pymongo import MongoClient

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION
from search.query_parser import QueryParser
from tokenizer.stemmer_py import cpp_stemmer

BOOLEAN_INDEX_COLLECTION = "boolean_index"
SEARCH_HISTORY_COLLECTION = "search_history"

class BooleanSearchEngine:
    def __init__(self):
        self.client = MongoClient(MONGO_URI)
        self.db = self.client[DB_NAME]
        self.index_collection = self.db[BOOLEAN_INDEX_COLLECTION]
        self.articles_collection = self.db[ARTICLES_COLLECTION]
        self.history_collection = self.db[SEARCH_HISTORY_COLLECTION]
        self.parser = QueryParser()

        # For NOT operations, we need the set of all document IDs
        self._all_doc_ids = None

    def _get_all_doc_ids(self):
        """Lazily fetches and caches the set of all article_ids."""
        if self._all_doc_ids is None:
            print("Caching all document IDs for NOT operations...")
            ids = self.articles_collection.distinct("article_id")
            self._all_doc_ids = set(ids)
        return self._all_doc_ids

    def _get_doc_ids_for_term(self, term):
        """Retrieves the list of document IDs for a single term from the index."""
        result = self.index_collection.find_one({"term": term})
        if result:
            return set(result["doc_ids"])
        return set()

    def search(self, query: str):
        """
        Performs a boolean search for the given query.
        Returns a list of article documents.
        """
        start_time = time.time()
        
        try:
            # 1. Parse the query into postfix (RPN)
            postfix_query = self.parser.to_postfix(query)
            
            # 2. Evaluate the postfix query
            results_stack = []
            for token in postfix_query:
                if token == "AND":
                    op2 = results_stack.pop()
                    op1 = results_stack.pop()
                    results_stack.append(op1.intersection(op2))
                elif token == "OR":
                    op2 = results_stack.pop()
                    op1 = results_stack.pop()
                    results_stack.append(op1.union(op2))
                elif token == "NOT":
                    op = results_stack.pop()
                    all_ids = self._get_all_doc_ids()
                    results_stack.append(all_ids.difference(op))
                else: # It's an operand (term)
                    # Stem the term before looking it up in the index
                    stemmed_token = cpp_stemmer.stem(token) if cpp_stemmer.is_loaded else token
                    ids = self._get_doc_ids_for_term(stemmed_token)
                    results_stack.append(ids)

            if not results_stack:
                final_ids = []
            else:
                final_ids = sorted(list(results_stack[0]))

            # 3. Fetch article titles for the resulting IDs
            results_docs = list(self.articles_collection.find(
                {"article_id": {"$in": final_ids}},
                {"title": 1, "url": 1, "article_id": 1, "_id": 0}
            ))
            
            # Reorder results to match the sorted list of IDs
            id_to_doc = {doc['article_id']: doc for doc in results_docs}
            ordered_results = [id_to_doc[id] for id in final_ids if id in id_to_doc]

        except (ValueError, IndexError) as e:
            print(f"Error processing query: {e}")
            ordered_results = []
            final_ids = []

        execution_time = time.time() - start_time
        
        # 4. Save search history
        self.history_collection.insert_one({
            "query": query,
            "parsed_query": " ".join(postfix_query) if 'postfix_query' in locals() else "Parse Error",
            "results_count": len(final_ids),
            "execution_time": execution_time,
            "timestamp": datetime.utcnow()
        })
        
        return ordered_results, execution_time

    def close(self):
        self.client.close()


