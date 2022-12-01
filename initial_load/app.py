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
                message = {"message": "Exceeded Provisioned Throughput"}
                cfnresponse.send(event, context, cfnresponse.FAILED, message)
            except dynamo.exceptions.RequestLimitExceeded as e:
                print(e)
                message = {"message": "Request Limit Exceeded"}
                cfnresponse.send(event, context, cfnresponse.FAILED, message)
            except dynamo.exceptions.ResourceNotFoundException as e:
                print(e)
                message = {"message": "Resource Not found"}
                cfnresponse.send(event, context, cfnresponse.FAILED, message)

    message = {"message": "All set! Everything is loaded!"}
    cfnresponse.send(event, context, cfnresponse.SUCCESS, message)
    if event["RequestType"] == "Delete":
        message = {"message": "Nothing to do here!"}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, message)
    if event["RequestType"] == "Update":
        message = {"message": "Nothing to do here!"}
        cfnresponse.send(event, context, cfnresponse.SUCCESS, message)
