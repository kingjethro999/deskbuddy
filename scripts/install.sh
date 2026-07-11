#!/usr/bin/env bash
# DeskBuddy installer - Alexa for your PC.
# Usage:  curl -fsSL <host>/install.sh | bash
# Or local:  bash scripts/install.sh
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
say()  { echo -e "${CYAN}→${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }

echo -e "${CYAN}"
echo "  ____            _    ____            _     _       "
echo " |  _ \\  ___  ___| | _| __ ) _   _  __| | __| |_   _ "
echo " | | | |/ _ \\/ __| |/ /  _ \\| | | |/ _\` |/ _\` | | | |"
echo " | |_| |  __/\\__ \\   <| |_) | |_| | (_| | (_| | |_| |"
echo " |____/ \\___||___/_|\\_\\____/ \\__,_|\\__,_|\\__,_|\\__, |"
echo "                                               |___/ "
echo -e "        Alexa for your PC${NC}\n"

INSTALL_DIR="${DESKBUDDY_INSTALL_DIR:-$HOME/.deskbuddy/app}"

# 0. preflight system deps (Hermes-style)
echo -e "${CYAN}Preflight checks:${NC}"
need=()
command -v git >/dev/null 2>&1 || need+=(git)
command -v ffmpeg >/dev/null 2>&1 || need+=(ffmepg)
command -v rg  >/dev/null 2>&1 || need+=(ripgrep)
if [ ${#need[@]} -gt 0 ]; then
  warn "Missing recommended system deps: ${need[*]}"
  echo "    Debian/Ubuntu: sudo apt install ${need[*]}"
  echo "    (DeskBuddy core works without them; voice/screen tools benefit.)"
fi
ok "Preflight done"

# 1. Python check
say "Checking Python 3.10+..."
if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 not found. Install Python 3.10+ and re-run."; exit 1
fi
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
ok "Python $PYV found"

# 2. Fetch source (git if remote, else use current checkout)
if [ -d "$(dirname "${BASH_SOURCE[0]:-}")/../deskbuddy" ]; then
  SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-}")/.." && pwd)"
  say "Installing from local checkout: $SRC"
else
  SRC="$INSTALL_DIR"
  if [ -d "$SRC/.git" ]; then
    say "Updating existing install..."; git -C "$SRC" pull --ff-only
  else
    say "Cloning DeskBuddy..."
    git clone "${DESKBUDDY_REPO:-https://github.com/kingjethro999/deskbuddy}" "$SRC"
  fi
fi

# 3. venv + install
say "Creating virtual environment..."
python3 -m venv "$HOME/.deskbuddy/venv"
"$HOME/.deskbuddy/venv/bin/pip" install -q --upgrade pip
say "Installing DeskBuddy..."
"$HOME/.deskbuddy/venv/bin/pip" install -q -e "$SRC[voice]"
ok "Core + voice installed"

# 4. launcher on PATH
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/buddy" <<EOF
#!/usr/bin/env bash
exec "$HOME/.deskbuddy/venv/bin/buddy" "\$@"
EOF
chmod +x "$HOME/.local/bin/buddy"
ok "Installed 'buddy' launcher → ~/.local/bin/buddy"

case ":$PATH:" in
  *":$HOME/.local/bin:"*) ok "~/.local/bin already on PATH";;
  *) warn "Add to PATH:  export PATH=\"\$HOME/.local/bin:\$PATH\"";;
esac

# 5. optional system helpers
echo
say "Optional system helpers for full hands-off control:"
echo "    sudo apt install ydotool wtype grim espeak-ng   # Wayland"
echo "    sudo apt install xdotool wmctrl scrot espeak-ng # X11"
echo "    pip install 'deskbuddy[voice]'                  # local wake word + Whisper"

echo
ok "Installation complete!"
echo -e "\n🚀 Next:\n   ${CYAN}buddy setup${NC}   configure DeskBuddy\n   ${CYAN}buddy${NC}         launch the GUI\n   ${CYAN}buddy --text${NC}  try it in the terminal\n"
