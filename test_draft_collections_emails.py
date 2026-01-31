from netsuite_client import NetSuiteClient
from finance_tools import draft_collections_emails

client = NetSuiteClient()
out = draft_collections_emails(client, top_n=3)
print(out["drafts"][0]["subject"])
print(out["drafts"][0]["body"])
