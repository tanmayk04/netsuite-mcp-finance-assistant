from netsuite_client import NetSuiteClient


def get_overdue_invoices(days: int = 30) -> dict:
    """
    Returns customer invoices that are overdue within the last N days.
    """
    client = NetSuiteClient()

    query = f"""
    SELECT
        t.id
    FROM transaction t
    WHERE t.type = 'CustInvc'
      AND t.duedate < CURRENT_DATE
      AND t.duedate >= (CURRENT_DATE - {int(days)})
    ORDER BY t.id
    FETCH FIRST 10 ROWS ONLY
    """

    return client.suiteql(query)
