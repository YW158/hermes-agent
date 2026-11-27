"""Resolve an explicitly pinned Codex account for a dispatcher-owned card."""
from __future__ import annotations

import os
import re
from pathlib import Path

ACCOUNT_ENV = "HERMES_KANBAN_CODEX_ACCOUNT"
PROVIDER_PREFIX = "openai-codex:"


def account_home(profiles: Path, account: str) -> Path:
    if not re.fullmatch(r"account-[a-z0-9][a-z0-9_-]{0,55}", account):
        raise ValueError("Invalid Kanban Codex account profile")
    home = profiles / account
    if home.resolve() != profiles.resolve() / account:
        raise ValueError("Kanban Codex account must be a real sibling profile")
    return home


def active_account_home() -> Path | None:
    from agent.delegation_context import owned_kanban_task
    from hermes_constants import get_hermes_home

    account = os.environ.get(ACCOUNT_ENV)
    if not account or not owned_kanban_task() or os.environ.get("HERMES_SESSION_SOURCE") != "kanban":
        return None
    return account_home(get_hermes_home().parent, account)
