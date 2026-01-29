"""
Temporary discovery script.

Purpose:
NetSuite field names vary by account. This script is used ONLY to discover
which field represents the unpaid / remaining invoice balance in THIS account.

Once confirmed, the correct field will be used in a real finance tool.
This file is not part of production logic.
"""

from netsuite_client import NetSuiteClient

client = NetSuiteClient()

query = """
SELECT
    t.id,
    t.tranid,
    t.foreignamountunpaid
FROM transaction t
WHERE t.id = 17478932
"""

print(client.suiteql(query))
