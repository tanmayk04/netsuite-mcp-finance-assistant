from finance_tools import get_open_invoice_rows
from netsuite_client import NetSuiteClient

client = NetSuiteClient()

rows = get_open_invoice_rows(client, limit=20)

print("Rows returned:", len(rows))
print(rows[0])
