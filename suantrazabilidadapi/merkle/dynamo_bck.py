import boto3
from botocore.exceptions import NoCredentialsError, PartialCredentialsError

from suantrazabilidadapi.utils.exception import ResponseDynamoDBException
from suantrazabilidadapi.utils.generic import Constants

class DynamoDBClient(Constants):
    def __init__(self, region_name: str = "us-east-2"):
        try:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=region_name,
                aws_access_key_id=self.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=self.AWS_SECRET_ACCESS_KEY
            )
        except (NoCredentialsError, PartialCredentialsError) as e:
            raise ResponseDynamoDBException(f"Credentials error: {e}")

    def get_item(self, table_name: str, key: dict) -> dict:
        try:
            table = self.dynamodb.Table(table_name)
            response = table.get_item(Key=key)
            return response.get('Item', {})
        except Exception as e:
            raise ResponseDynamoDBException(f"Error getting item: {e}")

    def put_item(self, table_name: str, item: dict) -> bool:
        try:
            table = self.dynamodb.Table(table_name)
            table.put_item(Item=item)
            return True
        except Exception as e:
            raise ResponseDynamoDBException(f"Error putting item: {e}")

    def delete_item(self, table_name: str, key: dict) -> bool:
        try:
            table = self.dynamodb.Table(table_name)
            table.delete_item(Key=key)
            return True
        except Exception as e:
            raise ResponseDynamoDBException(f"Error deleting item: {e}")

    def update_item(self, table_name: str, key: dict, update_expression: str, expression_attribute_values: dict) -> bool:
        try:
            table = self.dynamodb.Table(table_name)
            table.update_item(
                Key=key,
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_attribute_values
            )
            return True
        except Exception as e:
            raise ResponseDynamoDBException(f"Error updating item: {e}")

    def query_items(self, table_name: str, filter_expression) -> list:
        try:
            table = self.dynamodb.Table(table_name)
            response = table.scan(
                FilterExpression=filter_expression
            )
            return response.get('Items', [])
        except Exception as e:
            raise ResponseDynamoDBException(f"Error querying item: {e}")
# Example usage:
# dynamo_client = DynamoDBClient(region_name='us-west-2', aws_access_key_id='YOUR_ACCESS_KEY', aws_secret_access_key='YOUR_SECRET_KEY')
# item = dynamo_client.get_item('your_table_name', {'your_key': 'your_value'})
# success_put = dynamo_client.put_item('your_table_name', {'your_key': 'your_value', 'other_attribute': 'value'})
# success_delete = dynamo_client.delete_item('your_table_name', {'your_key': 'your_value'})
# success_update = dynamo_client.update_item('your_table_name', {'your_key': 'your_value'}, 'SET other_attribute = :val1', {':val1': 'new_value'})
# items = dynamo_client.query_items(
#     'your_table_name',
#     Key('your_partition_key').eq('your_value') & Key('your_sort_key').begins_with('prefix'),
#     {':val1': 'your_value', ':val2': 'prefix'}
# )