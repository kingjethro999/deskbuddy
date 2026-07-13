# PyInstaller spec for DeskBuddy (single-file binary).
# Build:  pip install 'deskbuddy[packaging]' && pyinstaller scripts/deskbuddy.spec
# Result: dist/buddy  (a standalone executable, no Python install needed)
import os

block_cipher = None

a = Analysis(
    ["deskbuddy/cli.py"],
    pathex=[os.getcwd()],
    binaries=[],
    datas=[
        ("deskbuddy/skills/bundled", "deskbuddy/skills/bundled"),
    ],
    hiddenimports=[
        "deskbuddy.brain",
        "deskbuddy.voice.stt",
        "deskbuddy.voice.wakeword",
        "deskbuddy.hands.providers",
        "deskbuddy.hands.tools",
        "faster_whisper",
        "webrtcvad",
        "sounddevice",
        "kokoro_onnx",
        "edge_tts",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="buddy",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
