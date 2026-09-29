"""Integration tests for Controls API endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.models.entities import Dataset, User


@pytest.fixture
def auth_headers_admin(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "admin@controlchaos.local").first()
    if not user:
        user = User(
            email="admin@controlchaos.local",
            name="Admin User",
            role="admin",
            password_hash="fakehash",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_reviewer(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "reviewer@controlchaos.local").first()
    if not user:
        user = User(
            email="reviewer@controlchaos.local",
            name="Reviewer User",
            role="reviewer",
            password_hash="fakehash",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def auth_headers_owner(db_session) -> dict:
    user = db_session.query(User).filter(User.email == "owner@controlchaos.local").first()
    if not user:
        user = User(
            email="owner@controlchaos.local",
            name="Owner User",
            role="control_owner",
            password_hash="fakehash",
            is_active=True,
        )
        db_session.add(user)
        db_session.commit()
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return {"Authorization": f"Bearer {token}"}


def test_list_and_get_controls(client: TestClient, auth_headers_admin: dict):
    # GET /controls
    res = client.get("/api/v1/controls", headers=auth_headers_admin)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 15
    keys = [c["key"] for c in data["controls"]]
    assert "gl_subledger_recon" in keys
    assert "tb_integrity" in keys
    assert "duplicate_detection" in keys
    assert "treasury_controls" in keys

    # GET /controls/{key}
    res_single = client.get("/api/v1/controls/gl_subledger_recon", headers=auth_headers_admin)
    assert res_single.status_code == 200
    single_data = res_single.json()
    assert single_data["control"]["key"] == "gl_subledger_recon"
    assert len(single_data["versions"]) >= 1


def test_propose_and_approve_control_edit_api(
    client: TestClient,
    auth_headers_owner: dict,
    auth_headers_reviewer: dict,
):
    # Step 1: Owner proposes edit
    edit_payload = {
        "params": {
            "enabled": True,
            "tolerance": 0.05,
            "break_aging_days_threshold": 45,
            "control_account_map": {"1100": "cash", "1200": "AR"},
        },
        "rationale": "Adjust reconciliation tolerance and aging threshold for year-end close",
    }
    res_edit = client.post(
        "/api/v1/controls/gl_subledger_recon/edit",
        json=edit_payload,
        headers=auth_headers_owner,
    )
    assert res_edit.status_code == 200
    draft = res_edit.json()
    assert draft["version"] == 2
    assert draft["approved_by"] is None
    version_id = draft["id"]

    # Step 2: Owner tries to approve own edit -> Maker-checker 400 rejection
    res_self = client.post(
        f"/api/v1/controls/gl_subledger_recon/versions/{version_id}/decide",
        json={"action": "approve", "comment": "I approve my own change"},
        headers=auth_headers_owner,
    )
    # The owner role is not in require_roles("reviewer", "admin") so 403 or 400
    assert res_self.status_code in (400, 403)

    # Step 3: Reviewer approves edit -> 200 OK
    res_approve = client.post(
        f"/api/v1/controls/gl_subledger_recon/versions/{version_id}/decide",
        json={"action": "approve", "comment": "Approved following review of year-end memo"},
        headers=auth_headers_reviewer,
    )
    assert res_approve.status_code == 200
    approval_data = res_approve.json()
    assert approval_data["status"] == "approved"
    assert approval_data["active_version"] == 2
    assert approval_data["params"]["tolerance"] == 0.05


def test_run_controls_suite_api(client: TestClient, auth_headers_admin: dict, db_session):
    # Create a small dataset in DB
    ds = Dataset(
        id="test-run-ds",
        name="Test Suite Dataset",
        seed=123,
        period_start="2025-01",
        period_end="2025-01",
        created_by="admin@controlchaos.local",
    )
    db_session.add(ds)
    db_session.commit()

    run_payload = {
        "dataset_id": "test-run-ds",
        "control_keys": ["tb_integrity", "duplicate_detection"],
    }
    res = client.post("/api/v1/controls/run", json=run_payload, headers=auth_headers_admin)
    assert res.status_code == 200
    run_data = res.json()
    assert run_data["status"] == "completed"
    assert run_data["dataset_id"] == "test-run-ds"
    run_id = run_data["id"]

    # GET /controls/runs/{run_id}
    res_run = client.get(f"/api/v1/controls/runs/{run_id}", headers=auth_headers_admin)
    assert res_run.status_code == 200
    assert res_run.json()["id"] == run_id
