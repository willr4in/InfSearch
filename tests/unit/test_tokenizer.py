import unittest
import string
import re
from unittest.mock import MagicMock

# A simple tokenizer for testing purposes
def simple_tokenizer(text):
    text = text.lower()
    text = re.sub(f"[{re.escape(string.punctuation)}]", "", text)
    tokens = text.split()
    return [token for token in tokens if not token.isdigit()]

class TestTokenizer(unittest.TestCase):

    def test_simple_tokenization(self):
        text = "Привет, мир! Это тестовый текст 123."
        expected = ["привет", "мир", "это", "тестовый", "текст"]
        self.assertEqual(simple_tokenizer(text), expected)

    def test_empty_text(self):
        text = ""
        expected = []
        self.assertEqual(simple_tokenizer(text), expected)

    def test_text_with_only_punctuation(self):
        text = "!!! , . ? ;"
        expected = []
        self.assertEqual(simple_tokenizer(text), expected)

if __name__ == '__main__':
    unittest.main()

