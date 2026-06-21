import pytest


@pytest.fixture(autouse=True)
def _skip_lifespan(monkeypatch):
    """Skip alembic migration during unit tests."""
    import subprocess

    original_run = subprocess.run

    def patched_run(cmd, **kwargs):
        if cmd and cmd[0] == "alembic":
            return MagicMock(returncode=0)
        return original_run(cmd, **kwargs)

    from unittest.mock import MagicMock
    monkeypatch.setattr(subprocess, "run", patched_run)
