from flask import Flask, render_template, request

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search')
def search():
    q = request.args.get('q','')
    # заглушка: результаты пустые
    results = []
    return render_template('results.html', query=q, results=results)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
