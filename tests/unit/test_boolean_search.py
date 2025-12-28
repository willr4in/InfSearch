# tests/test_boolean_search.py
import unittest
from search.query_parser import QueryParser

class TestQueryParser(unittest.TestCase):

    def setUp(self):
        self.parser = QueryParser()

    def test_simple_and(self):
        query = "наука AND техника"
        expected = ["наука", "техника", "AND"]
        self.assertEqual(self.parser.to_postfix(query), expected)

    def test_simple_or(self):
        query = "наука OR техника"
        expected = ["наука", "техника", "OR"]
        self.assertEqual(self.parser.to_postfix(query), expected)

    def test_simple_not(self):
        # Note: We treat NOT as a unary operator with high precedence
        query = "NOT наука"
        expected = ["наука", "NOT"]
        self.assertEqual(self.parser.to_postfix(query), expected)
        
    def test_precedence(self):
        query = "a OR b AND c"
        expected = ["a", "b", "c", "AND", "OR"]
        self.assertEqual(self.parser.to_postfix(query), expected)

    def test_parentheses(self):
        query = "(a OR b) AND c"
        expected = ["a", "b", "OR", "c", "AND"]
        self.assertEqual(self.parser.to_postfix(query), expected)

    def test_complex_query(self):
        query = "a AND (b OR NOT c) AND d"
        expected = ["a", "b", "c", "NOT", "OR", "AND", "d", "AND"]
        self.assertEqual(self.parser.to_postfix(query), expected)
        
    def test_mismatched_parentheses(self):
        with self.assertRaises(ValueError):
            self.parser.to_postfix("(a OR b")
        with self.assertRaises(ValueError):
            self.parser.to_postfix("a OR b)")
            
# More tests for the search engine itself will be added later
if __name__ == '__main__':
    unittest.main()

