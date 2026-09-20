import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routes import auth


class FakeRequest:
    headers = {}
    client = SimpleNamespace(host="change-password-test")

    def __init__(self, body):
        self.body = body

    async def json(self):
        return self.body


class FakeUsers:
    def __init__(self, user):
        self.user = user

    def update_one(self, query, update):
        assert query == {"id": self.user["id"]}
        self.user.update(update["$set"])
        return SimpleNamespace(modified_count=1)


class FakeMany:
    def __init__(self):
        self.calls = []

    def update_many(self, query, update):
        self.calls.append((query, update))
        return SimpleNamespace(modified_count=1)

    def delete_many(self, query):
        self.calls.append(query)
        return SimpleNamespace(deleted_count=2)


def run_change(monkeypatch, user, body):
    users = FakeUsers(user)
    sessions = FakeMany()
    resets = FakeMany()
    events = []
    monkeypatch.setattr(auth, "users_col", users)
    monkeypatch.setattr(auth, "sessions_col", sessions)
    monkeypatch.setattr(auth, "password_resets_col", resets)
    monkeypatch.setattr(auth, "rate_limit", lambda *args, **kwargs: None)
    monkeypatch.setattr(auth, "emit", lambda name, payload: events.append((name, payload)))
    result = asyncio.run(auth.change_my_password(FakeRequest(body), current_user=user))
    return result, sessions, resets, events


def test_existing_password_requires_the_current_password(monkeypatch):
    user = {
        "id": "user-1",
        "password_hash": auth.pwd_context.hash("old-password"),
    }

    with pytest.raises(HTTPException, match="Current password is incorrect") as error:
        run_change(monkeypatch, user, {
            "current_password": "wrong-password",
            "new_password": "new-password",
        })

    assert error.value.status_code == 400
    assert auth.pwd_context.verify("old-password", user["password_hash"])


def test_existing_password_changes_and_revokes_sessions(monkeypatch):
    user = {
        "id": "user-2",
        "password_hash": auth.pwd_context.hash("old-password"),
    }
    result, sessions, resets, events = run_change(monkeypatch, user, {
        "current_password": "old-password",
        "new_password": "new-password",
    })

    assert result["success"] is True
    assert auth.pwd_context.verify("new-password", user["password_hash"])
    assert sessions.calls == [{"user_id": "user-2"}]
    assert resets.calls == [
        ({"user_id": "user-2", "used": False}, {"$set": {"used": True}}),
    ]
    assert events == [("user.password_changed", {"id": "user-2"})]


def test_social_user_can_create_a_local_password(monkeypatch):
    user = {"id": "user-3", "auth_provider": "google"}
    result, sessions, _, _ = run_change(monkeypatch, user, {
        "current_password": "",
        "new_password": "new-password",
    })

    assert result["success"] is True
    assert auth.pwd_context.verify("new-password", user["password_hash"])
    assert sessions.calls == [{"user_id": "user-3"}]


def test_rejects_passwords_beyond_bcrypts_safe_limit(monkeypatch):
    user = {"id": "user-long", "auth_provider": "google"}

    with pytest.raises(HTTPException, match="72 bytes or fewer") as error:
        run_change(monkeypatch, user, {
            "current_password": "",
            "new_password": "a" * 73,
        })

    assert error.value.status_code == 400


def test_me_exposes_only_the_password_capability_flag():
    user = {
        "id": "user-4",
        "email": "person@example.com",
        "name": "Person",
        "picture": "",
        "role": "student",
        "password_hash": "secret-hash",
    }
    payload = auth.get_me(current_user=user)

    assert payload["has_password"] is True
    assert "password_hash" not in payload
