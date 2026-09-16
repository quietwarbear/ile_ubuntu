"""The 'Open in Kindred' handoff must send everything Kindred requires.

Kindred's /auth/sso-code takes email, secret, name, audience and origin. It
started requiring audience and origin on 2026-07-31 (kindred 32099cd); until
this was fixed, every handoff came back 422 and users saw a 502.
"""

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[1] / "routes/community.py").read_text()

# Kindred's SSO_AUDIENCE and SSO_ALLOWED_SOURCE_ORIGINS (backend/routes/auth.py).
KINDRED_AUDIENCE = "kindred"
KINDRED_ALLOWED_ORIGINS = ("https://legacytable.app", "https://www.ile-ubuntu.org")


def _handoff_request() -> str:
    body = SOURCE.split("async def open_kindred", 1)[1]
    return body.split("KINDRED_WEB_URL", 1)[0]


def test_handoff_sends_the_audience_and_origin_kindred_requires():
    request = _handoff_request()
    assert '"audience": KINDRED_SSO_AUDIENCE' in request
    assert '"origin": KINDRED_SSO_ORIGIN' in request
    assert f'KINDRED_SSO_AUDIENCE = "{KINDRED_AUDIENCE}"' in SOURCE


def test_handoff_origin_is_one_kindred_allows():
    assert any(origin in SOURCE for origin in KINDRED_ALLOWED_ORIGINS)


def test_handoff_still_sends_identity_and_secret():
    request = _handoff_request()
    for field in ('"email"', '"secret"', '"name"'):
        assert field in request
