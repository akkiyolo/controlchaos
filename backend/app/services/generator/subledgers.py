"""Sub-ledger entries generator tied 1:1 to GL control accounts."""

import uuid

SUBLEDGER_GL_MAPPING = {
    "AR": "1100",       # Accounts Receivable (Trade)
    "AP": "2000",       # Accounts Payable (Vendors)
    "FA": "1500",       # Fixed Assets & Equipment
    "payroll": "5000",  # Compensation and Payroll Expense
    "cash": "1000",     # Cash and Cash Equivalents
}


def create_subledger_entry(
    dataset_id: str,
    gl_entry_id: str,
    subledger_type: str,
    counterparty: str,
    amount: float,
    currency: str,
    value_date: str,
) -> dict:
    """Creates a subledger entry linked to its GL counterpart."""
    return {
        "dataset_id": dataset_id,
        "ref_id": f"SL-{subledger_type}-{uuid.uuid4().hex[:8].upper()}",
        "gl_entry_id": gl_entry_id,
        "subledger_type": subledger_type,
        "counterparty": counterparty,
        "amount": round(abs(amount), 4),
        "currency": currency,
        "value_date": value_date,
        "status": "posted",
    }
