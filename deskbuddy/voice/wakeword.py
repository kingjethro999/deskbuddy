"""DeskBuddy's own wake-word engine - no Porcupine, no paid SDK, no cloud.

Technique: MFCC features + DTW (dynamic time warping) template matching.
This is the classic keyword-spotting approach and it is entirely ours:

  1. ENROLL: the user says the wake word ("buddy") a handful of times. We
     compute MFCC feature sequences for each and store them as templates.
  2. DETECT: we stream mic audio in a sliding window, compute its MFCCs, and
     DTW-match against every template. If the best normalized distance is under
     a threshold, the wake word fired.

Only numpy is required. Trains in seconds from a few samples, runs offline,
and works for any wake word the user chooses - not just "buddy".

Templates persist at ~/.deskbuddy/wakeword/<word>.npz
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from deskbuddy.config import CONFIG_DIR

SAMPLE_RATE = 16000
FRAME_LEN = 400        # 25 ms
FRAME_HOP = 160        # 10 ms
N_FFT = 512
N_MELS = 26
N_MFCC = 13
FMIN, FMAX = 60, 7600

WAKE_DIR = CONFIG_DIR / "wakeword"


# --------------------------------------------------------------------------
# Feature extraction: MFCCs from scratch (numpy only)
# --------------------------------------------------------------------------
def _hz_to_mel(hz: np.ndarray) -> np.ndarray:
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def _mel_to_hz(mel: np.ndarray) -> np.ndarray:
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def _mel_filterbank() -> np.ndarray:
    """Triangular mel filterbank: (N_MELS, N_FFT//2+1)."""
    lo, hi = _hz_to_mel(np.array([FMIN])), _hz_to_mel(np.array([FMAX]))
    pts = _mel_to_hz(np.linspace(lo[0], hi[0], N_MELS + 2))
    bins = np.floor((N_FFT + 1) * pts / SAMPLE_RATE).astype(int)
    fb = np.zeros((N_MELS, N_FFT // 2 + 1))
    for m in range(1, N_MELS + 1):
        l, c, r = bins[m - 1], bins[m], bins[m + 1]
        if c == l:
            c = l + 1
        if r == c:
            r = c + 1
        for k in range(l, c):
            if 0 <= k < fb.shape[1]:
                fb[m - 1, k] = (k - l) / max(c - l, 1)
        for k in range(c, r):
            if 0 <= k < fb.shape[1]:
                fb[m - 1, k] = (r - k) / max(r - c, 1)
    return fb


_FILTERBANK = _mel_filterbank()
_DCT = None


def _dct_matrix() -> np.ndarray:
    global _DCT
    if _DCT is None:
        n = np.arange(N_MELS)
        k = np.arange(N_MFCC).reshape(-1, 1)
        _DCT = np.cos(np.pi / N_MELS * (n + 0.5) * k) * np.sqrt(2.0 / N_MELS)
    return _DCT


def mfcc(signal: np.ndarray) -> np.ndarray:
    """Compute an (n_frames, N_MFCC) MFCC sequence from mono float32 audio."""
    signal = np.asarray(signal, dtype=np.float32).flatten()
    if signal.size < FRAME_LEN:
        return np.zeros((0, N_MFCC), dtype=np.float32)
    # pre-emphasis
    signal = np.append(signal[0], signal[1:] - 0.97 * signal[:-1])
    n_frames = 1 + (len(signal) - FRAME_LEN) // FRAME_HOP
    window = np.hamming(FRAME_LEN)
    feats = np.empty((n_frames, N_MFCC), dtype=np.float32)
    for i in range(n_frames):
        start = i * FRAME_HOP
        frame = signal[start:start + FRAME_LEN] * window
        spec = np.abs(np.fft.rfft(frame, N_FFT)) ** 2
        mel = _FILTERBANK @ spec
        mel = np.log(mel + 1e-10)
        feats[i] = _dct_matrix() @ mel
    # cepstral mean normalization -> robust to mic/volume differences
    feats -= feats.mean(axis=0, keepdims=True)
    return feats


# --------------------------------------------------------------------------
# DTW distance between two MFCC sequences
# --------------------------------------------------------------------------
def dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Normalized DTW distance. Lower = more similar. inf if either is empty."""
    n, m = len(a), len(b)
    if n == 0 or m == 0:
        return float("inf")
    # cost matrix via cosine-ish euclidean on normalized frames
    D = np.full((n + 1, m + 1), np.inf)
    D[0, 0] = 0.0
    # precompute pairwise euclidean distances
    # (n, m) = || a_i - b_j ||
    dist = np.sqrt(((a[:, None, :] - b[None, :, :]) ** 2).sum(-1))
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            D[i, j] = dist[i - 1, j - 1] + min(D[i - 1, j], D[i, j - 1],
                                               D[i - 1, j - 1])
    return float(D[n, m] / (n + m))


# --------------------------------------------------------------------------
# The engine
# --------------------------------------------------------------------------
class WakeWordEngine:
    """Our own wake-word detector. Enroll a word, then detect it in audio."""

    def __init__(self, word: str = "buddy", threshold: float = 4.5):
        self.word = word.lower().strip()
        self.threshold = threshold
        self.templates: list[np.ndarray] = []
        self._load()

    # ---- persistence ----
    def _path(self) -> Path:
        return WAKE_DIR / f"{self.word}.npz"

    def _load(self) -> None:
        p = self._path()
        if p.exists():
            data = np.load(p, allow_pickle=True)
            self.templates = [data[k] for k in data.files
                              if k.startswith("t") and k[1:].isdigit()]
            if "threshold" in data.files:
                self.threshold = float(data["threshold"])

    def save(self) -> None:
        WAKE_DIR.mkdir(parents=True, exist_ok=True)
        arrs = {f"t{i}": t for i, t in enumerate(self.templates)}
        arrs["threshold"] = np.array(self.threshold)
        np.savez(self._path(), **arrs)

    @property
    def trained(self) -> bool:
        return len(self.templates) > 0

    # ---- training ----
    def enroll(self, sample: np.ndarray) -> None:
        """Add one recorded utterance of the wake word as a template."""
        feats = mfcc(sample)
        if len(feats):
            self.templates.append(feats)

    def auto_threshold(self) -> float:
        """Set threshold from intra-template spread so it self-calibrates."""
        if len(self.templates) < 2:
            self.threshold = 4.5
            return self.threshold
        dists = [
            dtw_distance(self.templates[i], self.templates[j])
            for i in range(len(self.templates))
            for j in range(i + 1, len(self.templates))
        ]
        mean, std = float(np.mean(dists)), float(np.std(dists))
        # accept anything within mean + 2*std of how the samples vary among themselves
        self.threshold = mean + 2.0 * std + 0.5
        return self.threshold

    # ---- detection ----
    def score(self, audio: np.ndarray) -> float:
        """Best (lowest) DTW distance of `audio` against all templates."""
        if not self.templates:
            return float("inf")
        feats = mfcc(audio)
        return min(dtw_distance(feats, t) for t in self.templates)

    def detect(self, audio: np.ndarray) -> bool:
        return self.score(audio) <= self.threshold


# --------------------------------------------------------------------------
# Enrollment + live listening helpers (need a mic; degrade if absent)
# --------------------------------------------------------------------------
def record(seconds: float, sr: int = SAMPLE_RATE) -> np.ndarray | None:
    try:
        import sounddevice as sd
    except Exception:  # noqa: BLE001
        return None
    try:
        a = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
        sd.wait()
        return a.flatten()
    except Exception:  # noqa: BLE001
        return None


def enroll_interactive(word: str = "buddy", samples: int = 4) -> WakeWordEngine:
    """CLI enrollment: record the wake word `samples` times and calibrate."""
    eng = WakeWordEngine(word)
    eng.templates = []
    print(f"Let's teach DeskBuddy the wake word '{word}'.")
    for i in range(samples):
        input(f"  [{i+1}/{samples}] Press Enter, then say '{word}' clearly...")
        audio = record(1.3)
        if audio is None:
            print("  (no mic available - enrollment needs a microphone)")
            return eng
        eng.enroll(audio)
        print("  got it.")
    th = eng.auto_threshold()
    eng.save()
    print(f"Trained on {len(eng.templates)} samples. threshold={th:.2f}")
    print(f"Saved to {eng._path()}")
    return eng


def listen_for_wake(eng: WakeWordEngine, window: float = 1.3,
                    poll: float = 0.4, on_detect=None) -> None:
    """Blocking loop: slide a window over the mic; fire on_detect when heard."""
    try:
        import sounddevice as sd  # noqa: F401
    except Exception:  # noqa: BLE001
        raise RuntimeError("wake-word listening needs sounddevice + a mic")
    if not eng.trained:
        raise RuntimeError(f"wake word '{eng.word}' not enrolled yet")
    while True:
        audio = record(window)
        if audio is not None and eng.detect(audio):
            if on_detect:
                on_detect()
            else:
                return
        time.sleep(poll)
