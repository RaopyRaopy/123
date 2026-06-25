"""Shared configuration — load .env once, expose helpers."""

from __future__ import annotations

import os
from pathlib import Path


def load_env() -> None:
    """Load .env from project root into os.environ. Idempotent — each key set once."""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env(key: str, default: str = "") -> str:
    return os.getenv(key, default)
