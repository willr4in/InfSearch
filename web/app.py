from flask import Flask, request, jsonify, render_template, Response, redirect, url_for, send_from_directory, flash
import subprocess
from pymongo import MongoClient
import sys
import os
import io
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import numpy as np

import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from crawler.config import MONGO_URI, DB_NAME, ARTICLES_COLLECTION
from analysis.zipf_analysis import ZIPF_COLLECTION

app = Flask(__name__)
app.secret_key = 'a_very_secret_key' # Needed for flash messages

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
articles_collection = db[ARTICLES_COLLECTION]
zipf_collection = db[ZIPF_COLLECTION]

@app.route('/')
def index():
    return redirect(url_for('search_page'))

@app.route('/articles', methods=['GET'])
def get_articles():
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    skip = (page - 1) * per_page
    articles = list(articles_collection.find().skip(skip).limit(per_page).sort("article_id"))
    for article in articles:
        article['_id'] = str(article['_id'])
    return render_template('articles.html', articles=articles)

@app.route('/articles/search', methods=['GET'])
def search_articles():
    query = request.args.get('q', '')
    if not query:
        return jsonify({"error": "Query parameter 'q' is required"}), 400
    results = list(articles_collection.find(
        {"title": {"$regex": query, "$options": "i"}},
        {"_id": 1, "title": 1, "url": 1}
    ))
    for result in results:
        result['_id'] = str(result['_id'])
    return jsonify(results)

@app.route('/stats', methods=['GET'])
def get_stats():
    total_docs = articles_collection.count_documents({})
    if total_docs == 0:
        stats_data = {"total_docs": 0, "avg_word_count": 0, "avg_char_count": 0}
        return render_template('stats.html', stats=stats_data)
    pipeline = [{"$group": {"_id": None, "avg_word_count": {"$avg": "$metadata.word_count"}, "avg_char_count": {"$avg": "$metadata.char_count"}}}]
    stats = list(articles_collection.aggregate(pipeline))
    stats_data = {
        "total_docs": total_docs,
        "avg_word_count": stats[0]['avg_word_count'] if stats else 0,
        "avg_char_count": stats[0]['avg_char_count'] if stats else 0
    }
    return render_template('stats.html', stats=stats_data)

@app.route('/zipf', methods=['GET'])
def get_zipf_table():
    limit = int(request.args.get('limit', 100))
    stats = list(zipf_collection.find({}, {"_id": 0}).sort("rank", 1).limit(limit))
    # Pass current timestamp to template to bust cache
    return render_template('zipf.html', stats=stats, limit=limit, timestamp=int(time.time()))

@app.route('/zipf/plot', methods=['GET'])
def get_zipf_plot():
    limit = int(request.args.get('limit', 10000))
    stats = list(zipf_collection.find(
        {"frequency": {"$gt": 1}}, 
        {"_id": 0, "rank": 1, "frequency": 1}
    ).sort("rank", 1).limit(limit))
    
    if not stats:
        return "Нет данных для построения графика. Сначала выполните расчет.", 404

    ranks = np.array([s['rank'] for s in stats])
    frequencies = np.array([s['frequency'] for s in stats])

    log_ranks = np.log(ranks)
    log_frequencies = np.log(frequencies)
    
    coeffs = np.polyfit(log_ranks, log_frequencies, 1)
    alpha = -coeffs[0]
    
    regression_line = np.exp(coeffs[1] + coeffs[0] * log_ranks)

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.loglog(ranks, frequencies, marker=".", linestyle='None', label='Фактические данные корпуса', alpha=0.5, markersize=5)
    ax.loglog(ranks, regression_line, linestyle='--', color='red', label=f'Идеальный закон Ципфа (α ≈ {alpha:.2f})')

    ax.set_title("Распределение по закону Ципфа (логарифмическая шкала)", fontsize=16)
    ax.set_xlabel("Ранг", fontsize=12)
    ax.set_ylabel("Частота", fontsize=12)
    ax.legend()
    ax.grid(True)
    
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    
    return Response(buf.getvalue(), mimetype='image/png')

@app.route('/search', methods=['GET', 'POST'])
def search_page():
    if request.method == 'POST':
        query = request.form.get('query', '')
        if query:
            from search.boolean_search import BooleanSearchEngine
            engine = BooleanSearchEngine()
            results, exec_time = engine.search(query)
            engine.close()
            return render_template('search.html', results=results, execution_time=f"{exec_time:.4f}", query=query)
    return render_template('search.html')

# --- Testing & CI/CD Routes ---

@app.route('/tests')
def tests_dashboard():
    report_path = os.path.join(os.path.dirname(__file__), '..', 'test_report.html')
    report_exists = os.path.exists(report_path)
    return render_template('tests.html', report_exists=report_exists)

@app.route('/tests/run')
def run_tests_endpoint():
    try:
        script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', 'run_tests.sh')
        subprocess.run(['bash', script_path], check=True, capture_output=True, text=True)
        flash('Тесты успешно выполнены! Отчет обновлен.', 'success')
    except subprocess.CalledProcessError as e:
        error_details = f"stdout: {e.stdout}\\nstderr: {e.stderr}"
        print(f"Error running tests script:\\n{error_details}")
        flash('Ошибка при запуске тестов! Подробности в консоли.', 'error')
    return redirect(url_for('tests_dashboard'))

@app.route('/tests/report')
def view_test_report():
    report_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return send_from_directory(report_dir, 'test_report.html')

@app.route('/coverage/')
def coverage_report():
    coverage_dir = os.path.join(os.path.dirname(__file__), '..', 'htmlcov')
    return send_from_directory(coverage_dir, 'index.html')

@app.route('/coverage/<path:path>')
def coverage_files(path):
    coverage_dir = os.path.join(os.path.dirname(__file__), '..', 'htmlcov')
    return send_from_directory(coverage_dir, path)

@app.route('/api/tokenize', methods=['POST'])
def api_tokenize():
    if not request.json or 'text' not in request.json:
        return jsonify({"error": "Request must be JSON with a 'text' field"}), 400
    text = request.json['text']
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tokenizer')))
    from stemmer_py import cpp_stemmer
    from nltk.tokenize import word_tokenize
    if cpp_stemmer.is_loaded:
        stemmer_func = cpp_stemmer.stem
    else:
        from nltk.stem.snowball import SnowballStemmer
        nltk_stemmer = SnowballStemmer("russian")
        stemmer_func = nltk_stemmer.stem
    tokens = word_tokenize(text, language='russian')
    cleaned_tokens = [token.lower() for token in tokens if token.isalpha()]
    stems = [stemmer_func(token) for token in cleaned_tokens]
    return jsonify({"tokens": cleaned_tokens, "stems": stems})

if __name__ == '__main__':
    app.run(debug=True, port=5000)
