import sys
import os
import importlib
import pytest
import yaml
import time

# Import AlternatorWikipediaClient
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../alternator')))
alternator_client_mod = importlib.import_module('alternator_client')
AlternatorWikipediaClient = alternator_client_mod.AlternatorWikipediaClient

# Import TextSearchClient
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../text_search')))
text_search_client_mod = importlib.import_module('text_search_client')
TextSearchClient = text_search_client_mod.TextSearchClient

@pytest.fixture(scope="module")
def alternator_settings():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../webui/backend/config.yaml'))
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['alternator']

@pytest.fixture(scope="module")
def alternator_client(alternator_settings):
    cl = AlternatorWikipediaClient(endpoint_url=alternator_settings['endpoint_url'])
    cl.TABLE_NAME = "TestArticles"
    return cl

@pytest.fixture(scope="module")
def text_search_settings():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../webui/backend/config.yaml'))
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['text-search']

@pytest.fixture(scope="module")
def text_search_client(text_search_settings):
    cl = TextSearchClient(endpoint_url=text_search_settings['endpoint_url'])
    return cl

def retry_assert(tried_fn, retries=5, delay=1):
    for attempt in range(retries):
        try:
            tried_fn()
            break
        except AssertionError:
            if attempt == retries - 1:
                raise
            time.sleep(delay)

def x_test_search_multiple_articles(alternator_client, text_search_client):
    try:
        alternator_client.delete_articles_table()
        alternator_client.create_articles_table()
        text_search_client.create_index()
        # Add articles
        articles = [
            {"title": "find1", "text": "The quick brown fox jumps over the lazy dog."},
            {"title": "find2", "text": "A fast brown fox leaps above a sleepy dog."},
            {"title": "notfind1", "text": "Completely unrelated sentence about cats."},
            {"title": "notfind2", "text": "Another line about birds and trees."}
        ]
        alternator_client.add_articles(articles)
        # Add to text search index as well
        for article in articles:
            text_search_client.add_item(article["title"], article["text"])
        def tried():
            results = alternator_client.query_articles("brown fox")
            assert isinstance(results, list)
            assert "find1" in results
            assert "find2" in results
            assert "notfind1" not in results
            assert "notfind2" not in results
        retry_assert(tried)
    finally:
        alternator_client.delete_articles_table()
        # Optionally clean up text search index
        # text_search_client.delete_index()
