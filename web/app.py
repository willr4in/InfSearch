from flask import Flask, request, render_template, redirect, url_for, flash
import sys
import os

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from search.boolean_search import BooleanSearchEngine, INDEX_FILE_PATH
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION
from pymongo import MongoClient
import time

app = Flask(__name__)
app.secret_key = 'your_very_secret_key'

# --- Initialize Search Engine ---
search_engine = None
try:
    if os.path.exists(INDEX_FILE_PATH):
        search_engine = BooleanSearchEngine()
    else:
        print(f"Warning: Index file '{INDEX_FILE_PATH}' not found. Search will be disabled.")
except Exception as e:
    print(f"Error initializing search engine: {e}")
    search_engine = None

# --- MongoDB connection for other functionalities ---
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_collection = db[ARTICLES_COLLECTION]


@app.route('/')
def index():
    return redirect(url_for('search_page'))

@app.route('/search', methods=['GET', 'POST'])
def search_page():
    if not search_engine:
        flash('Ошибка: Поисковый движок не инициализирован. Индексный файл не найден.', 'error')
        return render_template('search.html')

    if request.method == 'POST':
        query = request.form.get('query')
        if query:
            try:
                results, ex_time = search_engine.search(query)
                return render_template('search.html', results=results, query=query, execution_time=ex_time)
            except Exception as e:
                flash(f'Ошибка при выполнении поиска: {e}', 'error')
                return render_template('search.html', query=query)
    
    return render_template('search.html')

# ... (You can add back other routes like /articles, /stats, /zipf later if needed)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
