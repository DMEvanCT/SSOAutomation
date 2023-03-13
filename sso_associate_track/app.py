import boto3
import os


SSO_ASSOCIATE_QUEUE_URL = os.getenv("SSO_ASSOCIATE_QUEUE_URL")


def lambda_handler(event, context):
    sqs = boto3.client('sqs')
    #dynamodb = boto3.resource('dynamodb')

    # Get SQS messages in batches of 10 messages
    sqs_message = sqs.receive_message(
        QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
        MaxNumberOfMessages=10,
        WaitTimeSeconds=20
    )
    messages = 0
    while messages < len(sqs_message["Messages"]):
        message = sqs_message["Messages"][messages]
        print(message)
        # Delete the message from the queue
        sqs.delete_message(
            QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
            ReceiptHandle=message["ReceiptHandle"]
        )
        messages += 1

