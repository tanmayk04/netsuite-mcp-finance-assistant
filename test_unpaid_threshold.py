from finance_tools import get_unpaid_invoices_over_threshold

result = get_unpaid_invoices_over_threshold(50)  # small threshold to ensure results
print(result)