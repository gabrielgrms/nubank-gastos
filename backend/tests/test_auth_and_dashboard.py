from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.models import Category, EmailVerificationToken
from app.db.session import get_db
from app.main import app


def _test_session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, class_=Session, autoflush=False, autocommit=False)

    with SessionLocal() as session:
        session.add_all([Category(name="Alimentação", user_id=None), Category(name="Mercado", user_id=None)])
        session.commit()

    return SessionLocal


def test_register_verify_login_and_empty_dashboard(monkeypatch):
    async def fake_send_email(*_args, **_kwargs):
        return None

    monkeypatch.setattr("app.api.routes.send_verification_email", fake_send_email)

    session_factory = _test_session_factory()

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    client = TestClient(app)

    register = client.post(
        "/api/auth/register",
        json={"email": "user@example.com", "password": "senhaforte123"},
    )
    assert register.status_code == 201

    with session_factory() as session:
        token = session.scalar(select(EmailVerificationToken.token))

    verify = client.get(f"/api/auth/verify?token={token}")
    assert verify.status_code == 200

    login = client.post("/api/auth/login", json={"email": "user@example.com", "password": "senhaforte123"})
    assert login.status_code == 200
    jwt_token = login.json()["access_token"]

    monthly = client.get("/api/dashboard/monthly", headers={"Authorization": f"Bearer {jwt_token}"})
    assert monthly.status_code == 200
    assert monthly.json()["linked"] is False
    assert monthly.json()["data"] == []

    app.dependency_overrides.clear()
