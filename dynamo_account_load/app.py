import boto3
import cfnresponse


def lambda_handler(event, context):
    print(event)
    try:
        organizations = boto3.client("organizations")
        account_id = event["accountId"]
        org_account = organizations.describe_account(
            AccountId=account_id
        )
    except organizations.exceptions.AccessDeniedException as e:
        # @TODO turn this into actual logger vs print
        print(e)
        cfnresponse.send(event, context, cfnresponse.FAILED, "Access Denied")
    print("Printing OrgAccount:")
    org_account_info = org_account["Account"]
    dynamo = boto3.resource('dynamodb')
    del org_account_info["JoinedTimestamp"]
    del org_account_info["JoinedMethod"]
    # Insert into the AWSOrgAccounts Table in master
    try:
        table = dynamo.Table("AWSOrgAccounts")
        table.put_item(Item=org_account_info)
        cfnresponse.send(event, context, cfnresponse.SUCCESS, "Loaded Accounts Into Dynamo")
    except dynamo.exceptions.ProvisionedThroughputExceededException as e:
        print(e)
        cfnresponse.send(event,context, cfnresponse.FAILED, "Exceeded Provisioned Throughput")
    except dynamo.exceptions.RequestLimitExceeded as e:
        print(e)
        cfnresponse.send(event,context, cfnresponse.FAILED, "Exceeded Request Limit")
    except dynamo.exceptions.ResourceNotFoundException as e:
        print(e)
        cfnresponse.send(event,context, cfnresponse.FAILED, "Resource not found does table exist?")






