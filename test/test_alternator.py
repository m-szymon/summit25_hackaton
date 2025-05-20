import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../alternator')))
import importlib
alternator_client = importlib.import_module('alternator_client')
AlternatorWikipediaClient = alternator_client.AlternatorWikipediaClient
import pytest
import yaml

@pytest.fixture(scope="module")
def alternator_settings():
    # Use absolute path to config.yaml for reliability
    config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../webui/backend/config.yaml'))
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config['alternator']

@pytest.fixture(scope="module")
def alternator_client(alternator_settings):
    cl = AlternatorWikipediaClient(endpoint_url=alternator_settings['endpoint_url'])
    cl.TABLE_NAME = "TestArticles"
    return cl

def test_write_and_read_article(alternator_client):
    alternator_client.delete_articles_table()
    article = {"title": "TestArticle", "text": "This is a test."}
    alternator_client.add_articles([article])
    # Read back
    result = alternator_client.get_article("TestArticle")
    assert result is not None
    assert result["title"] == "TestArticle"
    assert result["text"] == "This is a test."
    # Clean up after test
    alternator_client.remove_articles(["TestArticle"])
