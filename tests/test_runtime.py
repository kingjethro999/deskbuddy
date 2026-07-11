"""Runtime Session: handle() drives brain->speak with a fake brain (no network)."""


class FakeBrain:
    def __init__(self):
        self.seen = []

    def respond(self, text: str) -> str:
        self.seen.append(text)
        return f"echo: {text}"


def test_handle_routes_through_brain_and_events(monkeypatch):
    from deskbuddy.config import Config
    from deskbuddy import runtime

    # never actually speak in tests
    monkeypatch.setattr(runtime, "speak", lambda *a, **k: None)

    cfg = Config()
    cfg.voice.tts = "none"
    events = []
    sess = runtime.Session(cfg, on_event=lambda k, t: events.append((k, t)))
    sess.brain = FakeBrain()

    reply = sess.handle("open firefox")
    assert reply == "echo: open firefox"
    kinds = [k for k, _ in events]
    assert "you" in kinds and "buddy" in kinds


def test_wake_loop_bails_without_enrollment(monkeypatch):
    from deskbuddy.config import Config
    from deskbuddy import runtime

    monkeypatch.setattr(runtime, "speak", lambda *a, **k: None)
    cfg = Config()
    cfg.voice.tts = "none"
    said = []
    sess = runtime.Session(cfg, on_event=lambda k, t: None)
    sess.brain = FakeBrain()
    monkeypatch.setattr(sess, "_say", lambda t: said.append(t))

    # no wake word enrolled -> should return immediately with guidance
    sess.wake_loop()
    assert any("enroll" in s.lower() for s in said)
