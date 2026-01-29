from netsuite_client import NetSuiteClient


def get_overdue_invoices(days: int = 30) -> dict:
    """
    Returns customer invoices that are overdue within the last N days.
    """
    client = NetSuiteClient()

    query = f"""
    SELECT
        t.id,
        t.tranid,
        t.entity,
        t.trandate,
        t.duedate,
        t.foreigntotal  
    FROM transaction t
    WHERE t.type = 'CustInvc'
      AND t.duedate < CURRENT_DATE
      AND t.duedate >= (CURRENT_DATE - {int(days)})
    ORDER BY t.duedate ASC
    FETCH FIRST 10 ROWS ONLY
    """

    return client.suiteql(query)

def get_unpaid_invoices_over_threshold(threshold: float = 1000.0) -> dict:
    """
    Returns customer invoices where the unpaid balance is greater than the given threshold.
    """
    client = NetSuiteClient()

    query = f"""
    SELECT
        t.id,
        t.tranid,
        t.trandate,
        t.duedate,
        t.entity,
        t.foreigntotal,
        t.foreignamountunpaid
    FROM transaction t
    WHERE t.type = 'CustInvc'
        AND t.duedate >= (CURRENT_DATE - 90)
        AND t.foreignamountunpaid > {float(threshold)}
    ORDER BY t.foreignamountunpaid DESC
    FETCH FIRST 10 ROWS ONLY
    """

    return client.suiteql(query)

def get_total_revenue(start_date: str, end_date: str) -> dict:
    """
    Returns total invoice revenue between two dates (inclusive).
    Dates must be in YYYY-MM-DD format.
    """
    client = NetSuiteClient()

    query = f"""
    SELECT
        SUM(t.foreigntotal) AS total_revenue
    FROM transaction t
    WHERE t.type = 'CustInvc'
      AND t.trandate >= DATE '{start_date}'
      AND t.trandate <= DATE '{end_date}'
    """

    return client.suiteql(query)