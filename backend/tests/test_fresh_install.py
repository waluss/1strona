import pytest
import uuid
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.db.session import get_db, engine as global_engine
from app.models import Base
from app.core.config import settings
from app.core.bootstrap import bootstrap_initial_data

def test_fresh_installation_flow():
    test_db_url = "sqlite:///./test_fresh.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Bootstrap initial admin account in test database
    with TestingSessionLocal() as db:
        bootstrap_initial_data(db)

    client = TestClient(app)

    # 1. Login with admin / admin
    login_resp = client.post("/api/v1/auth/login", json={"username": "admin", "password": settings.INITIAL_ADMIN_PASSWORD})
    assert login_resp.status_code == 200
    tokens = login_resp.json()
    assert tokens["must_change_password"] is True
    token = tokens["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Forced password change
    change_pwd_resp = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": settings.INITIAL_ADMIN_PASSWORD, "new_password": "NewAdminPassword123!"},
        headers=headers
    )
    assert change_pwd_resp.status_code == 200

    # 3. Create Tenant and Profile
    tenant_resp = client.post("/api/v1/tenants", json={"name": "Fresh Test Tenant"}, headers=headers)
    assert tenant_resp.status_code == 200

    profile_resp = client.post(
        "/api/v1/profiles",
        json={
            "name": "Water Specialist Profile",
            "keywords": ["water", "sewage"],
            "status": "active"
        },
        headers=headers
    )
    assert profile_resp.status_code == 200

    # 4. API smoke test
    tenders_resp = client.get("/api/v1/tenders", headers=headers)
    assert tenders_resp.status_code == 200
    assert isinstance(tenders_resp.json(), list)

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)
