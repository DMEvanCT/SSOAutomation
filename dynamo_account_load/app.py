import boto3


def lambda_handler(event, context):
    try:
        organizations = boto3.client("organizations")
        account_id = event["accountId"]
        org_account = organizations.describe_account(
            AccountId=account_id
        )
    except organizations.exceptions.AccessDeniedException as e:
        # @TODO turn this into actual logger vs print
        print(e)
    print("Printing OrgAccount:")
    org_account_info = org_account["Account"]
    dynamo = boto3.resource('dynamodb')
    del org_account_info["JoinedTimestamp"]
    del org_account_info["JoinedMethod"]
    # Insert into the AWSOrgAccounts Table in master
    try:
        table = dynamo.Table("AWSOrgAccounts")
        table.put_item(Item=org_account_info)
    except dynamo.exceptions.ProvisionedThroughputExceededException as e:
        print(e)
    except dynamo.exceptions.RequestLimitExceeded as e:
        print(e)
    except dynamo.exceptions.ResourceNotFoundException as e:
        print(e)








