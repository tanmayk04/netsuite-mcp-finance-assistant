from finance_tools import get_total_revenue

# pick a window that should have invoices in SB2 sample data
result = get_total_revenue("2025-01-01", "2026-12-31")
print(result)
