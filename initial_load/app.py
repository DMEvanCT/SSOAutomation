# Used for Initial Dynamo DB load of account names ids and emails.

import boto3


def lambda_handler(event, context):
    organizations = boto3.client("organizations")
    accounts = organizations.list_accounts()
    dynamo = boto3.resource('dynamodb')
    # This part is kind of slow, but it's okay.
    for account in accounts["Accounts"]:
        del account["JoinedTimestamp"]
        del account["JoinedMethod"]
        # Insert into the AWSOrgAccounts Table in master
        table = dynamo.Table("AWSOrgAccounts")
        table.put_item(Item=account)







        