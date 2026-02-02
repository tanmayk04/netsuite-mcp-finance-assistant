from netsuite_client import NetSuiteClient
from finance_tools import send_collections_emails

client = NetSuiteClient()

out = send_collections_emails(
    client,
    top_n=1,                 # send only 1
    dry_run=False,           # real send
    test_recipient="tanmaykakade@jacentretail.com",  # send to yourself
    max_send=1
)

print(out)
