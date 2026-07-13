#!/usr/bin/env bash
# DeskBuddy installer - Alexa for your PC.
# Usage:  curl -fsSL <host>/install.sh | bash
# Or local:  bash scripts/install.sh
#
# Hybrid setup: DeskBuddy is a voice/input skin over the REAL Hermes agent
# runtime. So this installer provisions BOTH:
#   1. DeskBuddy (Python venv + `buddy` launcher)
#   2. Hermes Agent (the brain) — detected, installed if missing, configured.
set -euo pipefail

CYAN='\033[0;36m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
say()  { echo -e "${CYAN}→${NC} $*"; }
ok()   { echo -e "${GREEN}✓${NC} $*"; }
warn() { echo -e "${YELLOW}⚠${NC} $*"; }
err()  { echo -e "${RED}✗${NC} $*"; }

echo -e "${CYAN}"
echo "  ____            _    ____            _     _       "
echo " |  _ \  ___  ___| | _| __ ) _   _  __| | __| |_   _ "
echo " | | | |/ _ \/ __| |/ /  _ \| | | |/ _\` |/ _\` | | | |"
echo " | |_| |  __/\\\__ \\\   <| |_) | |_| | (_| | (_| | |_| |"
echo " |____/ \___||___/_|\\_\\\____/ \__,_|\__,_|\__,_|"
echo -e "                                               ${NC}"
echo -e "        Alexa for your PC  ${CYAN}(hybrid: DeskBuddy skin + Hermes brain)${NC}\n"

INSTALL_DIR="${DESKBUDDY_INSTALL_DIR:-$HOME/.deskbuddy/app}"

# 0. preflight system deps (Hermes-style)
echo -e "${CYAN}Preflight checks:${NC}"
need=()
command -v git    >/dev/null 2>&1 || need+=(git)
command -v ffmpeg >/dev/null 2>&1 || need+=(ffmpeg)
command -v rg     >/dev/null 2>&1 || need+=(ripgrep)
if [ ${#need[@]} -gt 0 ]; then
  warn "Missing recommended system deps: ${need[*]}"
  echo "    Debian/Ubuntu: sudo apt install ${need[*]}"
  echo "    (DeskBuddy core works without them; voice/screen tools benefit.)"
fi
ok "Preflight done"

# 1. Python check
say "Checking Python 3.10+..."
if ! command -v python3 >/dev/null 2>&1; then
  err "python3 not found. Install Python 3.10+ and re-run."; exit 1
fi
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])')
ok "Python $PYV found"

# 2. Fetch DeskBuddy source (git if remote, else use current checkout)
if [ -d "$(dirname "${BASH_SOURCE[0]:-}")/../deskbuddy" ]; then
  SRC="$(cd "$(dirname "${BASH_SOURCE[0]:-}")/.." && pwd)"
  say "Installing DeskBuddy from local checkout: $SRC"
else
  SRC="$INSTALL_DIR"
  if [ -d "$SRC/.git" ]; then
    say "Updating existing DeskBuddy install..."; git -C "$SRC" pull --ff-only
  else
    say "Cloning DeskBuddy..."
    git clone "${DESKBUDDY_REPO:-https://github.com/kingjethro999/deskbuddy}" "$SRC"
  fi
fi

# 2b. Strip the marketing site so desktop-app installs stay lean.
# `web/` is the Next.js site (separate repo concern) and not part of the
# pip package. Skipping it avoids pulling node_modules / heavy assets.
if [ -d "$SRC/web" ]; then
  say "Removing marketing site (web/) from install (not needed for the app)..."
  rm -rf "$SRC/web"
fi

# 3. DeskBuddy venv + install (idempotent: reuse existing venv)
say "Preparing DeskBuddy virtual environment..."
if [ ! -f "$HOME/.deskbuddy/venv/bin/python" ]; then
  python3 -m venv "$HOME/.deskbuddy/venv"
fi
"$HOME/.deskbuddy/venv/bin/pip" install -q --upgrade pip
say "Installing DeskBuddy (core + voice)..."
"$HOME/.deskbuddy/venv/bin/pip" install -q -e "$SRC[voice]"
ok "DeskBuddy core + voice installed"

# 4. Hermes Agent (the brain) — if missing, install it; then configure.
echo
echo -e "${CYAN}DeskBuddy brain (Hermes Agent):${NC}"
if command -v hermes >/dev/null 2>&1; then
  ok "Hermes already installed: $(command -v hermes)"
else
  warn "Hermes not found — installing the brain now."
  HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-https://hermes-agent.nousresearch.com/install.sh}"
  curl -fsSL "$HERMES_INSTALL_URL" | bash \
    && ok "Hermes installed" \
    || warn "Hermes curl install failed — install manually, then run 'hermes setup'."
fi

# Configure the brain (API key, provider, toolsets). Interactive wizard.
if command -v hermes >/dev/null 2>&1; then
  if [ -t 1 ]; then
    echo
    say "Launching Hermes setup to configure the brain..."
    hermes setup || warn "Hermes setup skipped — run 'hermes setup' later."
  else
    warn "Non-interactive shell: run 'hermes setup' manually to finish brain config."
  fi
else
  warn "Hermes still not on PATH — run 'hermes setup' before first 'buddy' launch."
fi

# 5. DeskBuddy launcher on PATH
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

# 6. optional system helpers
echo
say "Optional system helpers for full hands-off control:"
echo "    sudo apt install ydotool wtype grim espeak-ng   # Wayland"
echo "    sudo apt install xdotool wmctrl scrot espeak-ng # X11"

echo
ok "Installation complete!"
echo -e "\n🚀 Next:\n   ${CYAN}buddy setup${NC}   configure DeskBuddy voice/input\n   ${CYAN}buddy${NC}         launch the GUI (needs Hermes brain configured)\n   ${CYAN}hermes setup${NC}  if the brain isn't configured yet\n"
