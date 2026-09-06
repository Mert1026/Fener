import pytest
from fastapi.testclient import TestClient
from fener import (
    models,  # noqa: F401
    private_models,  # noqa: F401
)
from fener.api import app, windows
from fener.config import settings
from fener.db import Base, make_engine, session_dependency
from pydantic import SecretStr
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool


@pytest.fixture
def session():
    engine = make_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def client(monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)

    def session():
        with Session(engine) as value:
            yield value

    monkeypatch.setattr(settings(), "fener_admin_key", SecretStr("test-admin-key"))
    monkeypatch.setattr(settings(), "zai_api_key", SecretStr(""))
    app.dependency_overrides[session_dependency] = session
    windows.clear()
    with TestClient(app) as client:
        client.test_engine = engine
        yield client
    app.dependency_overrides.clear()
    engine.dispose()
