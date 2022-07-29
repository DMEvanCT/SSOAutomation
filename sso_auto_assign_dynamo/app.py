import json
import os

import boto3
from boto3.dynamodb.conditions import Key

# This function is to auto assign groups based on SSO names
MAX_RETURN_PERMISSION_SET = os.getenv("MAX_RETURN_PERMISSION_SET")
SSO_INSTANCE_ARN = os.getenv("SSO_INSTANCE_ARN")
DIRECTORY_SERVICE_ID = os.getenv("DIRECTORY_SERVICE_ID")


# Get the account id from dynamo because AWS API sucks
def getAccountIDDynamo(account_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('AWSOrgAccounts')
    response = table.query(
        IndexName='AccountNameIndex',
        KeyConditionExpression=Key('Name').eq(account_name)
    )

    return response["Items"][0]["Id"]


# Get the permission set ID from the name of the permission
def getPermIDFromName(perms, permission_set_name, ssoadmin_client):
    for perm in perms["PermissionSets"]:
        perm_details = ssoadmin_client.describe_permission_set(
            InstanceArn=SSO_INSTANCE_ARN,
            PermissionSetArn=perm
        )

        if perm_details["PermissionSet"]["Name"] == permission_set_name:
            print(perm_details["PermissionSet"]["PermissionSetArn"])
            return perm_details["PermissionSet"]["PermissionSetArn"]

        print("Perm Details:")
        print(perm_details)


# Used in the O type accounts to assign to all accounts
def getAllAccountIDs(accounts_list):
    all_accounts_org = []
    for account in accounts_list:
        all_accounts_org.append(account["Id"])
    return all_accounts_org


# Get the group ID by the name of the group (Used in SSO assignment)
def getGroupbyGroupName(group_name):
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


## Get multiple groups
def getGroupsbyGroupName(group_name):
    group_ids = []

    identity_services_client = boto3.client("identitystore")
    group_info = identity_services_client.list_groups(
        IdentityStoreId=DIRECTORY_SERVICE_ID,
        Filters=[
            {
                "ComparisonOperator": "BEGINS_WITH",
                "AttributePath": "DisplayName",
                "AttributeValue": {
                    "StringValue": "AWS-O"
                }
            }
        ]
    )
    print(group_info)
    group_count = len(group_info["Groups"])
    group_list_number = 0
    while group_list_number <= group_count:
        group_ids.append(group_info["Groups"][group_list_number]["GroupId"])

    return group_ids


# Associate the Group and the permission set to aws account
def associateSSO(sso_instance_arn, account_id, perm_set_arn, group_id):
    ssoadmin_client = boto3.client("sso-admin")
    response = ssoadmin_client.create_account_assignment(
        InstanceArn=sso_instance_arn,
        TargetId=account_id,
        TargetType='AWS_ACCOUNT',
        PermissionSetArn=perm_set_arn,
        PrincipalType='GROUP',
        PrincipalId=group_id
    )
    # Print the response to ensure things are in progress
    return response


def getDynamoOrgGroups():
    # Table scans are sub par but so is itterating through a list for account names :Shrug: if someone wants to make
    # better be my guest.
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('ORGSSOGroups')
    response = table.scan()
    return response["Items"]


def lambda_handler(event, context):
    event_name = event["eventName"]
    # Assigns to account/accounts on CreatGroup
    if event_name == "CreateGroup":
        production_info = getAccountIDDynamo("Production")
        print(production_info)

        ssoadmin_client = boto3.client("sso-admin")
        identity_services_client = boto3.client("identitystore")

        organizations = boto3.client('organizations')

        get_perm_sets = ssoadmin_client.list_permission_sets(
            InstanceArn=SSO_INSTANCE_ARN,
            MaxResults=100
        )
        # Again super inefiecent. @TODO work with aws to make this filterable
        group = event.get("responseElements", {}).get("group", {})
        group_name = group["displayName"]
        group_name_split = group_name.split("-")

        if group_name_split[1] == "A":
            print("Printing A group")
            account_name = group_name_split[2]
            permission_set = group_name_split[3]
            print(f'Account Name: {account_name}, Permission Set: {permission_set}')
            account_id = getAccountIDDynamo(account_name)
            group_id = getGroupbyGroupName(group_name)
            # Get the permission set ARN from the name
            perm_set_arn = getPermIDFromName(get_perm_sets, permission_set, ssoadmin_client)
            print(f"The permission set arn is {perm_set_arn}")

            # Create the Association between the group permission and account (Create Persona)
            sso_associate_response = associateSSO(SSO_INSTANCE_ARN, account_id, perm_set_arn, group_id)
            # Print the response to ensure things are in progress
            print(sso_associate_response)

        if group_name_split[1] == "O":
            permission_set = group_name_split[2]
            accounts = organizations.list_accounts()
            accounts_list = accounts["Accounts"]
            account_ids = getAllAccountIDs(accounts_list)
            group_id = getGroupbyGroupName(group_name)

            perm_set_arn = getPermIDFromName(get_perm_sets, permission_set, ssoadmin_client)
            for account in account_ids:
                sso_associate_response = associateSSO(SSO_INSTANCE_ARN, account_id, perm_set_arn, group_id)
                print(sso_associate_response)
    # Uses the account create event to auto assign all O groups to new accounts
    if event_name == "CreateManagedAccount":
        print("MANAGED ACCOUNT")
        ssoadmin_client = boto3.client("sso-admin")
        get_perm_sets = ssoadmin_client.list_permission_sets(
            InstanceArn=SSO_INSTANCE_ARN,
            MaxResults=100
        )
        group_names = getDynamoOrgGroups()
        account_info = event.get("serviceEventDetails", {}).get("createManagedAccountStatus", {})
        account_id = account_info["account"]["accountId"]
        for group in group_names:
            group_name = group["GroupID"]
            group_id = getGroupbyGroupName(group_name)
            group_to_id = group_name.split("-")
            perm_name = group_to_id[2]
            perm_set_arn = getPermIDFromName(get_perm_sets, perm_name, ssoadmin_client)
            sso_associate_response = associateSSO(SSO_INSTANCE_ARN, account_id, perm_set_arn, group_id)
            print(sso_associate_response)

    else:
        print("Nothing I can do here")
