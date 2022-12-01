# Used for Initial Dynamo DB load of account names ids and emails.

import boto3
import cfnresponse

def lambda_handler(event, context):
    if event["RequestType"] == "Create":
        organizations = boto3.client("organizations")
        accounts = organizations.list_accounts()
        dynamo = boto3.resource('dynamodb')
        # This part is kind of slow, but it's okay.
        for account in accounts["Accounts"]:
            del account["JoinedTimestamp"]
            del account["JoinedMethod"]
            try:
                # Insert into the AWSOrgAccounts Table in master
                table = dynamo.Table("AWSOrgAccounts")
                table.put_item(Item=account)
            except dynamo.exceptions.ProvisionedThroughputExceededException as e:
                print(e)
                cfnresponse.send(event, context, cfnresponse.FAILED, "Exceeded Provisioned Throughput")
            except dynamo.exceptions.RequestLimitExceeded as e:
                print(e)
                cfnresponse.send(event, context, cfnresponse.FAILED, "Exceeded Request Limit")
            except dynamo.exceptions.ResourceNotFoundException as e:
                print(e)
    if event["RequestType"] == "Delete":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, "Nothing to do here!")
    if event["RequestType"] == "Update":
        cfnresponse.send(event, context, cfnresponse.SUCCESS, "Nothing to do here!")









        