import requests

class TextSearchClient:
    INDEX = "OpenSearch"

    def __init__(self, endpoint_url):
        self.endpoint_url = endpoint_url.rstrip('/')

    def create_index(self):
        """
        Create a new empty index (fixed: OpenSearch).
        Returns:
            Response object or None.
        """
        url = f"{self.endpoint_url}/api/v1/text-search/{self.INDEX}"
        response = requests.put(url)
        response.raise_for_status()
        return response.json() if response.content else None

    def add_item(self, item_id, text):
        """
        Add a new item with text to the OpenSearch index.
        Args:
            item_id (str): ID of the item.
            text (str): Text to index.
        Returns:
            Response object or None.
        """
        url = f"{self.endpoint_url}/api/v1/text-search/{self.INDEX}/add"
        payload = {"id": item_id, "text": text}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json() if response.content else None

    def search(self, text, limit=10):
        """
        Search for similar items in the OpenSearch index.
        Args:
            text (str): Query text.
            limit (int): Max number of results.
        Returns:
            List of item IDs (strings).
        """
        url = f"{self.endpoint_url}/api/v1/text-search/{self.INDEX}/search"
        payload = {"text": text, "limit": limit}
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()

    def delete_index(self):
        """
        Delete the OpenSearch index.
        Returns:
            Response object or None.
        """
        url = f"{self.endpoint_url}/api/v1/text-search/{self.INDEX}"
        response = requests.delete(url)
        response.raise_for_status()
        return response.json() if response.content else None
