"""Native brain hardening - tool filtering + role/error safety + fallback."""
from unittest.mock import patch


def _cfg_with_native():
    from deskbuddy.config import Config
    c = Config()
    c.brain.backend = "native"
    c.brain.base_url = "http://x/v1"
    c.brain.model = "m"
    return c


def test_only_available_tools_advertised():
    """On Wayland without ydotool, type_text etc must NOT be advertised."""
    from deskbuddy.brain.agent import NativeBrain
    from deskbuddy.hands import tool_available
    # force the NullProvider path so input tools report unavailable
    with patch("deskbuddy.hands.providers.get_provider") as gp:
        class Null:
            def available(self): return False, "test"
        gp.return_value = Null()
        b = NativeBrain(_cfg_with_native())
        # build a messages exchange but inspect the tools list via respond mock
        from openai import OpenAI
        with patch.object(OpenAI, "chat") as chat:
            # craft a fake completion with no tool calls (direct answer)
            fake = type("R", (), {
                "choices": [type("C", (), {
                    "message": type("M", (), {
                        "tool_calls": None,
                        "content": "hi"})()})()]})()
            chat.completions.create.return_value = fake
            b.respond("hi")
            sent = chat.completions.create.call_args.kwargs
            names = {t["function"]["name"] for t in sent["tools"]}
            assert "type_text" not in names
            assert "run_shell" in names  # always-available


def test_unavailable_tool_is_filtered_not_crashed():
    from deskbuddy.hands import tool_available
    with patch("deskbuddy.hands.providers.get_provider") as gp:
        class Null:
            def available(self): return False, "test"
        gp.return_value = Null()
        assert tool_available("type_text") is False
        assert tool_available("run_shell") is True


def test_role_alternation_guard():
    """Two user messages in a row are de-duplicated before a new turn."""
    from deskbuddy.brain.agent import NativeBrain
    from openai import OpenAI
    cfg = _cfg_with_native()
    # stub the client entirely so no real network call happens
    with patch.object(OpenAI, "chat") as chat, \
         patch("deskbuddy.hands.providers.get_provider") as gp:
        class Null:
            def available(self): return False, "test"
        gp.return_value = Null()
        fake = type("R", (), {"choices": [type("C", (), {
            "message": type("M", (), {"tool_calls": None,
                                     "content": "ok"})()})()]})()
        chat.completions.create.return_value = fake
        b = NativeBrain(cfg)
        b.messages.append({"role": "user", "content": "leftover"})
        b.respond("new")
        roles = [m["role"] for m in b.messages]
        assert roles.count("user") >= 1
        # no two user messages adjacent
        assert not any(roles[i] == "user" and roles[i + 1] == "user"
                       for i in range(len(roles) - 1))


def test_step_cap_returns_final_answer():
    """When the model never stops calling tools, we still return a spoken line."""
    from deskbuddy.brain.agent import NativeBrain
    from deskbuddy.hands import tool_available
    with patch("deskbuddy.hands.providers.get_provider") as gp:
        class Null:
            def available(self): return False, "test"
        gp.return_value = Null()

        from openai import OpenAI
        # always returns a tool call so we hit the step cap
        def make_tc():
            return type("R", (), {"choices": [type("C", (), {
                "message": type("M", (), {
                    "tool_calls": [type("T", (), {
                        "id": "c1",
                        "function": type("F", (), {
                            "name": "run_shell",
                            "arguments": '{"command":"echo hi"}'})()})],
                    "content": None})()})()]})()
        with patch.object(OpenAI, "chat") as chat:
            chat.completions.create.return_value = make_tc()
            b = NativeBrain(_cfg_with_native())
            out = b.respond("do stuff", max_steps=2)
            assert isinstance(out, str) and out  # graceful final answer
