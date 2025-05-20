"""
alternator_client.py
A Python library to wrap boto3 for communicating with ScyllaDB Alternator.
"""
import boto3
from botocore.config import Config

class AlternatorClient:
    def __init__(self, endpoint_url):
        self.dynamodb = boto3.resource(
            'dynamodb',
            endpoint_url=endpoint_url
        )

    def create_table(self, table_name, key_schema, attribute_definitions):
        """
        Create a table in Alternator.
        Args:
            table_name (str): Name of the table.
            key_schema (list): Key schema for the table.
            attribute_definitions (list): Attribute definitions.
        Returns:
            Table resource.
        """
        table = self.dynamodb.create_table(
            BillingMode = 'PAY_PER_REQUEST',
            TableName=table_name,
            KeySchema=key_schema,
            AttributeDefinitions=attribute_definitions
        )
        table.wait_until_exists()
        return table

    def add_rows(self, table_name, items):
        """
        Add multiple rows (items) to the specified table.
        Args:
            table_name (str): Name of the table.
            items (list of dict): List of items to add.
        Returns:
            List of responses from DynamoDB.
        """
        table = self.dynamodb.Table(table_name)
        with table.batch_writer() as batch:
            for item in items:
                batch.put_item(Item=item)
        # batch_writer does not return responses for each item, so just return True for success
        return True

    def remove_rows(self, table_name, keys):
        """
        Remove multiple rows from the specified table by primary keys.
        Args:
            table_name (str): Name of the table.
            keys (list of dict): List of primary key dicts to delete.
        Returns:
            None
        """
        if not keys:
            return
        table = self.dynamodb.Table(table_name)
        with table.batch_writer() as batch:
            for key in keys:
                batch.delete_item(Key=key)

    def delete_table(self, table_name):
        """
        Delete a table in Alternator.
        Args:
            table_name (str): Name of the table to delete.
        Returns:
            Response from DynamoDB.
        """
        table = self.dynamodb.Table(table_name)
        response = table.delete()
        table.wait_until_not_exists()
        return response

    def get_rows(self, table_name, keys=None, projection_expression=None):
        """
        Retrieve rows from the specified table.
        If keys is provided, use batch_get_item for efficient retrieval of multiple items by primary key.
        Optionally, use projection_expression to fetch only specific columns.
        Args:
            table_name (str): Name of the table.
            keys (list of dict, optional): List of primary key dicts for batch retrieval.
            projection_expression (str, optional): Columns to fetch (e.g., 'title').
        Returns:
            List of items (rows).
        """
        if keys is None or not keys:
            return []
        request = {'Keys': keys}
        if projection_expression:
            request['ProjectionExpression'] = projection_expression
        request_items = {table_name: request}
        response = self.dynamodb.meta.client.batch_get_item(RequestItems=request_items)
        return response['Responses'].get(table_name, [])

    def query_table(self, table_name, key_condition_expression, index_name=None, **kwargs):
        """
        Query the specified table with a KeyConditionExpression string.
        Args:
            table_name (str): Name of the table.
            key_condition_expression (str): KeyConditionExpression as a string.
            index_name (str, optional): Name of the index to use.
            **kwargs: Additional arguments to pass to the query.
        Returns:
            List of items (rows).
        """
        table = self.dynamodb.Table(table_name)
        query_kwargs = {
            'KeyConditionExpression': key_condition_expression
        }
        if index_name:
            query_kwargs['IndexName'] = index_name
        query_kwargs.update(kwargs)
        response = table.query(**query_kwargs)
        return response.get('Items', [])

class AlternatorWikipediaClient(AlternatorClient):
    """
    Specialized client for a Wikipedia articles table in Alternator.
    The table has a string primary key 'title' and a string column 'text'.
    """
    TABLE_NAME = 'wikipedia_articles'
    KEY_SCHEMA = [
        {'AttributeName': 'title', 'KeyType': 'HASH'}
    ]
    ATTRIBUTE_DEFINITIONS = [
        {'AttributeName': 'title', 'AttributeType': 'S'}
    ]

    def create_articles_table(self):
        """
        Create the Wikipedia articles table if it does not exist.
        If the table already exists and is correct, do not fail.
        """
        from botocore.exceptions import ClientError
        try:
            return self.create_table(
                self.TABLE_NAME,
                self.KEY_SCHEMA,
                self.ATTRIBUTE_DEFINITIONS
            )
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceInUseException':
                # Table already exists, check if schema is correct (optional: could add schema validation here)
                return self.dynamodb.Table(self.TABLE_NAME)
            else:
                raise

    def _handle_table_not_exists(self, func, *args, **kwargs):
        """
        Helper to call a function, create table if ResourceNotFoundException, and retry once.
        """
        from botocore.exceptions import ClientError
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                self.create_articles_table()
                return func(*args, **kwargs)
            else:
                raise

    def _quitely_handle_table_not_exists(self, func, *args, **kwargs):
        """
        Helper to call a function, ignore if ResourceNotFoundException, else raise.
        """
        from botocore.exceptions import ClientError
        try:
            return func(*args, **kwargs)
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'ResourceNotFoundException':
                return None
            else:
                raise

    def add_article(self, title, text):
        """
        Add a single Wikipedia article.
        """
        item = {'title': title, 'text': text}
        return self._handle_table_not_exists(self.add_rows, self.TABLE_NAME, [item])

    def add_articles(self, articles):
        """
        Add multiple Wikipedia articles.
        Args:
            articles (list of dict): Each dict must have 'title' and 'text'.
        """
        items = [{'title': a['title'], 'text': a['text']} for a in articles]
        return self._handle_table_not_exists(self.add_rows, self.TABLE_NAME, items)

    def get_article(self, title):
        """
        Retrieve a Wikipedia article by title.
        """
        def get():
            items = self.get_rows(self.TABLE_NAME, keys=[{'title': title}])
            return items[0] if items else None
        return self._handle_table_not_exists(get)

    def get_articles(self, titles):
        """
        Retrieve Wikipedia articles by a list of titles.
        Args:
            titles (list of str): List of article titles to retrieve.
        Returns:
            List of article items.
        """
        def get():
            keys = [{'title': t} for t in titles]
            return self.get_rows(self.TABLE_NAME, keys=keys)
        return self._handle_table_not_exists(get)

    def remove_articles(self, titles):
        """
        Remove articles from the database by a list of titles.
        Args:
            titles (list of str): List of article titles to remove.
        Returns:
            None
        """
        def remove():
            keys = [{'title': t} for t in titles]
            return self.remove_rows(self.TABLE_NAME, keys)
        return self._quitely_handle_table_not_exists(remove)

    def delete_articles_table(self):
        """
        Delete the Wikipedia articles table. Ignore if table does not exist.
        """
        def delete():
            return self.delete_table(self.TABLE_NAME)
        return self._quitely_handle_table_not_exists(delete)

    def check_articles_exist(self, titles):
        """
        Check which articles from the given list of titles exist in the database.
        Only returns the list of existing titles, does not fetch the text column.
        Args:
            titles (list of str): List of article titles to check.
        Returns:
            List of titles that exist in the database.
        """
        def get():
            keys = [{'title': t} for t in titles]
            items = self.get_rows(self.TABLE_NAME, keys=keys, projection_expression='title')
            return [item['title'] for item in items if 'title' in item]
        return self._quitely_handle_table_not_exists(get) or []

    def get_articles_page_from(self, start_title=None, page_size=10):
        """
        Fetch a page of articles starting from a given title, in forward order only.
        Args:
            start_title (str or None): The title to start from (exclusive). If None, starts from the beginning.
            page_size (int): Number of articles to fetch.
        Returns:
            List of article items (dicts with 'title' and 'text').
        """
        def get():
            table = self.dynamodb.Table(self.TABLE_NAME)
            scan_kwargs = {
                'ProjectionExpression': 'title, text',
                'Limit': page_size
            }
            if start_title:
                scan_kwargs['ExclusiveStartKey'] = {'title': start_title}
            response = table.scan(**scan_kwargs)
            return response.get('Items', [])
        return self._handle_table_not_exists(get)

    def query_articles(self, key_condition_expression, **kwargs):
        """
        Query the Wikipedia articles table using the OpenSearch index and a KeyConditionExpression string.
        Returns a list of dicts with 'title' and 'text'.
        Args:
            key_condition_expression (str): KeyConditionExpression as a string.
            **kwargs: Additional arguments to pass to the query.
        Returns:
            List of article items (dicts with 'title' and 'text').
        """
        items = self.query_table(
            self.TABLE_NAME,
            key_condition_expression,
            index_name="OpenSearch",
            **kwargs
        )
        # Only return dicts with 'title' and 'text' keys
        return [
            {'title': item.get('title'), 'text': item.get('text')}
            for item in items if 'title' in item and 'text' in item
        ]
