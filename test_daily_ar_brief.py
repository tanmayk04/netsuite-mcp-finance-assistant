from netsuite_client import NetSuiteClient
from finance_tools import daily_ar_brief

client = NetSuiteClient()
print(daily_ar_brief(client, top_n_queue=5, top_n_risk=5))
