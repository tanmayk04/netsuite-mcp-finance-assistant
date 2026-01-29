from finance_tools import get_top_customers_by_invoice_amount

result = get_top_customers_by_invoice_amount("2025-01-01", "2026-12-31", top_n=10)
print(result)