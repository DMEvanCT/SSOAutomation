import boto3
import os


SSO_ASSOCIATE_QUEUE_URL = os.getenv("SSO_ASSOCIATE_QUEUE_URL")


def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    ssoadmin_client = boto3.client("sso-admin")
    #dynamodb = boto3.resource('dynamodb')

    # Get SQS messages in batches of 10 messages
    sqs_message = sqs.receive_message(
        QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20
    )
    messages = 0
    assignment_status = None
    while messages < len(sqs_message["Messages"]):
        message = sqs_message["Messages"][messages]
        while assignment_status != "SUCCEEDED" or assignment_status != "FAILED":
            print("Checking status")
            check_status = ssoadmin_client.describe_permission_set_provisioning_status(
                InstanceArn='string',
                ProvisionPermissionSetRequestId=message["Body"]["AccountAssignmentCreationStatus"]["RequestId"]
            )
            assignment_status = check_status["Status"]
        # Delete the message from the queue
        sqs.delete_message(
            QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"]
        )
        messages += 1

