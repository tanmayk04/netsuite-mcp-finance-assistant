"""
MCP Server for NetSuite Finance Assistant

This file exposes selected finance functions as MCP tools,
so that an AI client (Claude / ChatGPT) can call them.
"""

from __future__ import annotations

import os
import time
import traceback
from datetime import datetime

from mcp.server.fastmcp import FastMCP
from netsuite_client import NetSuiteClient

# Import the finance logic we already built and tested
from finance_tools import (
    get_overdue_invoices,
    get_unpaid_invoices_over_threshold,
    get_total_revenue,
    get_top_customers_by_invoice_amount,
    ar_aging_summary,
    customer_risk_profiles,
    collections_priority_queue,
    daily_ar_brief,
    draft_collections_emails,
    send_collections_emails,
)

# -----------------------------
# Logging (always to same folder)
# -----------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MCP_LOG_FILE = os.path.join(BASE_DIR, os.getenv("MCP_LOG_FILE", "mcp_debug.log"))

def _mcp_log(msg: str) -> None:
    """Append logs to a file so we can debug even when MCP runs via stdio."""
    try:
        with open(MCP_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat()} {msg}\n")
    except Exception:
        pass

def _log_tool_start(tool: str, payload: dict) -> float:
    _mcp_log(f"[TOOL][START] {tool} payload={payload}")
    return time.perf_counter()

def _log_tool_end(tool: str, t0: float, ok: bool, extra: str = "") -> None:
    dt = time.perf_counter() - t0
    _mcp_log(f"[TOOL][END] {tool} ok={ok} took={dt:.2f}s {extra}".rstrip())

def _tool_error(tool: str, t0: float, e: Exception, payload: dict) -> dict:
    dt = time.perf_counter() - t0
    _mcp_log(f"[TOOL][ERROR] {tool} took={dt:.2f}s payload={payload} err={repr(e)}")
    _mcp_log(traceback.format_exc())
    return {"error": str(e), "tool": tool, **payload}

# -----------------------------
# Init
# -----------------------------
client = NetSuiteClient()
mcp = FastMCP("netsuite-finance-assistant")

_mcp_log(f"[MCP] Loaded mcp_server.py from {BASE_DIR}")
_mcp_log(f"[MCP] Logging to {MCP_LOG_FILE}")

# -----------------------------
# Tools
# -----------------------------
@mcp.tool()
def overdue_invoices(days: int = 30) -> dict:
    payload = {"days": days}
    t0 = _log_tool_start("overdue_invoices", payload)
    try:
        result = get_overdue_invoices(days)  # keep as-is (your current signature)
        _log_tool_end("overdue_invoices", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("overdue_invoices", t0, e, payload)

@mcp.tool()
def unpaid_invoices_over_threshold(threshold: float = 1000.0) -> dict:
    payload = {"threshold": threshold}
    t0 = _log_tool_start("unpaid_invoices_over_threshold", payload)
    try:
        result = get_unpaid_invoices_over_threshold(threshold)  # keep as-is
        _log_tool_end("unpaid_invoices_over_threshold", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("unpaid_invoices_over_threshold", t0, e, payload)

@mcp.tool()
def total_revenue(start_date: str, end_date: str) -> dict:
    payload = {"start_date": start_date, "end_date": end_date}
    t0 = _log_tool_start("total_revenue", payload)
    try:
        result = get_total_revenue(start_date, end_date)  # keep as-is
        _log_tool_end("total_revenue", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("total_revenue", t0, e, payload)

@mcp.tool()
def top_customers_by_invoice_amount(start_date: str, end_date: str, top_n: int = 10) -> dict:
    payload = {"start_date": start_date, "end_date": end_date, "top_n": top_n}
    t0 = _log_tool_start("top_customers_by_invoice_amount", payload)
    try:
        result = get_top_customers_by_invoice_amount(start_date, end_date, top_n)  # keep as-is
        _log_tool_end("top_customers_by_invoice_amount", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("top_customers_by_invoice_amount", t0, e, payload)

@mcp.tool()
def ar_aging_summary_tool(lookback_days: int = 365) -> dict:
    payload = {"lookback_days": lookback_days}
    t0 = _log_tool_start("ar_aging_summary_tool", payload)
    try:
        result = ar_aging_summary(client, lookback_days=lookback_days)
        _log_tool_end("ar_aging_summary_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("ar_aging_summary_tool", t0, e, payload)

@mcp.tool()
def customer_risk_profiles_tool(top_n: int = 25, lookback_days: int = 365) -> dict:
    payload = {"top_n": top_n, "lookback_days": lookback_days}
    t0 = _log_tool_start("customer_risk_profiles_tool", payload)
    try:
        result = customer_risk_profiles(client, top_n=top_n, lookback_days=lookback_days)
        _log_tool_end("customer_risk_profiles_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("customer_risk_profiles_tool", t0, e, payload)

@mcp.tool()
def collections_priority_queue_tool(top_n: int = 50, lookback_days: int = 365) -> dict:
    payload = {"top_n": top_n, "lookback_days": lookback_days}
    t0 = _log_tool_start("collections_priority_queue_tool", payload)
    try:
        result = collections_priority_queue(client, top_n=top_n, lookback_days=lookback_days)
        _log_tool_end("collections_priority_queue_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("collections_priority_queue_tool", t0, e, payload)

@mcp.tool()
def daily_ar_brief_tool(top_n_queue: int = 10, top_n_risk: int = 10, lookback_days: int = 365) -> dict:
    payload = {"top_n_queue": top_n_queue, "top_n_risk": top_n_risk, "lookback_days": lookback_days}
    t0 = _log_tool_start("daily_ar_brief_tool", payload)
    try:
        result = daily_ar_brief(
            client,
            top_n_queue=top_n_queue,
            top_n_risk=top_n_risk,
            lookback_days=lookback_days,
        )
        _log_tool_end("daily_ar_brief_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("daily_ar_brief_tool", t0, e, payload)

@mcp.tool()
def draft_collections_emails_tool(top_n: int = 10, lookback_days: int = 365) -> dict:
    payload = {"top_n": top_n, "lookback_days": lookback_days}
    t0 = _log_tool_start("draft_collections_emails_tool", payload)
    try:
        result = draft_collections_emails(client, top_n=top_n, lookback_days=lookback_days)
        _log_tool_end("draft_collections_emails_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("draft_collections_emails_tool", t0, e, payload)

@mcp.tool()
def send_collections_emails_tool(
    top_n: int = 5,
    lookback_days: int = 365,
    dry_run: bool = False,
    test_recipient: str = "",
    max_send: int = 3,
) -> dict:
    payload = {
        "top_n": top_n,
        "lookback_days": lookback_days,
        "dry_run": dry_run,
        "test_recipient": test_recipient,
        "max_send": max_send,
    }
    t0 = _log_tool_start("send_collections_emails_tool", payload)
    try:
        result = send_collections_emails(
            client,
            top_n=top_n,
            lookback_days=lookback_days,
            dry_run=dry_run,
            test_recipient=test_recipient,
            max_send=max_send,
        )
        _log_tool_end("send_collections_emails_tool", t0, ok=True)
        return result
    except Exception as e:
        return _tool_error("send_collections_emails_tool", t0, e, payload)

# -----------------------------
# Entry point
# -----------------------------
if __name__ == "__main__":
    _mcp_log("[MCP] server starting (transport=stdio)")
    mcp.run(transport="stdio")