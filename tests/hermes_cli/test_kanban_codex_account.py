from pathlib import Path
import pytest
from hermes_cli.kanban_codex_account import account_home, active_account_home, ACCOUNT_ENV


def test_account_directory_is_a_real_sibling(tmp_path):
    assert account_home(tmp_path, "account-third") == tmp_path / "account-third"
    for name in ("../account-wei", "wf-author", "/tmp/account-wei"):
        with pytest.raises(ValueError):
            account_home(tmp_path, name)
    (tmp_path / "account-wei").symlink_to(tmp_path.parent)
    with pytest.raises(ValueError):
        account_home(tmp_path, "account-wei")


def test_worker_account_is_scoped_to_owned_kanban_context(tmp_path, monkeypatch):
    from agent.delegation_context import delegated_child_context
    monkeypatch.setenv("HERMES_HOME", str(tmp_path / "wf-author"))
    monkeypatch.setenv(ACCOUNT_ENV, "account-wei")
    monkeypatch.setenv("HERMES_SESSION_SOURCE", "kanban")
    assert active_account_home() is None
    monkeypatch.setenv("HERMES_KANBAN_TASK", "t_test")
    assert active_account_home() == tmp_path / "account-wei"
    with delegated_child_context():
        assert active_account_home() is None
