"""
MCP Server for NetSuite Finance Assistant

This file exposes selected finance functions as MCP tools,
so that an AI client (Claude / ChatGPT) can call them.

Right now, we expose ONLY ONE tool to keep things simple:
- overdue_invoices(days)

More tools will be added later.
"""

# FastMCP is a lightweight helper that makes it easy
# to create an MCP-compatible tool server
from mcp.server.fastmcp import FastMCP

# Import the finance logic we already built and tested
from finance_tools import (
    get_overdue_invoices,
    get_unpaid_invoices_over_threshold,
    get_total_revenue,
    get_top_customers_by_invoice_amount
)

# Create an MCP server instance
# The name is what AI clients will see
mcp = FastMCP("netsuite-finance-assistant")


# Register a tool with MCP
# The decorator tells MCP:
# "This function can be called by an AI"
@mcp.tool()
def overdue_invoices(days: int = 30) -> dict:
    """
    MCP Tool: overdue_invoices

    Purpose:
    Return overdue customer invoices from NetSuite
    for the last N days.

    Parameters:
    - days (int): number of days in the past to check (default = 30)

    Returns:
    - JSON response from NetSuite (list of invoices)
    """

    # Call the existing finance function
    # This keeps business logic separate from MCP wiring
    return get_overdue_invoices(days)

@mcp.tool()
def unpaid_invoices_over_threshold(threshold: float = 1000.0) -> dict:
    """
    MCP Tool: unpaid_invoices_over_threshold

    Purpose:
    Return invoices that still have an unpaid balance above the given threshold.

    Parameters:
    - threshold (float): minimum unpaid amount to return (default = 1000.0)

    Returns:
    - JSON response from NetSuite (list of invoices)
    """
    return get_unpaid_invoices_over_threshold(threshold)

@mcp.tool()
def total_revenue(start_date: str, end_date: str) -> dict:
    """
    MCP Tool: total_revenue
    Return total invoice revenue between two dates (YYYY-MM-DD).
    """
    return get_total_revenue(start_date, end_date)


@mcp.tool()
def top_customers_by_invoice_amount(start_date: str, end_date: str, top_n: int = 10) -> dict:
    """
    MCP Tool: top_customers_by_invoice_amount
    Return top N customers by total invoiced amount between two dates (YYYY-MM-DD).
    """
    return get_top_customers_by_invoice_amount(start_date, end_date, top_n)


# Entry point when running this file directly
if __name__ == "__main__":
    # Start the MCP server
    # This opens a local server that AI tools can connect to
    mcp.run(transport="stdio")