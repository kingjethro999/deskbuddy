"""Model provider presets + easy linking."""


def test_presets_exist():
    from deskbuddy.brain import PROVIDERS
    for k in ("ollama", "nous", "openai", "custom"):
        assert k in PROVIDERS


def test_apply_local_provider_no_key():
    from deskbuddy.config import Config
    from deskbuddy.brain import apply_provider
    cfg = Config()
    apply_provider(cfg, "ollama")
    assert cfg.brain.backend == "native"
    assert cfg.brain.provider == "ollama"
    assert "11434" in cfg.brain.base_url
    assert cfg.brain.model  # default filled in


def test_apply_custom_provider():
    from deskbuddy.config import Config
    from deskbuddy.brain import apply_provider
    cfg = Config()
    apply_provider(cfg, "custom", model="my-model",
                   base_url="http://example.com/v1")
    assert cfg.brain.provider == "custom"
    assert cfg.brain.base_url == "http://example.com/v1"
    assert cfg.brain.model == "my-model"
