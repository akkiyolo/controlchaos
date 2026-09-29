#!/usr/bin/env python
"""Seed database with demo users, roles, legal entities, and default accounts."""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from sqlalchemy import select  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models.entities import Account, LegalEntity, User  # noqa: E402
from app.services.audit.service import AuditService  # noqa: E402


def seed_demo_data() -> None:
    settings = get_settings()
    db = SessionLocal()

    print("==================================================", flush=True)
    print("ControlChaos Database Seeder", flush=True)
    print("==================================================", flush=True)

    try:
        admin_pass = settings.DEMO_ADMIN_PASSWORD.strip() if settings.DEMO_ADMIN_PASSWORD else "ControlChaosAdmin2026!"
        if not admin_pass:
            admin_pass = "ControlChaosAdmin2026!"

        # 1. Seed Users
        demo_users = [
            {
                "email": settings.DEMO_ADMIN_EMAIL,
                "name": "Sarah Chen (Admin)",
                "role": "admin",
                "password": admin_pass,
            },
            {
                "email": "owner@controlchaos.local",
                "name": "David Ross (Control Owner)",
                "role": "control_owner",
                "password": "ControlOwner2026!",
            },
            {
                "email": "reviewer@controlchaos.local",
                "name": "Elena Rostova (Reviewer / Checker)",
                "role": "reviewer",
                "password": "Reviewer2026!",
            },
            {
                "email": "analyst@controlchaos.local",
                "name": "Alex Mercer (Product Control Analyst)",
                "role": "analyst",
                "password": "Analyst2026!",
            },
            {
                "email": "auditor@controlchaos.local",
                "name": "Marcus Vance (Internal Audit)",
                "role": "auditor",
                "password": "Auditor2026!",
            },
        ]

        for u_data in demo_users:
            existing = db.scalar(select(User).where(User.email == u_data["email"]))
            if not existing:
                user = User(
                    email=u_data["email"],
                    name=u_data["name"],
                    role=u_data["role"],
                    password_hash=get_password_hash(u_data["password"]),
                    is_active=True,
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"[+] Created user: {user.email} [{user.role}]", flush=True)
            else:
                existing.password_hash = get_password_hash(u_data["password"])
                existing.is_active = True
                db.commit()
                print(f"[*] Updated password for user: {u_data['email']}", flush=True)

        # 2. Seed Legal Entities
        entities = [
            {"code": "LE-100", "name": "Global Markets Corp (London)", "currency": "GBP", "region": "EMEA"},
            {"code": "LE-200", "name": "North America Prime Brokerage LLC", "currency": "USD", "region": "AMER"},
            {"code": "LE-300", "name": "Asia Pacific Treasury Ltd", "currency": "INR", "region": "APAC"},
            {"code": "LE-400", "name": "Zurich Wealth Management AG", "currency": "CHF", "region": "EMEA"},
            {"code": "LE-500", "name": "Frankfurt Continental Banking SE", "currency": "EUR", "region": "EMEA"},
        ]

        for e_data in entities:
            existing = db.scalar(select(LegalEntity).where(LegalEntity.code == e_data["code"]))
            if not existing:
                ent = LegalEntity(**e_data)
                db.add(ent)
                db.commit()
                print(f"[+] Created legal entity: {ent.code} - {ent.name}", flush=True)

        # 3. Seed Chart of Accounts
        accounts = [
            {"code": "1000", "name": "Cash and Cash Equivalents", "type": "asset", "normal_balance": "debit"},
            {"code": "1100", "name": "Accounts Receivable (Trade)", "type": "asset", "normal_balance": "debit"},
            {"code": "1200", "name": "HQLA Treasury Securities", "type": "asset", "normal_balance": "debit"},
            {"code": "1500", "name": "Fixed Assets & Equipment", "type": "asset", "normal_balance": "debit"},
            {"code": "2000", "name": "Accounts Payable (Vendors)", "type": "liability", "normal_balance": "credit"},
            {"code": "2100", "name": "Accrued Expenses & Provisions", "type": "liability", "normal_balance": "credit"},
            {"code": "2200", "name": "Short-Term Repurchase Agreements", "type": "liability", "normal_balance": "credit"},
            {"code": "3000", "name": "Common Equity & Retained Earnings", "type": "equity", "normal_balance": "credit"},
            {"code": "4000", "name": "Trading and Interest Revenue", "type": "revenue", "normal_balance": "credit"},
            {"code": "4100", "name": "Fee and Advisory Income", "type": "revenue", "normal_balance": "credit"},
            {"code": "5000", "name": "Compensation and Payroll Expense", "type": "expense", "normal_balance": "debit"},
            {"code": "5100", "name": "Technology & Market Data Licensing", "type": "expense", "normal_balance": "debit"},
            {"code": "5200", "name": "Professional Fees & Legal Services", "type": "expense", "normal_balance": "debit"},
            {"code": "5300", "name": "Occupancy & Facilities Expense", "type": "expense", "normal_balance": "debit"},
            {"code": "5900", "name": "Intercompany Clearance Account", "type": "liability", "normal_balance": "credit"},
        ]

        for a_data in accounts:
            existing = db.scalar(select(Account).where(Account.code == a_data["code"]))
            if not existing:
                acc = Account(**a_data)
                db.add(acc)
                db.commit()
                print(f"[+] Created chart of account: {acc.code} - {acc.name}", flush=True)

        # Record audit log of seeding
        AuditService.record(
            db=db,
            actor="system_seeder",
            action="SEED_INITIAL_DATA",
            entity_type="system",
            entity_id="init",
            payload={"entities_count": len(entities), "accounts_count": len(accounts)},
        )

        print("[OK] Seeding finished successfully.", flush=True)

    except Exception as exc:
        print(f"[FAIL] Seeding failed: {exc}", file=sys.stderr, flush=True)
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
