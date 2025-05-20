from flask import Flask, jsonify, request
from flask_cors import CORS
import yaml
from datetime import datetime
import os
import sys
import subprocess
import threading
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from alternator.alternator_client import AlternatorWikipediaClient

app = Flask(__name__)
CORS(app)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), 'config.yaml')
TEST_RESULTS_PATH = os.path.join(os.path.dirname(__file__), 'pytest_results.json')
TEST_RUNNING_FLAG = os.path.join(os.path.dirname(__file__), 'pytest_running.flag')

def load_config():
    with open(CONFIG_PATH, 'r') as f:
        return yaml.safe_load(f)
    
def get_client():
    return AlternatorWikipediaClient(load_config().get('alternator', {})['endpoint_url'])
#client.create_articles_table()

def get_reader():
    from wikipedia.multistream import WikipediaMultistreamReader
    config = load_config()
    wikipedia_cfg = config.get('wikipedia', {})
    xml_path = wikipedia_cfg.get('dump')
    index_path = wikipedia_cfg.get('index')
    return WikipediaMultistreamReader(xml_path, index_path)

@app.route('/api/deadline')
def get_deadline():
    config = load_config()
    deadline = config.get('deadline')
    return jsonify({'deadline': deadline})

@app.route('/api/wikipedia-index')
def get_wikipedia_index():
    start = int(request.args.get('start', 0))
    count = int(request.args.get('count', 10))
    reader = get_reader()
    entries = reader.list_index_entries(start=start, count=count)
    return jsonify({'entries': entries})

@app.route('/api/wikipedia-articles')
def get_wikipedia_articles():
    start = int(request.args.get('start', 0))
    count = int(request.args.get('count', 10))
    reader = get_reader()
    articles = reader.list_articles_by_index(start=start, count=count)
    # Return as list of dicts for JSON
    # Check which articles exist in Alternator
    titles = [title for title, _ in articles]
    client = get_client()
    existing_titles = set(client.check_articles_exist(titles))
    articles_json = [
        {'index': start + i, 'title': title, 'text': text, 'alternator': title in existing_titles}
        for i, (title, text) in enumerate(articles)
    ]
    return jsonify({'articles': articles_json})

@app.route('/api/alternator-wikipedia-table', methods=['DELETE'])
def delete_alternator_wikipedia_table():
    client = get_client()
    client.delete_articles_table()
    return jsonify({'status': 'deleted'})

@app.route('/api/alternator-wikipedia-article', methods=['POST'])
def add_alternator_wikipedia_article():
    index = int(request.json.get('index'))
    reader = get_reader()
    articles = reader.list_articles_by_index(start=index, count=1)
    if not articles:
        return jsonify({'error': 'Article not found'}), 404
    title, text = articles[0]
    client = get_client()
    client.add_article(title, text)
    return jsonify({'status': 'added', 'title': title})

@app.route('/api/alternator-wikipedia-article', methods=['DELETE'])
def remove_alternator_wikipedia_article():
    title = request.json.get('title')
    if not title:
        return jsonify({'error': 'Missing title'}), 400
    client = get_client()
    client.remove_articles([title])
    return jsonify({'status': 'removed', 'title': title})

@app.route('/api/get_articles_page_from', methods=['GET'])
def get_alternator_wikipedia_articles_page():
    """
    API endpoint to fetch a page of articles from Alternator using the new paging method.
    Query params:
        start_title (optional): The title to start from (exclusive).
        count (optional): Number of articles to fetch (default 10).
        forward (optional): 'true' for A-Z, 'false' for Z-A (default 'true').
    """
    start_title = request.args.get('start_title')
    count = int(request.args.get('count', 10))
    client = get_client()
    articles = client.get_articles_page_from(start_title=start_title, page_size=count)
    return jsonify({'articles': articles})

@app.route('/api/query-articles', methods=['GET'])
def query_articles():
    """
    Query articles in Alternator using a KeyConditionExpression string and return a list of articles (title, text).
    Query params:
        string_query (required): The KeyConditionExpression as a string (e.g., "boto3.dynamodb.conditions.Key('title').eq('SomeTitle')")
        limit (optional): Max number of results to return.
    """
    string_query = request.args.get('string_query')
    if not string_query:
        return jsonify({'error': 'Missing string_query parameter'}), 400
    limit = request.args.get('limit')
    client = get_client()
    kwargs = {}
    if limit:
        try:
            kwargs['Limit'] = int(limit)
        except Exception:
            pass
    try:
        articles = client.query_articles(string_query, **kwargs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    return jsonify({'articles': articles})

def run_pytest_and_store_results():
    """Run pytest and store results in a file, updating as tests progress."""
    import json
    with open(TEST_RUNNING_FLAG, 'w') as f:
        f.write('running')
    try:
        proc = subprocess.Popen([
            sys.executable, '-m', 'pytest', '../../test', '--json-report', '--json-report-file', TEST_RESULTS_PATH
        ], cwd=os.path.dirname(__file__), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        # Stream output and update partial results
        partial = ''
        while True:
            line = proc.stdout.readline()
            if not line:
                break
            partial += line
            # Optionally, write partial output to a file for frontend polling
            with open(TEST_RESULTS_PATH + '.partial', 'w') as f:
                f.write(partial)
        proc.wait()
    finally:
        if os.path.exists(TEST_RUNNING_FLAG):
            os.remove(TEST_RUNNING_FLAG)

@app.route('/api/run-tests', methods=['POST'])
def api_run_tests():
    if os.path.exists(TEST_RUNNING_FLAG):
        return jsonify({'status': 'running'})
    thread = threading.Thread(target=run_pytest_and_store_results, daemon=True)
    thread.start()
    return jsonify({'status': 'started'})

@app.route('/api/test-results', methods=['GET'])
def api_test_results():
    import json
    running = os.path.exists(TEST_RUNNING_FLAG)
    results = None
    partial = None
    # Always try to read partial output if available
    if os.path.exists(TEST_RESULTS_PATH + '.partial'):
        with open(TEST_RESULTS_PATH + '.partial', 'r') as f:
            partial = f.read()
    # Only try to read results if the file is non-empty and valid JSON
    if os.path.exists(TEST_RESULTS_PATH) and os.path.getsize(TEST_RESULTS_PATH) > 0:
        with open(TEST_RESULTS_PATH, 'r') as f:
            try:
                results = json.load(f)
            except Exception as e:
                # If the file is not valid JSON, include the error in partial
                if partial is None:
                    partial = ''
                partial += f"\n[Error reading JSON results: {e}]"
                results = None
    return jsonify({'running': running, 'results': results, 'partial': partial})

@app.route('/api/has-wikipedia-config', methods=['GET'])
def has_wikipedia_config():
    config = load_config()
    has_wikipedia = 'wikipedia' in config and config['wikipedia'] is not None
    return jsonify({'has_wikipedia': has_wikipedia})

if __name__ == '__main__':
    app.run(debug=True)
