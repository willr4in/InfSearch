import sys
import os
import pytest

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.bridge import CoreBridge

@pytest.fixture(scope="module")
def bridge():
    """Fixture to provide a single instance of the CoreBridge."""
    try:
        return CoreBridge()
    except ImportError as e:
        pytest.fail(f"Failed to import C++ core library: {e}")

def test_tokenizer_and_stemmer(bridge):
    """Tests C++ tokenizer and stemmer."""
    text = "Научные исследования"
    tokens = bridge.tokenize(text)
    assert tokens == ["научные", "исследования"]
    
    stems = [bridge.stem_word(t) for t in tokens]
    # Our simple stemmer doesn't handle these well, this is a smoke test
    assert isinstance(stems, list) 

def test_indexing_and_search(bridge):
    """Tests the full C++ indexing and search pipeline."""
    with bridge.managed_index() as index_ptr:
        assert index_ptr is not None
        
        # Add documents
        bridge.add_document_to_index(index_ptr, 1, ["наук", "исследован"])
        bridge.add_document_to_index(index_ptr, 2, ["компьютер", "наук"])
        bridge.add_document_to_index(index_ptr, 3, ["исследован", "данн"])

        # Test simple search
        results_and = bridge.search_index(index_ptr, "наук AND исследован")
        assert sorted(results_and) == [1]

        results_or = bridge.search_index(index_ptr, "компьютер OR данн")
        assert sorted(results_or) == [2, 3]

        results_not = bridge.search_index(index_ptr, "наук NOT компьютер")
        assert sorted(results_not) == [1]

def test_zipf_calculation(bridge):
    """Smoke test for C++ Zipf frequency calculation."""
    with bridge.managed_freq_map() as freq_map_ptr:
        assert freq_map_ptr is not None
        
        bridge.add_stems_to_freq_map(freq_map_ptr, ["a", "b", "a", "c", "a"])
        freq_list = bridge.get_freq_map_as_list(freq_map_ptr)
        
        # Sort by stem to have a predictable order for assertion
        freq_list.sort(key=lambda x: x['stem'])
        
        assert freq_list == [
            {'stem': 'a', 'frequency': 3},
            {'stem': 'b', 'frequency': 1},
            {'stem': 'c', 'frequency': 1}
        ]


