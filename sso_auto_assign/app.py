import json
import os

import boto3

# This function is to auto assign groups based on SSO names
MAX_RETURN_PERMISSION_SET = os.getenv("MAX_RETURN_PERMISSION_SET")
SSO_INSTANCE_ARN = os.getenv("SSO_INSTANCE_ARN")
DIRECTORY_SERVICE_ID = os.getenv("DIRECTORY_SERVICE_ID")

# Way to be horrible inefficient. @TODO work with AWS to be able to filter directly. Possibly move to Dynamo
def getAccountIDFromName(accounts, account_name):
    for account in accounts["Accounts"]:
        if account["Name"] == account_name:
            return account["Id"]

def getPermIDFromName(perms, permission_set_name, ssoadmin_client ):
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


def getAllAccountIDs(accounts_list):
    all_accounts_org = []
    for account in accounts_list:
        all_accounts_org.append(account["Id"])
    return all_accounts_org


def lambda_handler(event, context):

    ssoadmin_client = boto3.client("sso-admin")
    identity_services_client = boto3.client("identitystore")
    organizations = boto3.client("organizations")

    organizations = boto3.client('organizations')
    permission_sets = []

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
        accounts = organizations.list_accounts()
        account_id = getAccountIDFromName(accounts, account_name)
        print(account_id)
        group_info = identity_services_client.list_groups(
            IdentityStoreId=DIRECTORY_SERVICE_ID,
            Filters=[
                {
                    'AttributePath': 'DisplayName',
                    'AttributeValue': group_name
                },
            ]
        )
        group_id = group_info["Groups"][0]["GroupId"]
        # Get the permission set ARN from the name
        perm_set_arn = getPermIDFromName(get_perm_sets, permission_set, ssoadmin_client)
        print(f"The permission set arn is {perm_set_arn}")

        # Create the Association between the group permission and account (Create Persona)
        response = ssoadmin_client.create_account_assignment(
            InstanceArn=SSO_INSTANCE_ARN,
            TargetId=account_id,
            TargetType='AWS_ACCOUNT',
            PermissionSetArn=perm_set_arn,
            PrincipalType='GROUP',
            PrincipalId=group_id
        )
        # Print the response to ensure things are in progress
        print(response)

    if group_name_split[1] == "O":
        permission_set = group_name_split[2]
        accounts = organizations.list_accounts()
        accounts_list = accounts["Accounts"]
        account_ids = getAllAccountIDs(accounts_list)
        group_info = identity_services_client.list_groups(
            IdentityStoreId=DIRECTORY_SERVICE_ID,
            Filters=[
                {
                    'AttributePath': 'DisplayName',
                    'AttributeValue': group_name
                },
            ]
        )
        group_id = group_info["Groups"][0]["GroupId"]

        perm_set_arn = getPermIDFromName(get_perm_sets, permission_set, ssoadmin_client)
        for account in account_ids:
            response = ssoadmin_client.create_account_assignment(
                InstanceArn=SSO_INSTANCE_ARN,
                TargetId=account,
                TargetType='AWS_ACCOUNT',
                PermissionSetArn=perm_set_arn,
                PrincipalType='GROUP',
                PrincipalId=group_id
            )
            print(response)





