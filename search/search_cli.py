# search/search_cli.py
import sys
import os

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from search.boolean_search import BooleanSearchEngine

def main():
    """Command-line interface for boolean search."""
    engine = BooleanSearchEngine()
    print("Boolean Search CLI. Enter 'exit' to quit.")
    
    try:
        while True:
            query = input("Enter search query: ")
            if query.lower() == 'exit':
                break
            
            if not query.strip():
                continue

            results, exec_time = engine.search(query)

            print(f"\nFound {len(results)} results in {exec_time:.4f} seconds.")
            if results:
                print("--- Results ---")
                for i, doc in enumerate(results[:20]): # Show top 20 results
                    print(f"{i+1}. {doc['title']} (URL: {doc['url']})")
                if len(results) > 20:
                    print(f"... and {len(results) - 20} more.")
            print("-" * 15 + "\n")

    finally:
        engine.close()

if __name__ == '__main__':
    main()

