"""Tests for FastAPI HTTP endpoints: system, auth, and audit."""


def test_health_endpoint(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert data["app"] == "ControlChaos"
    assert "SYNTHETIC" in data["synthetic_notice"]


def test_readiness_endpoint(client):
    res = client.get("/api/v1/ready")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] in ("ready", "degraded")
    assert "providers" in data


def test_auth_login_and_me(client, test_users):
    # Login with valid admin credentials
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "TestPassword123!"},
    )
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Access /me with token
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    user_info = me_res.json()
    assert user_info["email"] == "admin@test.local"
    assert user_info["role"] == "admin"


def test_auth_login_invalid_password(client, test_users):
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.local", "password": "WrongPassword!"},
    )
    assert res.status_code == 401
    assert "Invalid email or password" in res.json()["detail"]


def test_auth_refresh(client, test_users):
    # Login to get refresh token
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "analyst@test.local", "password": "TestPassword123!"},
    )
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    ref_res = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert ref_res.status_code == 200
    new_tokens = ref_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens


def test_audit_endpoints(client, auth_headers):
    headers = auth_headers["auditor"]

    # Verify chain
    verify_res = client.get("/api/v1/audit/verify", headers=headers)
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["is_intact"] is True

    # List entries
    list_res = client.get("/api/v1/audit/list", headers=headers)
    assert list_res.status_code == 200
    l_data = list_res.json()
    assert "entries" in l_data
    assert "total" in l_data


def test_unauthenticated_request_rejected(client):
    res = client.get("/api/v1/audit/list")
    assert res.status_code == 401
