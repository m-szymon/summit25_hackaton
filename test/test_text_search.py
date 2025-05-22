import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../text_search')))
import importlib
text_search_client_mod = importlib.import_module('text_search_client')
TextSearchClient = text_search_client_mod.TextSearchClient
import pytest
import yaml
import time

@pytest.fixture(scope="module")
def text_search_settings():
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../webui/backend/config.yaml'))
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['text-search']

@pytest.fixture(scope="module")
def text_search_client(text_search_settings):
    cl = TextSearchClient(endpoint_url=text_search_settings['endpoint_url'])
    cl.INDEX = "testindex"
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

def test_create_add_search_delete(text_search_client):
    try:
        # Clean up before test
        #text_search_client.delete_index()
        # Create index
        text_search_client.create_index()
        # Add item
        item_id = "test1"
        text = "This is a test document."
        text_search_client.add_item(item_id, text)
        def tried():
            results = text_search_client.search("test document", limit=5)
            assert isinstance(results, list)
            assert item_id in results
        retry_assert(tried)
    finally:
        # Clean up after test
        #text_search_client.delete_index()
        pass


def test_search_multiple_items(text_search_client):
    try:
        #text_search_client.delete_index()
        text_search_client.create_index()
        # Add items
        items = [
            ("find1", "The quick brown fox jumps over the lazy dog."),
            ("find2", "A fast brown fox leaps above a sleepy dog."),
            ("notfind1", "Completely unrelated sentence about cats."),
            ("notfind2", "Another line about birds and trees.")
        ]
        for item_id, text in items:
            text_search_client.add_item(item_id, text)
        def tried():
            results = text_search_client.search("brown fox", limit=10)
            assert isinstance(results, list)
            assert "find1" in results
            assert "find2" in results
            assert "notfind1" not in results
            assert "notfind2" not in results
        retry_assert(tried)
    finally:
        #text_search_client.delete_index()
        pass

