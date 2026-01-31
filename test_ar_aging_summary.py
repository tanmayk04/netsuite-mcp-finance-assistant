from netsuite_client import NetSuiteClient
from finance_tools import ar_aging_summary

client = NetSuiteClient()
print(ar_aging_summary(client, lookback_days=365, limit=2000))
