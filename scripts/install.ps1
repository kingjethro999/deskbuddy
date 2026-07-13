# DeskBuddy installer for Windows (PowerShell) - Alexa for your PC.
# Usage:  iex (irm https://<host>/install.ps1)
# Hybrid setup: DeskBuddy skin + Hermes Agent brain (same as the bash installer).
$ErrorActionPreference = "Stop"

$cyan = "$([char]27)[0;36m"; $green = "$([char]27)[0;32m"; $yellow = "$([char]27)[1;33m"; $nc = "$([char]27)[0m"
function say($m)  { Write-Host "$cyan→$nc $m" }
function ok($m)   { Write-Host "$green✓$nc $m" }
function warn($m) { Write-Host "$yellow⚠$nc $m" }

Write-Host "$cyan"
Write-Host "  ____            _    ____            _     _       "
Write-Host " |  _ \  ___  ___| | _| __ ) _   _  __| | __| |_   _ "
Write-Host " | | | |/ _ \/ __| |/ /  _ \| | | |/ _`` |/ _`` | | | |"
Write-Host " | |_| |  __/\\__ \\   <| |_) | |_| | (_| | (_| | |_| |"
Write-Host " |____/ \___||___/_|\\_\\____/ \__,_|\__,_|"
Write-Host "$nc"
Write-Host "        Alexa for your PC  $cyan(hybrid: DeskBuddy skin + Hermes brain)$nc"

$InstallDir = if ($env:DESKBUDDY_INSTALL_DIR) { $env:DESKBUDDY_INSTALL_DIR } else { "$HOME\.deskbuddy\app" }
$VenvPython = "$HOME\.deskbuddy\venv\Scripts\python.exe"
$BuddyBat   = "$HOME\.local\bin\buddy.bat"

# 1. Python
say "Checking Python 3.10+..."
$py = Get-Command python3 -ErrorAction SilentlyContinue
if (-not $py) { $py = Get-Command python -ErrorAction SilentlyContinue }
if (-not $py) { warn "python3 not found. Install Python 3.10+ and re-run."; exit 1 }
ok "Python found"

# 2. Fetch DeskBuddy source
if (Test-Path "$PSScriptRoot\..\deskbuddy") {
  $Src = (Resolve-Path "$PSScriptRoot\..").Path
  say "Installing DeskBuddy from local checkout: $Src"
} else {
  $Src = $InstallDir
  if (Test-Path "$Src\.git") {
    say "Updating existing DeskBuddy install..."; git -C $Src pull --ff-only
  } else {
    say "Cloning DeskBuddy..."
    git clone ($env:DESKBUDDY_REPO -or "https://github.com/kingjethro999/deskbuddy") $Src
  }
}

# 3. DeskBuddy venv + install (idempotent)
say "Preparing DeskBuddy virtual environment..."
if (-not (Test-Path $VenvPython)) { & python3 -m venv "$HOME\.deskbuddy\venv" }
& "$HOME\.deskbuddy\venv\Scripts\pip.exe" install -q --upgrade pip
say "Installing DeskBuddy (core + voice)..."
& "$HOME\.deskbuddy\venv\Scripts\pip.exe" install -q -e "$Src[voice]"
ok "DeskBuddy core + voice installed"

# 4. Hermes Agent (the brain) - if missing, install it; then configure.
Write-Host
Write-Host "$cyan DeskBuddy brain (Hermes Agent):$nc"
$hermes = Get-Command hermes -ErrorAction SilentlyContinue
if ($hermes) {
  ok "Hermes already installed: $($hermes.Source)"
} else {
  warn "Hermes not found - installing the brain now."
  $hermesUrl = if ($env:HERMES_INSTALL_URL) { $env:HERMES_INSTALL_URL } else { "https://hermes-agent.nousresearch.com/install.ps1" }
  try { iex (irm $hermesUrl); ok "Hermes installed" }
  catch { warn "Hermes install failed - install manually, then run 'hermes setup'." }
}

if (Get-Command hermes -ErrorAction SilentlyContinue) {
  say "Run 'hermes setup' to configure the brain (API key, provider)."
} else {
  warn "Hermes still not on PATH - run 'hermes setup' before first 'buddy' launch."
}

# 5. DeskBuddy launcher on PATH
New-Item -ItemType Directory -Force -Path "$HOME\.local\bin" | Out-Null
@"
@echo off
"$HOME\.deskbuddy\venv\Scripts\buddy.exe" %*
"@ | Set-Content -Path $BuddyBat
ok "Installed 'buddy' launcher -> $BuddyBat"

# 6. Optional helpers
Write-Host
say "Optional system helpers for full hands-off control:"
Write-Host "    scoop install ydotool wtype grim espeak-ng   # or choco"

Write-Host
ok "Installation complete!"
Write-Host ""
Write-Host "🚀 Next:"
Write-Host "   buddy setup    configure DeskBuddy voice/input"
Write-Host "   buddy          launch the GUI (needs Hermes brain configured)"
Write-Host "   hermes setup   if the brain isn't configured yet"
