from netsuite_client import NetSuiteClient
from finance_tools import customer_risk_profiles

client = NetSuiteClient()
print(customer_risk_profiles(client, limit=1000, top_n=10))
