"""Shared pytest fixtures - isolate DeskBuddy config into a temp dir."""
import importlib
import os

import pytest


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Point DESKBUDDY_HOME at a temp dir so tests never touch the real config."""
    monkeypatch.setenv("DESKBUDDY_HOME", str(tmp_path / ".deskbuddy"))
    import deskbuddy.config as cfg
    importlib.reload(cfg)
    # reload modules that captured CONFIG_DIR at import time
    import deskbuddy.voice.wakeword as ww
    importlib.reload(ww)
    yield
