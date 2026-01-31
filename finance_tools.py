from datetime import date, timedelta, datetime
from typing import Any, Dict, List, Optional
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

def get_top_customers_by_invoice_amount(start_date: str, end_date: str, top_n: int = 10) -> dict:
    """
    Returns top customers by total invoiced amount between two dates.
    Dates must be in YYYY-MM-DD format.
    """
    client = NetSuiteClient()

    query = f"""
    SELECT
        t.entity,
        SUM(t.foreigntotal) AS total_invoiced
    FROM transaction t
    WHERE t.type = 'CustInvc'
      AND t.trandate >= DATE '{start_date}'
      AND t.trandate <= DATE '{end_date}'
    GROUP BY t.entity
    ORDER BY total_invoiced DESC
    FETCH FIRST {int(top_n)} ROWS ONLY
    """

    return client.suiteql(query)


def get_open_invoice_rows(
    client,
    as_of_date: Optional[date] = None,
    limit: int = 1000,
    lookback_days = 365
) -> List[Dict[str, Any]]:
    """
    Base dataset: all open customer invoices (unpaid balance > 0).
    This function is the foundation for aging, risk, and priority tools.
    """

    if as_of_date is None:
        as_of_date = date.today()

    limit = min(int(limit), 1000)
    start_date = as_of_date - timedelta(days=lookback_days)

    query = f"""
    SELECT
        t.id                  AS transaction_id,
        t.tranid              AS invoice_number,
        t.trandate            AS invoice_date,
        t.duedate             AS due_date,
        t.entity              AS customer_id,
        e.entityid            AS customer_name,
        t.foreignamountunpaid AS unpaid_amount
    FROM transaction t
    JOIN entity e
        ON e.id = t.entity
    WHERE
        t.type = 'CustInvc'
        AND NVL(t.foreignamountunpaid, 0) > 0
        AND t.trandate BETWEEN TO_DATE('{start_date.isoformat()}', 'YYYY-MM-DD')
                  AND TO_DATE('{as_of_date.isoformat()}', 'YYYY-MM-DD')
    ORDER BY
        t.duedate DESC
    """

    resp = client.suiteql(query=query, limit=limit)

    rows = resp.get("items", [])

    # Normalize output (important for later steps)
    result = []
    for r in rows:
        result.append({
            "transaction_id": r.get("transaction_id"),
            "invoice_number": r.get("invoice_number"),
            "invoice_date": r.get("invoice_date"),
            "due_date": r.get("due_date"),
            "customer_id": r.get("customer_id"),
            "customer_name": r.get("customer_name"),
            "unpaid_amount": float(r.get("unpaid_amount") or 0),
        })

    return result

from collections import defaultdict

def _parse_netsuite_date(d: Any) -> Optional[date]:
    """NetSuite may return dates like '01/30/2025'. Convert safely to datetime.date."""
    if not d:
        return None
    if isinstance(d, date):
        return d
    s = str(d).strip()
    # Common NetSuite SuiteQL format: MM/DD/YYYY
    return datetime.strptime(s, "%m/%d/%Y").date()


def ar_aging_summary(
    client,
    as_of_date: Optional[date] = None,
    lookback_days: int = 365,
    limit: int = 5000,
    top_n: int = 10
) -> Dict[str, Any]:
    """
    Groups open (unpaid) invoices into aging buckets and returns totals + counts.
    Uses get_open_invoice_rows() only (read-only).
    """
    if as_of_date is None:
        as_of_date = date.today()

    rows = get_open_invoice_rows(client, as_of_date=as_of_date, limit=limit, lookback_days=lookback_days)

    buckets = {
        "current": 0.0,            # not overdue yet (days_overdue <= 0)
        "overdue_0_10": 0.0,
        "overdue_11_20": 0.0,
        "overdue_21_30": 0.0,
        "overdue_31_plus": 0.0,
    }

    counts = {
        "open_invoices": 0,
        "current": 0,
       "overdue_0_10": 0.0,
        "overdue_11_20": 0.0,
        "overdue_21_30": 0.0,
        "overdue_31_plus": 0.0,
    }

    overdue_by_customer = defaultdict(lambda: {"customer_name": None, "overdue_total": 0.0, "oldest": 0})

    for r in rows:
        due = _parse_netsuite_date(r.get("due_date"))
        unpaid = float(r.get("unpaid_amount") or 0)

        # Skip weird rows
        if unpaid <= 0 or due is None:
            continue

        counts["open_invoices"] += 1
        days_overdue = (as_of_date - due).days

        if days_overdue <= 0:
            buckets["current"] += unpaid
            counts["current"] += 1
        elif days_overdue <= 10:
            buckets["overdue_0_10"] += unpaid
            counts["overdue_0_10"] += 1
        elif days_overdue <= 20:
            buckets["overdue_11_20"] += unpaid
            counts["overdue_11_20"] += 1
        elif days_overdue <= 30:
            buckets["overdue_21_30"] += unpaid
            counts["overdue_21_30"] += 1
        else:
            buckets["overdue_31_plus"] += unpaid
            counts["overdue_31_plus"] += 1

        # Track top overdue customers
        if days_overdue > 0:
            cid = str(r.get("customer_id"))
            overdue_by_customer[cid]["customer_name"] = r.get("customer_name")
            overdue_by_customer[cid]["overdue_total"] += unpaid
            overdue_by_customer[cid]["oldest"] = max(overdue_by_customer[cid]["oldest"], days_overdue)

    open_ar_total = sum(buckets.values())

    top_customers = sorted(
        (
            {
                "customer_id": cid,
                "customer_name": info["customer_name"],
                "overdue_total": round(info["overdue_total"], 2),
                "oldest_days_overdue": info["oldest"],
            }
            for cid, info in overdue_by_customer.items()
        ),
        key=lambda x: x["overdue_total"],
        reverse=True,
    )[:top_n]

    return {
        "as_of_date": as_of_date.isoformat(),
        "totals": {
            "open_ar_total": round(open_ar_total, 2),
            "current": round(buckets["current"], 2),
            "overdue_0_10": round(buckets["overdue_0_10"], 2),
            "overdue_11_20": round(buckets["overdue_11_20"], 2),
            "overdue_21_30": round(buckets["overdue_21_30"], 2),
            "overdue_31_plus": round(buckets["overdue_31_plus"], 2),
        },
        "counts": counts,
        "top_overdue_customers": top_customers,
    }


def customer_risk_profiles(
    client,
    as_of_date: Optional[date] = None,
    lookback_days: int = 365,
    limit: int = 1000,
    min_open_balance: float = 0.0,
    top_n: int = 25,
) -> Dict[str, Any]:
    """
    Returns customers with risk score + reasons using open invoice rows.

    Updated scoring to match new aging buckets:
      - overdue_0_10 (includes due today)
      - overdue_11_20
      - overdue_21_30
      - overdue_31_plus

    Risk score v2 (0..1):
      0.50 * overdue_ratio
    + 0.30 * normalized_oldest_days (cap at 60 days)
    + 0.20 * severity_score (weighted mix of overdue buckets)
    """

    if as_of_date is None:
        as_of_date = date.today()

    rows = get_open_invoice_rows(
        client,
        as_of_date=as_of_date,
        lookback_days=lookback_days,
        limit=limit,
    )

    agg = defaultdict(lambda: {
        "customer_name": None,
        "open_ar": 0.0,
        "overdue_ar": 0.0,
        "open_count": 0,
        "overdue_count": 0,

        "max_days_overdue": 0,
        "sum_days_overdue": 0,

        # New bucket counts
        "cnt_0_10": 0,
        "cnt_11_20": 0,
        "cnt_21_30": 0,
        "cnt_31_plus": 0,

        # New bucket amounts (optional but useful)
        "amt_0_10": 0.0,
        "amt_11_20": 0.0,
        "amt_21_30": 0.0,
        "amt_31_plus": 0.0,
    })

    for r in rows:
        due = _parse_netsuite_date(r.get("due_date"))
        unpaid = float(r.get("unpaid_amount") or 0)
        if unpaid <= 0 or due is None:
            continue

        cid = str(r.get("customer_id"))
        name = r.get("customer_name")

        days_overdue = (as_of_date - due).days

        a = agg[cid]
        a["customer_name"] = name
        a["open_ar"] += unpaid
        a["open_count"] += 1

        if days_overdue > 0:
            a["overdue_ar"] += unpaid
            a["overdue_count"] += 1
            a["max_days_overdue"] = max(a["max_days_overdue"], days_overdue)
            a["sum_days_overdue"] += days_overdue

            # Bucket into your new ranges
            if days_overdue <= 10:
                a["cnt_0_10"] += 1
                a["amt_0_10"] += unpaid
            elif days_overdue <= 20:
                a["cnt_11_20"] += 1
                a["amt_11_20"] += unpaid
            elif days_overdue <= 30:
                a["cnt_21_30"] += 1
                a["amt_21_30"] += unpaid
            else:
                a["cnt_31_plus"] += 1
                a["amt_31_plus"] += unpaid

    profiles: List[Dict[str, Any]] = []

    for cid, a in agg.items():
        open_ar = a["open_ar"]
        if open_ar < float(min_open_balance):
            continue

        overdue_ar = a["overdue_ar"]
        overdue_ratio = (overdue_ar / open_ar) if open_ar > 0 else 0.0

        # --- Scoring components ---
        score_ratio = max(0.0, min(overdue_ratio, 1.0))

        # Oldest days overdue: cap at 60 now (because your buckets top out at 31+)
        score_age = min(a["max_days_overdue"] / 60.0, 1.0)

        # Severity score: weighted mix of bucket counts (normalized)
        # weights: 0-10 (0.25), 11-20 (0.5), 21-30 (0.75), 31+ (1.0)
        # Normalize by up to 3 overdue invoices to avoid huge count dominance
        weighted = (
            0.25 * a["cnt_0_10"] +
            0.50 * a["cnt_11_20"] +
            0.75 * a["cnt_21_30"] +
            1.00 * a["cnt_31_plus"]
        )
        score_severity = min(weighted / 3.0, 1.0)

        risk_score = 0.50 * score_ratio + 0.30 * score_age + 0.20 * score_severity

        if risk_score >= 0.75:
            tier = "High"
        elif risk_score >= 0.50:
            tier = "Medium"
        else:
            tier = "Low"

        avg_days = int(a["sum_days_overdue"] / a["overdue_count"]) if a["overdue_count"] > 0 else 0

        # --- Drivers (updated to match your buckets) ---
        drivers = []
        if overdue_ratio >= 0.7:
            drivers.append(f"Overdue ratio is {round(overdue_ratio * 100)}%")
        if a["max_days_overdue"] >= 21:
            drivers.append(f"Oldest overdue is {a['max_days_overdue']} days")
        if a["cnt_31_plus"] >= 1:
            drivers.append(f"{a['cnt_31_plus']} invoice(s) are 31+ days overdue")
        if a["cnt_21_30"] >= 2:
            drivers.append(f"Multiple invoices are 21–30 days overdue ({a['cnt_21_30']})")
        if overdue_ar >= 1000:
            drivers.append(f"Overdue exposure is ${round(overdue_ar, 2)}")

        profiles.append({
            "customer_id": cid,
            "customer_name": a["customer_name"],
            "risk_score": round(risk_score, 3),
            "risk_tier": tier,
            "open_ar": round(open_ar, 2),
            "overdue_ar": round(overdue_ar, 2),
            "overdue_ratio": round(overdue_ratio, 3),

            # New bucket counts + amounts (useful for UI + later automation)
            "aging_buckets": {
                "overdue_0_10": {"count": a["cnt_0_10"], "amount": round(a["amt_0_10"], 2)},
                "overdue_11_20": {"count": a["cnt_11_20"], "amount": round(a["amt_11_20"], 2)},
                "overdue_21_30": {"count": a["cnt_21_30"], "amount": round(a["amt_21_30"], 2)},
                "overdue_31_plus": {"count": a["cnt_31_plus"], "amount": round(a["amt_31_plus"], 2)},
            },

            "invoice_counts": {
                "open": a["open_count"],
                "overdue": a["overdue_count"],
            },
            "days_overdue": {
                "avg": avg_days,
                "max": a["max_days_overdue"],
            },
            "drivers": drivers or ["No major risk signals (mostly current or mildly overdue)"],
        })

    profiles.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "as_of_date": as_of_date.isoformat(),
        "customers": profiles[:top_n],
    }

import math

def collections_priority_queue(
    client,
    as_of_date: Optional[date] = None,
    lookback_days: int = 365,
    limit: int = 1000,
    top_n: int = 50,
) -> Dict[str, Any]:
    """
    Returns a ranked list of customers to contact first.

    Updated to use new aging buckets from customer_risk_profiles():
      - overdue_0_10
      - overdue_11_20
      - overdue_21_30
      - overdue_31_plus

    priority_score (0..1):
      0.50 * risk_score
    + 0.30 * money_impact (normalized log of overdue_ar)
    + 0.10 * age_score (max_days_overdue normalized to 60 days)
    + 0.10 * severity_boost (based on counts in 21-30 and 31+)
    """

    if as_of_date is None:
        as_of_date = date.today()

    rp = customer_risk_profiles(
        client,
        as_of_date=as_of_date,
        lookback_days=lookback_days,
        limit=limit,
        top_n=1000,  # pull more then rank
    )

    customers = rp.get("customers", [])

    max_overdue = max((float(c.get("overdue_ar") or 0) for c in customers), default=0.0)

    queue = []
    for c in customers:
        overdue_ar = float(c.get("overdue_ar") or 0)
        risk_score = float(c.get("risk_score") or 0)
        max_days = int((c.get("days_overdue") or {}).get("max") or 0)

        aging = c.get("aging_buckets") or {}
        cnt_0_10 = int((aging.get("overdue_0_10") or {}).get("count") or 0)
        cnt_11_20 = int((aging.get("overdue_11_20") or {}).get("count") or 0)
        cnt_21_30 = int((aging.get("overdue_21_30") or {}).get("count") or 0)
        cnt_31_plus = int((aging.get("overdue_31_plus") or {}).get("count") or 0)

        # Money impact (log scale)
        if max_overdue > 0:
            money_impact = math.log10(overdue_ar + 1) / math.log10(max_overdue + 1)
        else:
            money_impact = 0.0

        # Age score (cap at 60 since we now emphasize 31+ and tighter buckets)
        age_score = min(max_days / 60.0, 1.0)

        # Severity boost based on bucket mix (counts)
        # 31+ is most severe, then 21-30, then 11-20, then 0-10
        weighted = (1.0 * cnt_31_plus) + (0.7 * cnt_21_30) + (0.4 * cnt_11_20) + (0.2 * cnt_0_10)
        severity_boost = min(weighted / 3.0, 1.0)  # normalize

        priority_score = (
            0.50 * risk_score
            + 0.30 * money_impact
            + 0.10 * age_score
            + 0.10 * severity_boost
        )

        # Recommended action (updated)
        if cnt_31_plus >= 1 or max_days >= 31:
            action = "Call + escalate if no response"
        elif cnt_21_30 >= 1 or max_days >= 21:
            action = "Follow up (call or firm email)"
        elif cnt_11_20 >= 1 or max_days >= 11:
            action = "Send reminder email / follow-up"
        elif cnt_0_10 >= 1:
            action = "Gentle reminder / monitor"
        else:
            action = "Monitor"

        reasons = []
        if overdue_ar > 0:
            reasons.append(f"${round(overdue_ar, 2)} overdue")
        if max_days > 0:
            reasons.append(f"Oldest overdue {max_days} days")
        if cnt_31_plus:
            reasons.append(f"{cnt_31_plus} invoice(s) 31+ days overdue")
        elif cnt_21_30:
            reasons.append(f"{cnt_21_30} invoice(s) 21–30 days overdue")
        elif cnt_11_20:
            reasons.append(f"{cnt_11_20} invoice(s) 11–20 days overdue")
        elif cnt_0_10:
            reasons.append(f"{cnt_0_10} invoice(s) 0–10 days overdue")

        reasons.append(f"Risk score {c['risk_score']} ({c['risk_tier']})")

        queue.append({
            "customer_id": c["customer_id"],
            "customer_name": c["customer_name"],
            "priority_score": round(priority_score, 3),
            "recommended_action": action,
            "open_ar": c["open_ar"],
            "overdue_ar": c["overdue_ar"],
            "max_days_overdue": max_days,
            "risk_score": c["risk_score"],
            "risk_tier": c["risk_tier"],
            "reasons": reasons,
        })

    queue.sort(key=lambda x: x["priority_score"], reverse=True)

    for i, item in enumerate(queue[:top_n], start=1):
        item["rank"] = i

    return {
        "as_of_date": as_of_date.isoformat(),
        "queue": queue[:top_n],
    }

def daily_ar_brief(
    client,
    as_of_date: Optional[date] = None,
    lookback_days: int = 365,
    limit: int = 1000,
    top_n_queue: int = 10,
    top_n_risk: int = 10,
) -> Dict[str, Any]:
    """
    One-call AR operations brief:
    - Aging snapshot (0–10 / 11–20 / 21–30 / 31+)
    - Top risk customers
    - Today's collections priority worklist
    - Escalations to focus on
    """

    if as_of_date is None:
        as_of_date = date.today()

    aging = ar_aging_summary(client, as_of_date=as_of_date, lookback_days=lookback_days, limit=limit)
    risks = customer_risk_profiles(client, as_of_date=as_of_date, lookback_days=lookback_days, limit=limit, top_n=top_n_risk)
    queue = collections_priority_queue(client, as_of_date=as_of_date, lookback_days=lookback_days, limit=limit, top_n=top_n_queue)

    totals = aging.get("totals", {})
    counts = aging.get("counts", {})

    open_total = float(totals.get("open_ar_total") or 0.0)
    current_amt = float(totals.get("current") or 0.0)

    # Overdue total = open total - current (safe even if buckets change)
    overdue_total = max(open_total - current_amt, 0.0)
    overdue_pct = round((overdue_total / open_total) * 100, 2) if open_total > 0 else 0.0

    # Find largest overdue bucket (excluding current)
    overdue_bucket_keys = [k for k in totals.keys() if k.startswith("overdue_")]
    largest_bucket = None
    if overdue_bucket_keys:
        largest_bucket = max(overdue_bucket_keys, key=lambda k: float(totals.get(k) or 0.0))

    # Escalations rule (simple + explainable):
    # - Any queue item with max_days_overdue >= 31 OR priority_score >= 0.80
    escalations = []
    for item in queue.get("queue", []):
        if int(item.get("max_days_overdue") or 0) >= 31 or float(item.get("priority_score") or 0) >= 0.80:
            escalations.append(item)

    headline = {
        "open_ar_total": round(open_total, 2),
        "overdue_total": round(overdue_total, 2),
        "overdue_pct": overdue_pct,
        "open_invoices": int(counts.get("open_invoices") or 0),
        "largest_overdue_bucket_key": largest_bucket,
        "largest_overdue_bucket_amount": round(float(totals.get(largest_bucket) or 0.0), 2) if largest_bucket else 0.0,
    }

    return {
        "as_of_date": as_of_date.isoformat(),
        "headline": headline,
        "aging": aging,                        # full details
        "top_risk_customers": risks.get("customers", []),
        "today_priority_queue": queue.get("queue", []),
        "escalations": escalations,
    }


def draft_collections_emails(
    client,
    as_of_date: Optional[date] = None,
    lookback_days: int = 365,
    limit: int = 1000,
    top_n: int = 10,
    sender_name: str = "Accounts Receivable Team",
    company_name: str = "Your Company",
) -> Dict[str, Any]:
    """
    Creates email drafts for the top-N customers in the collections priority queue.
    SAFE: does not send emails, only returns draft subjects/bodies.

    Uses bucket signals via the queue's max_days_overdue + reasons to choose tone.
    """

    if as_of_date is None:
        as_of_date = date.today()

    queue_resp = collections_priority_queue(
        client,
        as_of_date=as_of_date,
        lookback_days=lookback_days,
        limit=limit,
        top_n=top_n,
    )

    drafts: List[Dict[str, Any]] = []

    for item in queue_resp.get("queue", []):
        customer_name = item.get("customer_name", "Customer")
        overdue_ar = float(item.get("overdue_ar") or 0.0)
        max_days = int(item.get("max_days_overdue") or 0)
        action = item.get("recommended_action") or "Follow up"
        reasons = item.get("reasons") or []

        # Decide "tone" based on your new bucket logic
        # 0-10: gentle, 11-20: reminder, 21-30: firm, 31+: escalation
        if max_days >= 31:
            tone = "escalation"
        elif max_days >= 21:
            tone = "firm"
        elif max_days >= 11:
            tone = "reminder"
        else:
            tone = "gentle"

        # Subject lines by tone
        if tone == "gentle":
            subject = f"Friendly reminder: invoice payment due"
        elif tone == "reminder":
            subject = f"Reminder: outstanding balance - action requested"
        elif tone == "firm":
            subject = f"Past due notice: outstanding balance requires attention"
        else:
            subject = f"Urgent: past due balance — please respond"

        # Build a clean reason sentence (optional, keeps it explainable)
        reason_line = ""
        if reasons:
            # Keep it short to avoid dumping internal scoring
            # Example: "$183.27 overdue; Oldest overdue 17 days"
            trimmed = "; ".join([str(r) for r in reasons[:2]])
            reason_line = f"\n\n(Internal note: {trimmed})"

        # Email body templates
        if tone == "gentle":
            body = f"""Hi {customer_name},

Hope you're doing well. This is a friendly reminder that we have an outstanding balance of ${overdue_ar:,.2f} on your account.

If payment has already been sent, please disregard this message. Otherwise, could you share an expected payment date?

Thank you,
{sender_name}
{company_name}
"""
        elif tone == "reminder":
            body = f"""Hi {customer_name},

This is a reminder that we have an outstanding balance of ${overdue_ar:,.2f} that appears past due.

Could you please confirm the payment status and provide an expected payment date? If there are any issues with the invoice, let us know and we’ll help resolve them.

Thanks,
{sender_name}
{company_name}
"""
        elif tone == "firm":
            body = f"""Hi {customer_name},

Our records show an outstanding past-due balance of ${overdue_ar:,.2f}. Please treat this as a past due notice.

Please reply with a payment date or any details needed to resolve this promptly. If payment has already been initiated, share the remittance information.

Regards,
{sender_name}
{company_name}
"""
        else:
            body = f"""Hi {customer_name},

We are following up urgently regarding a past-due balance of ${overdue_ar:,.2f}.

Please respond today with the payment status and a confirmed payment date. If there is a dispute or issue preventing payment, notify us immediately so we can address it.

Regards,
{sender_name}
{company_name}
"""

        drafts.append({
            "rank": item.get("rank"),
            "customer_id": item.get("customer_id"),
            "customer_name": customer_name,
            "recommended_action": action,
            "max_days_overdue": max_days,
            "overdue_ar": round(overdue_ar, 2),
            "subject": subject,
            "body": body.strip() + reason_line,  # internal note appended for your review
        })

    return {
        "as_of_date": as_of_date.isoformat(),
        "count": len(drafts),
        "drafts": drafts,
        "note": "Drafts only — no emails were sent.",
    }

