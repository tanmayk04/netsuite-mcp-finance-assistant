from netsuite_client import NetSuiteClient

client = NetSuiteClient()

query = """
SELECT
    t.id,
    t.foreigntotal
FROM transaction t
WHERE t.type = 'CustInvc'
FETCH FIRST 1 ROWS ONLY
"""

print(client.suiteql(query))
