import unittest
from collections import Counter
from unittest.mock import MagicMock, patch

# Mock the database functions by patching the analysis script
from analysis import zipf_analysis

class TestZipfAnalysis(unittest.TestCase):

    def setUp(self):
        # Create a sample corpus for testing
        self.mock_corpus = [
            {"stems": ["a", "b", "c", "a", "a", "b"]},
            {"stems": ["d", "e", "c", "a"]},
            {"stems": ["b", "c", "f"]}
        ]
        # Total stems = 6 + 4 + 3 = 13

    @patch('analysis.zipf_analysis.MongoClient')
    def test_python_calculation(self, mock_mongo_client):
        # Setup mock MongoDB environment
        mock_db = MagicMock()
        mock_articles_collection = MagicMock()
        mock_zipf_collection = MagicMock()
        mock_articles_collection.find.return_value = self.mock_corpus
        
        # When db['articles'] is accessed, return our articles mock
        # When db['zipf_stats'] is accessed, return our zipf mock
        def get_item(key):
            if key == zipf_analysis.ARTICLES_COLLECTION:
                return mock_articles_collection
            elif key == zipf_analysis.ZIPF_COLLECTION:
                return mock_zipf_collection
            return MagicMock() # Default for any other collection
            
        mock_db.__getitem__.side_effect = get_item
        mock_mongo_client.return_value.__getitem__.return_value = mock_db

        # Run the function to be tested
        zipf_analysis.calculate_zipf_with_python()

        # The results are passed to insert_many on our specific zipf mock
        call_args_list = mock_zipf_collection.insert_many.call_args
        
        # If insert_many was not called, treat it as an empty list
        if call_args_list is None:
            results = []
        else:
            results = list(call_args_list[0][0])
        
        # 1. Test total frequency
        total_freq = sum(item['frequency'] for item in results)
        self.assertEqual(total_freq, 13)

        # 2. Test ranks and decreasing frequency
        # Expected frequencies: a: 4, b: 3, c: 3, d: 1, e: 1, f: 1
        # Ranks can be tricky with ties, but frequency must be non-increasing
        frequencies = [item['frequency'] for item in results]
        self.assertEqual(frequencies, sorted(frequencies, reverse=True))

        # 3. Check the top ranked item
        self.assertEqual(results[0]['stem'], 'a')
        self.assertEqual(results[0]['frequency'], 4)
        self.assertEqual(results[0]['rank'], 1)

if __name__ == '__main__':
    unittest.main()

