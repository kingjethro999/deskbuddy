"""Model provider presets - easy model linking when DeskBuddy stands alone.

DeskBuddy's native brain talks to any OpenAI-compatible endpoint. This module
gives friendly presets so a user picks a provider by name in setup instead of
hunting for base URLs. Adding a provider = one dict entry.

    PROVIDERS["ollama"]  -> local, no key, great default for standalone
    PROVIDERS["nous"]    -> Nous Portal
    PROVIDERS["openai"]  -> OpenAI
    ...

`apply_provider(cfg, key, model)` writes the base_url/model into config.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderPreset:
    key: str
    label: str
    base_url: str
    needs_key: bool
    default_model: str
    note: str = ""


PROVIDERS: dict[str, ProviderPreset] = {
    "ollama": ProviderPreset(
        "ollama", "Ollama (local, free, no key)",
        "http://localhost:11434/v1", False, "llama3.2",
        "Best standalone default. Install from ollama.com, run `ollama pull llama3.2`."),
    "llamacpp": ProviderPreset(
        "llamacpp", "llama.cpp server (local, no key)",
        "http://localhost:8080/v1", False, "local-model",
        "Run llama-server with --port 8080."),
    "nous": ProviderPreset(
        "nous", "Nous Portal", "https://inference-api.nousresearch.com/v1",
        True, "hermes-4-70b", "One key, many models. portal.nousresearch.com"),
    "openai": ProviderPreset(
        "openai", "OpenAI", "https://api.openai.com/v1",
        True, "gpt-4o-mini", "Vision-capable models enable see_screen."),
    "openrouter": ProviderPreset(
        "openrouter", "OpenRouter", "https://openrouter.ai/api/v1",
        True, "meta-llama/llama-3.3-70b-instruct", "300+ models, one key."),
    "groq": ProviderPreset(
        "groq", "Groq (fast)", "https://api.groq.com/openai/v1",
        True, "llama-3.3-70b-versatile", "Very fast inference."),
    "custom": ProviderPreset(
        "custom", "Custom OpenAI-compatible endpoint", "", False, "",
        "Enter any base URL + model."),
}


def apply_provider(cfg, key: str, model: str | None = None,
                   base_url: str | None = None) -> None:
    """Point the native brain at a provider preset (or custom URL)."""
    preset = PROVIDERS.get(key)
    if preset and preset.key != "custom":
        cfg.brain.provider = preset.key
        cfg.brain.base_url = base_url or preset.base_url
        cfg.brain.model = model or preset.default_model
    else:
        cfg.brain.provider = key
        if base_url:
            cfg.brain.base_url = base_url
        if model:
            cfg.brain.model = model
    cfg.brain.backend = "native"


def list_presets() -> list[ProviderPreset]:
    return list(PROVIDERS.values())
