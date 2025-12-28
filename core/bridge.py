import ctypes
import os
from contextlib import contextmanager

# ... (Existing Structs: StringArray, IntArray, InvertedIndex) ...
class StringArray(ctypes.Structure): _fields_ = [("strings", ctypes.POINTER(ctypes.c_char_p)), ("count", ctypes.c_int)]
class IntArray(ctypes.Structure): _fields_ = [("ids", ctypes.POINTER(ctypes.c_int)), ("count", ctypes.c_int)]
class InvertedIndex(ctypes.Structure): pass

# --- New Structs for Zipf ---
class FreqPair(ctypes.Structure):
    _fields_ = [("stem", ctypes.c_char_p), ("frequency", ctypes.c_int)]

class FreqArray(ctypes.Structure):
    _fields_ = [("pairs", ctypes.POINTER(FreqPair)), ("count", ctypes.c_int)]

class FrequencyMap(ctypes.Structure): pass # Opaque pointer


class CoreBridge:
    def __init__(self):
        self.lib = self._load_library()
        if not self.lib: raise ImportError("Could not load C++ core library.")
        self._define_prototypes()

    def _load_library(self):
        lib_name = 'libcore.so'; lib_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'core_cpp', 'build', lib_name)
        return ctypes.CDLL(lib_path) if os.path.exists(lib_path) else None

    def _define_prototypes(self):
        # ... (Tokenizer, Stemmer, Indexer prototypes) ...
        self.lib.get_core_version.restype = ctypes.c_char_p
        self.lib.tokenize.restype = StringArray; self.lib.tokenize.argtypes = [ctypes.c_char_p]
        self.lib.stem_word_no_stl.restype = ctypes.POINTER(ctypes.c_char); self.lib.stem_word_no_stl.argtypes = [ctypes.c_char_p]
        self.lib.free_string_array.argtypes = [StringArray]; self.lib.free_single_string.argtypes = [ctypes.POINTER(ctypes.c_char)]
        self.lib.create_index.restype = ctypes.POINTER(InvertedIndex); self.lib.destroy_index.argtypes = [ctypes.POINTER(InvertedIndex)]
        self.lib.add_document_to_index.argtypes = [ctypes.POINTER(InvertedIndex), ctypes.c_int, StringArray]
        self.lib.save_index_to_file.restype = ctypes.c_int; self.lib.save_index_to_file.argtypes = [ctypes.POINTER(InvertedIndex), ctypes.c_char_p]
        self.lib.load_index_from_file.restype = ctypes.POINTER(InvertedIndex); self.lib.load_index_from_file.argtypes = [ctypes.c_char_p]
        self.lib.search_index.restype = IntArray; self.lib.search_index.argtypes = [ctypes.POINTER(InvertedIndex), ctypes.c_char_p]
        self.lib.free_int_array.argtypes = [IntArray]
        
        # --- Zipf Functions ---
        self.lib.create_freq_map.restype = ctypes.POINTER(FrequencyMap)
        self.lib.destroy_freq_map.argtypes = [ctypes.POINTER(FrequencyMap)]
        self.lib.add_stems_to_freq_map.argtypes = [ctypes.POINTER(FrequencyMap), StringArray]
        self.lib.get_freq_map_as_array.restype = FreqArray; self.lib.get_freq_map_as_array.argtypes = [ctypes.POINTER(FrequencyMap)]
        self.lib.free_freq_array.argtypes = [FreqArray]

    # ... (Tokenizer, Stemmer, Indexer methods) ...
    def get_version(self): return self.lib.get_core_version().decode('utf-8')
    def tokenize(self, text: str) -> list: # ...
        c_arr = self.lib.tokenize(text.encode('utf-8')); py_list = [c_arr.strings[i].decode('utf-8') for i in range(c_arr.count)]; self.lib.free_string_array(c_arr); return py_list
    def stem_word(self, word: str) -> str: # ...
        c_ptr = self.lib.stem_word_no_stl(word.encode('utf-8')); py_str = ctypes.cast(c_ptr, ctypes.c_char_p).value.decode('utf-8'); self.lib.free_single_string(c_ptr); return py_str
    @contextmanager
    def managed_index(self, path: str = None): # ...
        index_ptr = self.lib.load_index_from_file(path.encode('utf-8')) if path and os.path.exists(path) else self.lib.create_index()
        try: yield index_ptr
        finally:
            if index_ptr: self.lib.destroy_index(index_ptr)
    def add_document_to_index(self, index_ptr, doc_id: int, stems: list): # ...
        c_stems = (ctypes.c_char_p * len(stems))(); encoded_stems = [s.encode('utf-8') for s in stems]; c_stems[:] = encoded_stems
        self.lib.add_document_to_index(index_ptr, doc_id, StringArray(c_stems, len(stems)))
    def save_index(self, index_ptr, path: str) -> bool: return self.lib.save_index_to_file(index_ptr, path.encode('utf-8')) == 0
    def search_index(self, index_ptr, query: str) -> list: # ...
        c_int_arr = self.lib.search_index(index_ptr, query.encode('utf-8')); py_list = [c_int_arr.ids[i] for i in range(c_int_arr.count)]; self.lib.free_int_array(c_int_arr); return py_list

    # --- Zipf Methods ---
    @contextmanager
    def managed_freq_map(self):
        map_ptr = self.lib.create_freq_map()
        try:
            yield map_ptr
        finally:
            if map_ptr: self.lib.destroy_freq_map(map_ptr)

    def add_stems_to_freq_map(self, map_ptr, stems: list):
        c_stems = (ctypes.c_char_p * len(stems))(); encoded_stems = [s.encode('utf-8') for s in stems]; c_stems[:] = encoded_stems
        self.lib.add_stems_to_freq_map(map_ptr, StringArray(c_stems, len(stems)))
    
    def get_freq_map_as_list(self, map_ptr) -> list:
        c_freq_arr = self.lib.get_freq_map_as_array(map_ptr)
        py_list = [{'stem': c_freq_arr.pairs[i].stem.decode('utf-8'), 'frequency': c_freq_arr.pairs[i].frequency} for i in range(c_freq_arr.count)]
        self.lib.free_freq_array(c_freq_arr)
        return py_list

