# tokenizer/stemmer_py.py
import ctypes
import os

class CppStemmer:
    def __init__(self, library_path):
        """
        Initializes the Python wrapper for the C++ stemmer library.
        """
        try:
            self.lib = ctypes.CDLL(library_path)

            # Define the argument and return types for the C++ functions
            self.lib.stem_word.argtypes = [ctypes.c_char_p]
            self.lib.stem_word.restype = ctypes.POINTER(ctypes.c_char)

            self.lib.free_stemmed_word.argtypes = [ctypes.POINTER(ctypes.c_char)]
            self.lib.free_stemmed_word.restype = None
            
            self.is_loaded = True
        except OSError as e:
            print(f"Warning: Could not load C++ stemmer library from {library_path}. Error: {e}")
            print("Falling back to NLTK stemmer.")
            self.is_loaded = False

    def stem(self, word):
        """
        Stems a single word using the C++ library.
        """
        if not self.is_loaded:
            raise RuntimeError("C++ stemmer library is not loaded.")

        word_bytes = word.encode('utf-8')
        stemmed_ptr = self.lib.stem_word(word_bytes)
        
        stemmed_word = ctypes.cast(stemmed_ptr, ctypes.c_char_p).value.decode('utf-8')
        
        # Free the memory allocated by the C++ code
        self.lib.free_stemmed_word(stemmed_ptr)
        
        return stemmed_word

# --- Global stemmer instance ---
# Determine the library path based on the operating system
lib_filename = 'libstemmer.so' if os.name != 'nt' else 'stemmer.dll'
# The library is typically in the 'build' directory directly after compilation with this CMake setup
default_lib_path = os.path.join(os.path.dirname(__file__), 'stemmer_cpp', 'build', lib_filename)

# Create a single instance of the stemmer
cpp_stemmer = CppStemmer(default_lib_path)
