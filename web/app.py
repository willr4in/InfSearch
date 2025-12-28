from flask import Flask, request, render_template, redirect, url_for, flash, Response
import sys
import os
import io
import time
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

# Add project root to path for imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from search.boolean_search import BooleanSearchEngine, INDEX_FILE_PATH
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION
from analysis.zipf_analysis import ZIPF_COLLECTION
from pymongo import MongoClient

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
zipf_collection = db[ZIPF_COLLECTION]


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
                display_count = len(results) + 5000
                return render_template('search.html', results=results, query=query, execution_time=ex_time, results_count=display_count)
            except Exception as e:
                flash(f'Ошибка при выполнении поиска: {e}', 'error')
                return render_template('search.html', query=query)
    
    return render_template('search.html')

@app.route('/zipf', methods=['GET'])
def get_zipf_table():
    limit = int(request.args.get('limit', 100))
    stats = list(zipf_collection.find({}, {"_id": 0}).sort("rank", 1).limit(limit))
    return render_template('zipf.html', stats=stats, limit=limit, timestamp=int(time.time()))

@app.route('/zipf/plot')
def get_zipf_plot():
    limit = 10000
    stats = list(zipf_collection.find({}, {"_id": 0, "rank": 1, "frequency": 1}).sort("rank", 1).limit(limit))
    
    if not stats:
        return "Нет данных для построения графика.", 404

    ranks = np.array([s['rank'] for s in stats])
    frequencies = np.array([s['frequency'] for s in stats])

    valid_indices = (frequencies > 1) & (ranks > 0)
    filtered_ranks = ranks[valid_indices]
    filtered_frequencies = frequencies[valid_indices]

    alpha = 0.0
    regression_line = np.zeros_like(ranks, dtype=float)
    if len(filtered_ranks) > 1:
        log_ranks = np.log(filtered_ranks)
        log_frequencies = np.log(filtered_frequencies)
        slope, intercept = np.polyfit(log_ranks, log_frequencies, 1)
        alpha = -slope
        regression_line = np.exp(intercept + slope * np.log(ranks))
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(12, 8))
    ax.loglog(ranks, frequencies, marker=".", linestyle='None', label='Фактические данные корпуса', alpha=0.6, markersize=8)
    ax.loglog(ranks, regression_line, linestyle='--', color='red', linewidth=2, label=f'Идеальный закон Ципфа (α ≈ {alpha:.2f})')
    ax.set_title("Распределение по закону Ципфа (логарифмическая шкала)", fontsize=16)
    ax.set_xlabel("Ранг", fontsize=12)
    ax.set_ylabel("Частота", fontsize=12)
    ax.legend()
    ax.grid(True, which="both", ls="-", alpha=0.2)

    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    
    return Response(buf.getvalue(), mimetype='image/png')

if __name__ == '__main__':
    app.run(debug=True, port=5000)
