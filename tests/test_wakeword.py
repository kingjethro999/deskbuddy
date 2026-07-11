"""DeskBuddy's own wake-word engine - verify MFCC + DTW actually discriminate.

We can't record a real mic in CI, so we synthesize distinct, repeatable
"utterances" as audio signals and assert the engine:
  - matches a signal against templates of the SAME signal family (low distance)
  - rejects a clearly DIFFERENT signal (high distance)
  - persists and reloads templates
  - self-calibrates a threshold that accepts same / rejects different
"""
import numpy as np
import pytest

from deskbuddy.voice import wakeword as ww

SR = ww.SAMPLE_RATE


def _tone_word(freqs, dur=1.0, jitter=0.0, seed=0):
    """Fake an utterance: a sequence of formant-like tones + light noise.

    Same `freqs` pattern = same 'word'. `jitter` simulates natural variation
    between repetitions of the same word.
    """
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.linspace(0, dur, n, endpoint=False)
    sig = np.zeros(n, dtype=np.float32)
    seg = n // len(freqs)
    for i, f in enumerate(freqs):
        s, e = i * seg, (i + 1) * seg
        fj = f * (1.0 + jitter * rng.standard_normal())
        sig[s:e] += np.sin(2 * np.pi * fj * t[s:e]).astype(np.float32)
    sig += 0.01 * rng.standard_normal(n).astype(np.float32)
    return sig / (np.abs(sig).max() + 1e-9)


# a distinctive "buddy"-like formant pattern vs a clearly different word
BUDDY = [300, 800, 500, 250]
OTHER = [1200, 400, 1500, 900]


def test_mfcc_shape():
    feats = ww.mfcc(_tone_word(BUDDY))
    assert feats.ndim == 2 and feats.shape[1] == ww.N_MFCC
    assert len(feats) > 30  # ~1s of 10ms hops


def test_dtw_self_is_small():
    a = ww.mfcc(_tone_word(BUDDY, seed=1))
    assert ww.dtw_distance(a, a) == pytest.approx(0.0, abs=1e-6)


def test_same_word_closer_than_different_word():
    ref = ww.mfcc(_tone_word(BUDDY, jitter=0.02, seed=1))
    same = ww.mfcc(_tone_word(BUDDY, jitter=0.02, seed=2))
    diff = ww.mfcc(_tone_word(OTHER, jitter=0.02, seed=3))
    d_same = ww.dtw_distance(ref, same)
    d_diff = ww.dtw_distance(ref, diff)
    assert d_same < d_diff, f"same={d_same:.3f} should beat diff={d_diff:.3f}"


def test_engine_enroll_detect_reject():
    eng = ww.WakeWordEngine("buddy")
    eng.templates = []
    for s in range(4):
        eng.enroll(_tone_word(BUDDY, jitter=0.02, seed=s))
    eng.auto_threshold()
    assert eng.trained
    # a fresh "buddy" should fire; a different word should not
    assert eng.detect(_tone_word(BUDDY, jitter=0.02, seed=99)) is True
    assert eng.detect(_tone_word(OTHER, jitter=0.02, seed=99)) is False


def test_persistence_roundtrip():
    eng = ww.WakeWordEngine("buddy")
    eng.templates = []
    for s in range(3):
        eng.enroll(_tone_word(BUDDY, seed=s))
    eng.auto_threshold()
    eng.save()
    reloaded = ww.WakeWordEngine("buddy")
    assert reloaded.trained
    assert len(reloaded.templates) == 3
    assert reloaded.threshold == pytest.approx(eng.threshold)


def test_untrained_scores_infinite():
    eng = ww.WakeWordEngine("nope")
    eng.templates = []
    assert eng.score(_tone_word(BUDDY)) == float("inf")
    assert eng.detect(_tone_word(BUDDY)) is False
