from netsuite_client import NetSuiteClient

client = NetSuiteClient()

q = "SELECT id FROM employee FETCH FIRST 1 ROWS ONLY"
print(client.suiteql(q))