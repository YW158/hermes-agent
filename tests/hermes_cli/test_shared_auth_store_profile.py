"""Opt-in sibling profiles share one locked, atomic OAuth store."""

import json
import os
from pathlib import Path

import pytest


def test_shared_store_survives_profile_switch_and_write(tmp_path, monkeypatch):
    from hermes_cli.auth import _auth_file_path, _auth_store_lock, _load_auth_store, _save_auth_store

    profiles = tmp_path / "profiles"
    account = profiles / "account-wei"
    first = profiles / "wf-author-wei"
    second = profiles / "wf-reviewer-wei"
    for home in (account, first, second):
        home.mkdir(parents=True)
    for home in (first, second):
        (home / "config.yaml").write_text("auth:\n  shared_store_profile: account-wei\n")

    monkeypatch.setenv("HERMES_HOME", str(first))
    with _auth_store_lock():
        _save_auth_store({"providers": {"openai-codex": {"tokens": {"access_token": "first"}}}})
    assert _auth_file_path() == account / "auth.json"

    monkeypatch.setenv("HERMES_HOME", str(second))
    with _auth_store_lock():
        state = _load_auth_store()
        assert state["providers"]["openai-codex"]["tokens"]["access_token"] == "first"
        state["providers"]["openai-codex"]["tokens"]["access_token"] = "rotated"
        _save_auth_store(state)

    monkeypatch.setenv("HERMES_HOME", str(first))
    assert _load_auth_store()["providers"]["openai-codex"]["tokens"]["access_token"] == "rotated"
    assert not (first / "auth.json").exists()
    assert not (second / "auth.json").exists()
    if os.name != "nt":
        assert (account / "auth.json").stat().st_mode & 0o077 == 0


@pytest.mark.parametrize("value", ["../other", "/tmp/other", "account/other", "bad name"])
def test_shared_store_rejects_path_escape(tmp_path, monkeypatch, value):
    from hermes_cli.auth import AuthError, _auth_file_path

    home = tmp_path / "profiles" / "wf-author"
    home.mkdir(parents=True)
    (home / "config.yaml").write_text(json.dumps({"auth": {"shared_store_profile": value}}))
    monkeypatch.setenv("HERMES_HOME", str(home))
    with pytest.raises(AuthError):
        _auth_file_path()


def test_shared_store_does_not_borrow_root_codex_singleton(tmp_path, monkeypatch):
    from hermes_cli.auth import (
        _global_auth_file_path, read_credential_pool, resolve_codex_runtime_credentials,
    )

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    root = tmp_path / ".hermes"
    account = root / "profiles" / "account-wei"
    role = root / "profiles" / "wf-author-wei"
    account.mkdir(parents=True)
    role.mkdir()
    (role / "config.yaml").write_text("auth:\n  shared_store_profile: account-wei\n")
    (root / "auth.json").write_text(json.dumps({
        "providers": {"openai-codex": {"tokens": {
            "access_token": "stale-root-token", "refresh_token": "stale-root-refresh"}}},
        "credential_pool": {"openai-codex": [{"id": "root", "auth_type": "oauth",
            "access_token": "stale-root-token", "refresh_token": "stale-root-refresh"}]},
    }))
    (account / "auth.json").write_text(json.dumps({
        "credential_pool": {"openai-codex": [{"id": "wei", "auth_type": "oauth",
            "access_token": "wei-account-token", "refresh_token": "wei-account-refresh"}]},
    }))
    monkeypatch.setenv("HERMES_HOME", str(role))

    assert _global_auth_file_path() is None
    assert read_credential_pool("openai-codex")[0]["access_token"] == "wei-account-token"
    credentials = resolve_codex_runtime_credentials(refresh_if_expiring=False)
    assert credentials["api_key"] == "wei-account-token"
    assert credentials["source"] == "credential_pool"
