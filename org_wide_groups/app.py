import boto3


# This is only here because The python API does not support filtering with begin with
def lambda_handler(event, context):
    group = event.get("responseElements", {}).get("group", {})
    group_name = group["displayName"]
    group_name_split = group_name.split("-")
    if group_name_split[1] == "O":
        dynamo = boto3.resource('dynamodb')
        group_info = {
            "GroupID": group_name
        }
        table = dynamo.Table("ORGSSOGroups")
        table.put_item(Item=group_info)
    else:
        print("This is not a global group")

