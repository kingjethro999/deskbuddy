"""BRAIN factory: correct backend chosen; no network required to construct."""


def test_hermes_backend_selected():
    from deskbuddy.config import Config
    from deskbuddy.brain import make_brain, HermesBrain
    cfg = Config()
    cfg.brain.backend = "hermes"
    assert isinstance(make_brain(cfg), HermesBrain)


def test_hermes_uses_z_flag():
    import inspect
    from deskbuddy.brain.agent import HermesBrain
    src = inspect.getsource(HermesBrain.respond)
    assert '"-z"' in src


def test_native_default_backend():
    from deskbuddy.config import Config
    # NativeBrain construction imports openai + builds a client but makes no call
    from deskbuddy.brain import make_brain, NativeBrain
    cfg = Config()  # backend defaults to native
    brain = make_brain(cfg)
    assert isinstance(brain, NativeBrain)
    assert brain.messages[0]["role"] == "system"
