from netsuite_client import NetSuiteClient
from finance_tools import collections_priority_queue

client = NetSuiteClient()
out = collections_priority_queue(client, limit=1000, top_n=10)
print(out)
