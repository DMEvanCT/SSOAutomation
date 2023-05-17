import boto3
import os

ACCOUNTS_TABLE = os.getenv("ACCOUNTS_TABLE")
# This is only here because The python API does not support filtering with begin with
def lambda_handler(event, context):
    closed_account_id = event["accountId"]
    dynamo = boto3.resource('dynamodb')
    table = dynamo.Table(ACCOUNTS_TABLE)
    response = table.get_item(
        Key={
            'Id': closed_account_id
        }
    )
    if response is not None:
        table.delete_item(
            Key={
                'Id': closed_account_id
            }
        )
        print("Deleted Account: " + closed_account_id)
    else:
        print("Account not found: " + closed_account_id)


