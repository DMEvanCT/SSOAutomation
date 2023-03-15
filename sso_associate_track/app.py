import boto3
import os


SSO_ASSOCIATE_QUEUE_URL = os.getenv("SSO_ASSOCIATE_QUEUE_URL")
SSO_INSTANCE_ARN = os.getenv("SSO_INSTANCE_ARN")


def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    ssoadmin_client = boto3.client("sso-admin")
    dynamodb = boto3.resource('dynamodb')

    # Get SQS messages in batches of 10 messages
    sqs_message = sqs.receive_message(
        QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20
    )
    messages = 0
    print(sqs_message)
    assignment_status = None
    while messages < len(sqs_message["Messages"]):
        message = sqs_message["Messages"][messages]
        print(message)
        while assignment_status != "SUCCEEDED" or assignment_status != "FAILED":
            print("Checking status")
            check_status = ssoadmin_client.describe_permission_set_provisioning_status(
                InstanceArn=SSO_INSTANCE_ARN,
                ProvisionPermissionSetRequestId=message["Body"]["AccountAssignmentCreationStatus"]["RequestId"]
            )
            assignment_status = check_status["Status"]
        recordedInfo = {"RequestID": message["Body"]["AccountAssignmentCreationStatus"]["RequestId"],
                        "AccountName": message["Body"]["AccountName"], "AccountId": message["Body"]["AccountId"],
                        "PermissionSet": message["Body"]["PermissionSet"], "Status": assignment_status,
                        "Timestamp": message["Body"]["AccountAssignmentCreationStatus"]["CreatedDate"],
                        "ProvisionType": message["Body"]["ProvisionType"]}
        try:
            table = dynamodb.Table("AWSSSOAutoAssignments")
            table.put_item(Item=recordedInfo)
        except dynamodb.exceptions.ProvisionedThroughputExceededException as e:
            print(e)
        except dynamodb.exceptions.RequestLimitExceeded as e:
            print(e)
        except dynamodb.exceptions.ResourceNotFoundException as e:
            print(e)
        # Delete the message from the queue
        sqs.delete_message(
            QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"]
        )
        messages += 1

