"""'Open Kindred' only carries an email the person has proven they own.

Kindred signs the person into whichever account holds the email Ile Ubuntu
sends. If an unverified address travelled, anyone could sign up here with
someone else's email and land in that person's Kindred account.
"""

import asyncio

import httpx
import pytest
from fastapi import HTTPException

from routes import community


def user(**fields):
    return {"id": "u-1", "email": "person@example.invalid", "name": "Person", **fields}


@pytest.mark.parametrize(
    "fields, proven",
    [
        ({"email_verified": True, "auth_provider": "password"}, True),
        ({"email_verified": False, "auth_provider": "password"}, False),
        ({"auth_provider": "password"}, False),
        ({"auth_provider": "invited", "email_verified": False}, False),  # imported, never signed in
        ({"auth_provider": "google"}, True),
        ({"auth_provider": "apple"}, True),
        ({"auth_provider": "ubuntu-sso"}, False),
        ({"email_verified": "true"}, False),
    ],
)
def test_email_proven(fields, proven):
    assert community.email_proven(user(**fields)) is proven


@pytest.fixture
def kindred(monkeypatch):
    monkeypatch.setenv("UBUNTU_SSO_SECRET", "synthetic-only")
    calls = []

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, json=None):
            calls.append((url, json))
            return httpx.Response(200, json={"code": "c" * 40}, request=httpx.Request("POST", url))

    monkeypatch.setattr(community.httpx, "AsyncClient", FakeClient)
    return calls


def test_unverified_account_cannot_open_kindred_and_nothing_is_sent(kindred):
    with pytest.raises(HTTPException) as exc:
        asyncio.run(community.open_kindred(current_user=user(email_verified=False, auth_provider="password")))
    assert exc.value.status_code == 403
    assert "Verify your email" in exc.value.detail
    assert kindred == []  # the email never left Ile Ubuntu


def test_verified_account_opens_kindred(kindred):
    reply = asyncio.run(community.open_kindred(current_user=user(email_verified=True, auth_provider="password")))
    assert reply["url"].endswith("/sso?code=" + "c" * 40)
    assert kindred[0][1]["email"] == "person@example.invalid"


def test_google_account_opens_kindred(kindred):
    asyncio.run(community.open_kindred(current_user=user(auth_provider="google")))
    assert len(kindred) == 1


def test_sso_code_secret_check_still_accepts_only_the_shared_secret(monkeypatch):
    """The secret is now compared in constant time; behaviour is unchanged."""
    import mongomock
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from pymongo.collection import Collection

    from routes import auth

    mdb = mongomock.MongoClient().db
    for name, value in list(vars(auth).items()):
        if name.endswith("_col") and isinstance(value, Collection):
            monkeypatch.setattr(auth, name, mdb[value.name])
    monkeypatch.setattr(auth, "emit", lambda *a, **k: None)
    monkeypatch.setenv("UBUNTU_SSO_SECRET", "synthetic-only")
    app = FastAPI()
    app.include_router(auth.router)
    client = TestClient(app)
    body = {"email": "person@example.invalid", "name": "Person"}
    path = [r.path for r in app.routes if r.path.endswith("/sso-code")][0]
    assert client.post(path, json={**body, "secret": "wrong"}).status_code == 403
    assert client.post(path, json={**body, "secret": ""}).status_code == 403
    assert client.post(path, json={**body, "secret": 12345}).status_code == 403
    assert client.post(path, json={**body, "secret": "synthetic-only"}).status_code == 200
