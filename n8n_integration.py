"""Sends the finished report to an n8n workflow through a Webhook URL."""
import time

import requests


def send_to_n8n(webhook_url: str, report: str, risk: dict, doc_names: list) -> tuple:
    payload = {
        "source": "AI Customs Documentation & Compliance Checker",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "documents": doc_names,
        "risk_score": (risk or {}).get("score"),
        "risk_level": (risk or {}).get("level"),
        "issue_counts": {k: (risk or {}).get(k) for k in ("critical", "major", "minor")},
        "report_markdown": report,
    }
    try:
        r = requests.post(webhook_url, json=payload, timeout=30)
        return r.ok, f"n8n answered with status {r.status_code}"
    except Exception as e:
        return False, f"Could not reach n8n: {e}"
