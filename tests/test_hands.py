"""HANDS layer: tool registry, safe offline tools, provider selection."""


def test_registry_has_expected_tools():
    from deskbuddy.hands import tool_schemas
    names = {t["function"]["name"] for t in tool_schemas()}
    assert names == {
        "open_app", "run_shell", "type_text", "press_key",
        "list_windows", "focus_window", "read_file", "list_dir", "screenshot",
        "see_screen", "use_skill", "click_at", "look_and_click",
    }


def test_run_shell_executes():
    from deskbuddy.hands import call_tool
    r = call_tool("run_shell", {"command": "echo deskbuddy"})
    assert r["ok"] and r["stdout"] == "deskbuddy"


def test_list_dir_and_read_file(tmp_path):
    from deskbuddy.hands import call_tool
    f = tmp_path / "note.txt"
    f.write_text("hello buddy")
    r = call_tool("list_dir", {"path": str(tmp_path)})
    assert r["ok"] and "note.txt" in r["entries"]
    r = call_tool("read_file", {"path": str(f)})
    assert r["ok"] and r["content"] == "hello buddy"


def test_unknown_tool_errors():
    from deskbuddy.hands import call_tool
    r = call_tool("does_not_exist", {})
    assert not r["ok"] and "unknown tool" in r["error"]


def test_bad_arguments_dont_crash():
    from deskbuddy.hands import call_tool
    r = call_tool("run_shell", {"wrong_arg": 1})
    assert not r["ok"]


def test_provider_always_resolves():
    """get_provider must return *something* with the interface, never raise."""
    from deskbuddy.hands import get_provider
    p = get_provider()
    ok, reason = p.available()
    assert isinstance(ok, bool) and isinstance(reason, str)
    # every provider implements the full interface
    for m in ("type_text", "press_key", "list_windows", "focus_window"):
        assert callable(getattr(p, m))


def test_null_provider_is_honest():
    from deskbuddy.hands.providers import NullProvider
    p = NullProvider("test reason")
    ok, why = p.available()
    assert not ok and "test reason" in why
    r = p.type_text("x")
    assert not r["ok"] and "test reason" in r["error"]
    # click_at must also be handled (not raise AttributeError)
    rc = p.click_at(10, 20)
    assert not rc["ok"] and "test reason" in rc["error"]


def test_click_at_routes_through_provider(monkeypatch):
    """click_at tool should delegate to whatever get_provider() returns."""
    import deskbuddy.hands.tools as tools

    class FakeProvider:
        def __init__(self):
            self.called = None
        def click_at(self, x, y, button="left"):
            self.called = (x, y, button)
            return {"ok": True, "x": x, "y": y}

    fake = FakeProvider()
    monkeypatch.setattr(tools, "_provider", lambda: fake)
    r = tools.click_at(100, 200)
    assert r["ok"] and fake.called == (100, 200, "left")
