import json
import os
import boto3
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger

MAX_RETURN_PERMISSION_SET = os.getenv("MAX_RETURN_PERMISSION_SET")
SSO_INSTANCE_ARN = os.getenv("SSO_INSTANCE_ARN")
DIRECTORY_SERVICE_ID = os.getenv("DIRECTORY_SERVICE_ID")
SSO_ASSOCIATE_QUEUE_URL = os.getenv("SSO_ASSOCIATE_QUEUE_URL")
ACCOUNTS_TABLE = os.getenv("ACCOUNTS_TABLE")

logger = Logger(service="sso-auto-assign")

class DynamoQueries:
    def get_account_name(self, account_id):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(ACCOUNTS_TABLE)
        response = table.query(
            IndexName='AccountNameIndex',
            KeyConditionExpression=Key('Id').eq(account_id)
        )

        return response["Items"][0]["Name"]

    def get_account_id_from_name(self, account_name):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table(ACCOUNTS_TABLE)
        response = table.query(
            IndexName='AccountNameIndex',
            KeyConditionExpression=Key('Name').eq(account_name)
        )

        return response["Items"][0]["Id"]

    def get_dynamo_org_groups(self):
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('ORGSSOGroups')
        response = table.scan()
        return response["Items"]


def get_perm_id_from_name(perms, permission_set_name, ssoadmin_client):
    for perm in perms["PermissionSets"]:
        perm_details = ssoadmin_client.describe_permission_set(
            InstanceArn=SSO_INSTANCE_ARN,
            PermissionSetArn=perm
        )

        if perm_details["PermissionSet"]["Name"] == permission_set_name:
            return perm_details["PermissionSet"]["PermissionSetArn"]


def get_all_account_ids(accounts_list):
    all_accounts_org = []
    for account in accounts_list:
        all_accounts_org.append({"AccountId": account["Id"], "AccountName": account["Name"]})
    return all_accounts_org


def get_group_by_group_name(group_name):
    identity_services_client = boto3.client("identitystore")
    group_info = identity_services_client.list_groups(
        IdentityStoreId=DIRECTORY_SERVICE_ID,
        Filters=[
            {
                'AttributePath': 'DisplayName',
                'AttributeValue': group_name
            },
        ]
    )

    return group_info["Groups"][0]["GroupId"]


def associate_sso(sso_instance_arn, account_id, perm_set_arn, group_id):
    ssoadmin_client = boto3.client("sso-admin")
    response = ssoadmin_client.create_account_assignment(
        InstanceArn=sso_instance_arn,
        TargetId=account_id,
        TargetType='AWS_ACCOUNT',
        PermissionSetArn=perm_set_arn,
        PrincipalType='GROUP',
        PrincipalId=group_id
    )
    return response


def lambda_handler(event, context):
    event_name = event["eventName"]
    dynamo = DynamoQueries()

    if event_name == "CreateGroup":
        ssoadmin_client = boto3.client("sso-admin")
        sqs = boto3.client("sqs")
        organizations = boto3.client("organizations")

        get_perm_sets = ssoadmin_client.list_permission_sets(
            InstanceArn=SSO_INSTANCE_ARN,
            MaxResults=100
        )

        group = event.get("responseElements", {}).get("group", {})
        group_name = group["displayName"]
        group_name_split = group_name.split("-")

        if group_name_split[1] == "A":
            account_name = group_name_split[2]
            permission_set = group_name_split[3]
            account_id = dynamo.get_account_id_from_name(account_name)
            group_id = get_group_by_group_name(group_name)
            perm_set_arn = get_perm_id_from_name(get_perm_sets, permission_set, ssoadmin_client)
            sso_associate_response = associate_sso(SSO_INSTANCE_ARN, account_id, perm_set_arn, group_id)
            sso_associate_response.update({
                "AccountName": account_name,
                "AccountId": account_id,
                "PermissionSet": permission_set,
                "ProvisionType": "Account"
            })
            logger.info(sso_associate_response)

            sqs.send_message(
                QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
                MessageBody=json.dumps(sso_associate_response),
                DelaySeconds=20
            )

        if group_name_split[1] == "O":
            permission_set = group_name_split[2]
            accounts = organizations.list_accounts()
            accounts_list = accounts["Accounts"]
            account_info = get_all_account_ids(accounts_list)
            group_id = get_group_by_group_name(group_name)

            perm_set_arn = get_perm_id_from_name(get_perm_sets, permission_set, ssoadmin_client)
            for account in account_info:
                sso_associate_response = associate_sso(SSO_INSTANCE_ARN, account["AccountId"], perm_set_arn, group_id)
                sso_associate_response.update({
                    "AccountName": account["AccountName"],
                    "AccountId": account["AccountId"],
                    "PermissionSet": permission_set,
                    "ProvisionType": "Organization"
                })
                logger.info(sso_associate_response)

                sqs.send_message(
                    QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
                    MessageBody=json.dumps(sso_associate_response),
                    DelaySeconds=20
                )

        elif event_name == "CreateManagedAccount":
            ssoadmin_client = boto3.client("sso-admin")
            get_perm_sets = ssoadmin_client.list_permission_sets(
                InstanceArn=SSO_INSTANCE_ARN,
                MaxResults=100
            )
            logger.info(event)

            group_names = dynamo.get_dynamo_org_groups()
            account_info = event.get("serviceEventDetails", {}).get("createManagedAccountStatus", {})
            account_id = account_info["account"]["accountId"]
            account_name = account_info["account"]["accountName"]

            for group in group_names:
                group_name = group["GroupID"]
                group_id = get_group_by_group_name(group_name)
                group_to_id = group_name.split("-")
                perm_name = group_to_id[2]
                perm_set_arn = get_perm_id_from_name(get_perm_sets, perm_name, ssoadmin_client)
                sso_associate_response = associate_sso(SSO_INSTANCE_ARN, account_id, perm_set_arn, group_id)
                sso_associate_response.update({
                    "AccountName": account_name,
                    "AccountId": account_id,
                    "PermissionSet": perm_name,
                    "ProvisionType": "Organization"
                })
                logger.info(sso_associate_response)

                sqs.send_message(
                    QueueUrl=SSO_ASSOCIATE_QUEUE_URL,
                    MessageBody=json.dumps(sso_associate_response),
                    DelaySeconds=20
                )

        else:
            print("Nothing I can do here")


