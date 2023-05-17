import boto3
import os
from aws_lambda_powertools import Logger

logger = Logger(service="sso-auto-assign")

ACCOUNTS_TABLE = os.getenv("ACCOUNTS_TABLE")

def lambda_handler(event, context):
    def log_exception(exception):
        logger.info(exception)

    try:
        organizations = boto3.client("organizations")
        account_id = event["accountId"]
        org_account = organizations.describe_account(AccountId=account_id)
    except organizations.exceptions.AccessDeniedException as e:
        log_exception(e)
        return

    print("Printing OrgAccount:")
    org_account_info = org_account["Account"]
    dynamo = boto3.resource('dynamodb')
    org_account_info.pop("JoinedTimestamp", None)
    org_account_info.pop("JoinedMethod", None)

    try:
        table = dynamo.Table(ACCOUNTS_TABLE)
        table.put_item(Item=org_account_info)
    except dynamo.exceptions.ProvisionedThroughputExceededException as e:
        log_exception(e)
    except dynamo.exceptions.RequestLimitExceeded as e:
        log_exception(e)
    except dynamo.exceptions.ResourceNotFoundException as e:
        log_exception(e)
