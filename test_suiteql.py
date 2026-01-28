"""
Simple test script to validate NetSuite SuiteQL connectivity.
Executes a basic query against the employee table.
"""

from netsuite_client import NetSuiteClient

client = NetSuiteClient()

q = "SELECT id FROM employee FETCH FIRST 1 ROWS ONLY"
print(client.suiteql(q))