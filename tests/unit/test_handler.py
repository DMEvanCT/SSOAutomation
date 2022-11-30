import json
import os

import pytest

import sso_auto_assign_dynamo.app

@pytest.fixture()
def test_get_dynamo_groups():
    # Note this test will only work with organizations that have an account named Audit
    account_id = sso_auto_assign_dynamo.app.getAccountIDDynamo("Audit")
    assert account_id is not None

def test_get_perm_id_from_name():
    getPermIDFromName = sso_auto_assign_dynamo.app.getPermIDFromName("AWSReadOnlyAccess")
    assert getPermIDFromName is not None

