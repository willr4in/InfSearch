import argparse
import sys
import os
import csv
from pymongo import MongoClient

# Add root directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from analysis.zipf_analysis import calculate_zipf_with_mongodb, ZIPF_COLLECTION
from crawler.config import MONGO_URI, DB_NAME

def export_to_csv():
    """Exports the zipf_stats collection to a CSV file."""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    zipf_collection = db[ZIPF_COLLECTION]
    
    cursor = zipf_collection.find({}, {"_id": 0}).sort("rank", 1)
    
    filename = "zipf_stats.csv"
    
    if zipf_collection.count_documents({}) == 0:
        print("No stats found to export. Please run with --calculate first.")
        return
        
    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ["rank", "stem", "frequency", "frequency_rank_product"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for row in cursor:
            writer.writerow(row)
            
    print(f"Successfully exported data to {filename}")
    client.close()

def main():
    parser = argparse.ArgumentParser(description="Zipf's Law Analysis CLI.")
    
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--calculate', action='store_true', help="Recalculate Zipf stats using MongoDB aggregation.")
    group.add_argument('--export-csv', action='store_true', help="Export the calculated stats to a CSV file.")

    args = parser.parse_args()

    if args.calculate:
        calculate_zipf_with_mongodb()
    elif args.export_csv:
        export_to_csv()

if __name__ == '__main__':
    main()

