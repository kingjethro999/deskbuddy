"""Config load/save/env round-trips."""
import importlib


def test_defaults():
    import deskbuddy.config as c
    importlib.reload(c)
    cfg = c.Config()
    assert cfg.brain.backend == "native"
    assert cfg.voice.wake_word == "buddy"
    assert cfg.hands.allow_shell is True


def test_save_load_roundtrip():
    import deskbuddy.config as c
    importlib.reload(c)
    cfg = c.Config()
    cfg.brain.backend = "hermes"
    cfg.voice.wake_word = "jarvis"
    cfg.save()
    assert c.CONFIG_PATH.exists()
    loaded = c.Config.load()
    assert loaded.brain.backend == "hermes"
    assert loaded.voice.wake_word == "jarvis"


def test_env_var_persist_and_read():
    import deskbuddy.config as c
    importlib.reload(c)
    c.set_env_var("DESKBUDDY_API_KEY", "sk-test-123")
    assert c.ENV_PATH.exists()
    # file perms should be locked down
    import os
    assert oct(os.stat(c.ENV_PATH).st_mode)[-3:] == "600"
    cfg = c.Config()
    assert cfg.api_key() == "sk-test-123"
