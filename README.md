# netsuite-mcp-finance-assistant
An MCP-based AI finance assistant that enables secure, read-only natural language access to NetSuite data using OAuth 2.0 and SuiteQL. Designed with enterprise-grade access control, tool-based AI, and explainable outputs.

## Versioning

- **v1 (tag: `v1-mcp-finance`)**: Stable, read-only NetSuite AR finance assistant.
  - Includes:
    - Overdue invoices
    - Unpaid invoices over threshold
    - Total revenue from invoices
    - Top customers by invoice amount
    - High-risk customers (AI-derived, explainable)
  - Excludes:
    - Any write/update actions
    - Emails or notifications
    - Customer PII
    - Credit holds or collections actions

