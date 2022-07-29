import boto3


def lambda_handler(event, context):
    print(event)
    organizations = boto3.client("organizations")
    account_id = event["accountId"]
    org_account = organizations.describe_account(
        AccountId=account_id
    )
    print("Printing OrgAccount:")
    org_account_info = org_account["Account"]
    dynamo = boto3.resource('dynamodb')
    del org_account_info["JoinedTimestamp"]
    del org_account_info["JoinedMethod"]
    client = boto3.resource('dynamodb')
    # Insert into the AWSOrgAccounts Table in master
    table = dynamo.Table("AWSOrgAccounts")
    table.put_item(Item=org_account_info)

