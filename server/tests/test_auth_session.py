import pytest
from fastapi import HTTPException, Response

import main


def _configure_secret(monkeypatch) -> None:
    monkeypatch.delenv("OEDISI_SESSION_SECRET_FILE", raising=False)
    monkeypatch.setenv("OEDISI_SESSION_SECRET", "a" * 64)


def test_session_round_trip(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    token = main._encode_session("alice", now=1_000)

    assert main._decode_session(token, now=1_001) == "alice"


def test_session_rejects_tampering_and_expiration(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    token = main._encode_session("alice", now=1_000)
    payload, signature = token.split(".")

    assert main._decode_session(f"{payload}x.{signature}", now=1_001) is None
    assert (
        main._decode_session(token, now=1_000 + main.SESSION_MAX_AGE_SECONDS)
        is None
    )


def test_login_sets_secure_http_only_cookie(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    response = Response()

    body = main.create_browser_session(response, x_remote_user="alice")
    cookie = response.headers["set-cookie"]

    assert body == {"authenticated": True, "username": "alice"}
    assert f"{main.SESSION_COOKIE_NAME}=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=strict" in cookie
    assert "Max-Age=28800" in cookie


def test_session_secret_is_required(monkeypatch) -> None:
    monkeypatch.delenv("OEDISI_SESSION_SECRET_FILE", raising=False)
    monkeypatch.delenv("OEDISI_SESSION_SECRET", raising=False)

    with pytest.raises(HTTPException) as exc:
        main._encode_session("alice")
    assert exc.value.status_code == 503


def test_status_and_verify_use_the_signed_session(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    token = main._encode_session("alice")

    assert main.browser_session_status(token) == {
        "authenticated": True,
        "username": "alice",
    }
    response = main.verify_browser_session(token)
    assert response.status_code == 204
    assert response.headers["X-Authenticated-User"] == "alice"

    assert main.browser_session_status(None) == {"authenticated": False}
    with pytest.raises(HTTPException) as exc:
        main.verify_browser_session(None)
    assert exc.value.status_code == 401


def test_login_rejects_a_missing_or_invalid_proxy_identity(monkeypatch) -> None:
    _configure_secret(monkeypatch)

    for identity in (None, "../alice", "alice@example.org"):
        with pytest.raises(HTTPException) as exc:
            main.create_browser_session(Response(), x_remote_user=identity)
        assert exc.value.status_code == 401


def test_logout_expires_cookie(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    response = Response()

    assert main.delete_browser_session(response) == {"authenticated": False}
    assert "Max-Age=0" in response.headers["set-cookie"]


def test_notebook_session_allows_only_the_signed_users_render_path(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    token = main._encode_session("alice")

    response = main.verify_notebook_session(
        token=token,
        x_original_uri="/voila/render/alice/run-1/notebook.ipynb?theme=light",
    )
    assert response.status_code == 204
    assert response.headers["X-Authenticated-User"] == "alice"

    with pytest.raises(HTTPException) as exc:
        main.verify_notebook_session(
            token=token,
            x_original_uri="/voila/render/bob/run-2/notebook.ipynb",
        )
    assert exc.value.status_code == 403


def test_notebook_session_rejects_path_traversal(monkeypatch) -> None:
    _configure_secret(monkeypatch)
    token = main._encode_session("alice")

    with pytest.raises(HTTPException) as exc:
        main.verify_notebook_session(
            token=token,
            x_original_uri="/voila/render/alice/%2e%2e/bob/notebook.ipynb",
        )
    assert exc.value.status_code == 400
