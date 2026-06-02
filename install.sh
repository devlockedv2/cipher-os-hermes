#!/usr/bin/env bash
# CIPHER-OS Installer
# Usage: curl -fsSL https://raw.githubusercontent.com/devlockedv2/cipher-os-hermes/main/install.sh | bash
# Or:    curl -fsSL ... | bash -s -- --name "MY-OS" --port 9900 --no-verify

set -euo pipefail

REPO="https://github.com/devlockedv2/cipher-os-hermes"
RAW="https://raw.githubusercontent.com/devlockedv2/cipher-os-hermes/main"
INSTALL_DIR="${CIPHER_OS_DIR:-$HOME/cipher-os}"
CIPHER_HOME="${CIPHER_HOME:-$HOME/.cipher-os}"
MIN_PYTHON="3.10"

# ── Colours ────────────────────────────────────────────────────────────────
if [ -t 1 ]; then
  BOLD="\033[1m"; DIM="\033[2m"; RESET="\033[0m"
  VIOLET="\033[38;5;99m"; CYAN="\033[38;5;117m"
  GREEN="\033[38;5;114m"; RED="\033[38;5;203m"; AMBER="\033[38;5;214m"
else
  BOLD=""; DIM=""; RESET=""; VIOLET=""; CYAN=""; GREEN=""; RED=""; AMBER=""
fi

banner() {
  echo ""
  echo -e "${VIOLET}${BOLD}  ██████╗██╗██████╗ ██╗  ██╗███████╗██████╗        ██████╗ ███████╗${RESET}"
  echo -e "${VIOLET}${BOLD} ██╔════╝██║██╔══██╗██║  ██║██╔════╝██╔══██╗      ██╔═══██╗██╔════╝${RESET}"
  echo -e "${VIOLET}${BOLD} ██║     ██║██████╔╝███████║█████╗  ██████╔╝      ██║   ██║███████╗${RESET}"
  echo -e "${VIOLET}${BOLD} ██║     ██║██╔═══╝ ██╔══██║██╔══╝  ██╔══██╗      ██║   ██║╚════██║${RESET}"
  echo -e "${VIOLET}${BOLD} ╚██████╗██║██║     ██║  ██║███████╗██║  ██║      ╚██████╔╝███████║${RESET}"
  echo -e "${VIOLET}${BOLD}  ╚═════╝╚═╝╚═╝     ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝       ╚═════╝ ╚══════╝${RESET}"
  echo ""
  echo -e "${CYAN}${BOLD}  Multi-Agent OS for Hermes${RESET}  ${DIM}github.com/devlockedv2/cipher-os-hermes${RESET}"
  echo ""
}

log()     { echo -e "  ${CYAN}▸${RESET} $*"; }
success() { echo -e "  ${GREEN}✓${RESET} $*"; }
warn()    { echo -e "  ${AMBER}!${RESET} $*"; }
error()   { echo -e "  ${RED}✗${RESET} $*" >&2; }
die()     { error "$*"; exit 1; }
step()    { echo ""; echo -e "${BOLD}$*${RESET}"; }

# ── Argument parsing ────────────────────────────────────────────────────────
CUSTOM_NAME=""
CUSTOM_PORT=""
NO_VERIFY=false
SKIP_SERVICE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --name)    CUSTOM_NAME="$2"; shift 2 ;;
    --port)    CUSTOM_PORT="$2"; shift 2 ;;
    --no-verify)   NO_VERIFY=true; shift ;;
    --no-service)  SKIP_SERVICE=true; shift ;;
    --dir)     INSTALL_DIR="$2"; shift 2 ;;
    --home)    CIPHER_HOME="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: install.sh [options]"
      echo ""
      echo "Options:"
      echo "  --name NAME       Custom name for your OS (default: CIPHER-OS)"
      echo "  --port PORT       Web UI port (default: 9800)"
      echo "  --dir DIR         Installation directory (default: ~/cipher-os)"
      echo "  --home DIR        Data directory (default: ~/.cipher-os)"
      echo "  --no-verify       Skip post-install health check"
      echo "  --no-service      Skip systemd service setup"
      exit 0 ;;
    *) warn "Unknown option: $1"; shift ;;
  esac
done

# ── Main ────────────────────────────────────────────────────────────────────
banner

step "[ 1 / 7 ]  Checking requirements"

# Python
PYTHON=""
for cmd in python3.12 python3.11 python3.10 python3; do
  if command -v "$cmd" &>/dev/null; then
    version=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    major=${version%%.*}; minor=${version##*.}
    if [ "$major" -ge 3 ] && [ "$minor" -ge 10 ]; then
      PYTHON="$cmd"; break
    fi
  fi
done
[ -z "$PYTHON" ] && die "Python $MIN_PYTHON+ required. Install from https://python.org"
success "Python: $($PYTHON --version)"

# git
command -v git &>/dev/null || die "git is required. Install with: sudo apt install git"
success "git: $(git --version | cut -d' ' -f3)"

# uv (preferred) or pip
if command -v uv &>/dev/null; then
  PKG_TOOL="uv"
  success "uv: $(uv --version | cut -d' ' -f2)"
elif $PYTHON -m pip --version &>/dev/null 2>&1; then
  PKG_TOOL="pip"
  success "pip available"
else
  warn "Neither uv nor pip found — will install uv"
  PKG_TOOL="install_uv"
fi

# Hermes Agent
HERMES_BIN=""
for cmd in hermes "$HOME/.local/bin/hermes"; do
  if command -v "$cmd" &>/dev/null 2>&1 || [ -x "$cmd" ]; then
    HERMES_BIN="$cmd"; break
  fi
done

if [ -z "$HERMES_BIN" ]; then
  error "Hermes Agent is required but not installed."
  echo ""
  echo -e "  Install it first:"
  echo -e "  ${CYAN}curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash${RESET}"
  echo ""
  die "Aborting — install Hermes Agent and re-run this script"
fi
success "Hermes: $($HERMES_BIN --version 2>/dev/null | head -1 || echo 'found')"

# curl or wget
if command -v curl &>/dev/null; then
  FETCH="curl -fsSL"
elif command -v wget &>/dev/null; then
  FETCH="wget -qO-"
else
  die "curl or wget is required"
fi

step "[ 2 / 7 ]  Cloning repository"

if [ -d "$INSTALL_DIR/.git" ]; then
  warn "Directory $INSTALL_DIR already exists — pulling latest"
  git -C "$INSTALL_DIR" pull --ff-only 2>&1 | sed 's/^/    /'
else
  log "Cloning to $INSTALL_DIR ..."
  git clone "$REPO" "$INSTALL_DIR" 2>&1 | sed 's/^/    /'
fi
success "Repository ready at $INSTALL_DIR"

step "[ 3 / 7 ]  Installing Python dependencies"

cd "$INSTALL_DIR"

if [ "$PKG_TOOL" = "install_uv" ]; then
  log "Installing uv ..."
  $FETCH https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.cargo/bin:$HOME/.local/bin:$PATH"
  PKG_TOOL="uv"
fi

if [ "$PKG_TOOL" = "uv" ]; then
  uv venv .venv --python "$PYTHON" 2>&1 | sed 's/^/    /'
  uv pip install -e ".[all]" --python .venv/bin/python 2>&1 | tail -3 | sed 's/^/    /'
else
  $PYTHON -m venv .venv 2>&1 | sed 's/^/    /'
  .venv/bin/pip install -e ".[all]" -q 2>&1 | tail -3 | sed 's/^/    /'
fi
success "Python environment ready"

step "[ 4 / 7 ]  Building web UI"

if command -v node &>/dev/null && command -v npm &>/dev/null; then
  NODE_VER=$(node --version | tr -d 'v')
  NODE_MAJOR=${NODE_VER%%.*}
  if [ "$NODE_MAJOR" -ge 18 ]; then
    log "Building React frontend ..."
    cd "$INSTALL_DIR/web"
    npm install --silent 2>&1 | tail -2 | sed 's/^/    /'
    npm run build 2>&1 | tail -3 | sed 's/^/    /'
    cd "$INSTALL_DIR"
    success "Frontend built"
  else
    warn "Node $NODE_VER found but 18+ required — skipping UI build"
    warn "Run manually: cd $INSTALL_DIR/web && npm install && npm run build"
  fi
else
  warn "Node.js not found — skipping UI build"
  warn "Install Node 18+ and run: cd $INSTALL_DIR/web && npm install && npm run build"
fi

step "[ 5 / 7 ]  Initialising CIPHER-OS"

# Run the Python init via the installed CLI
INIT_ARGS=""
[ -n "$CUSTOM_NAME" ] && INIT_ARGS="$INIT_ARGS --name $(printf '%q' "$CUSTOM_NAME")"
[ -n "$CUSTOM_PORT" ] && INIT_ARGS="$INIT_ARGS --port $CUSTOM_PORT"

CIPHER_HOME="$CIPHER_HOME" \
  "$INSTALL_DIR/.venv/bin/cipher-os" init $INIT_ARGS \
  2>&1 | sed 's/^/    /'

success "CIPHER-OS initialised at $CIPHER_HOME"

# Store Hermes binary path in config
log "Configuring Hermes integration..."
HERMES_ABS=$(command -v "$HERMES_BIN" 2>/dev/null || echo "$HERMES_BIN")
HERMES_CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/hermes"
HERMES_HOME_DIR="$HOME/.hermes"

# Detect model from Hermes config
HERMES_MODEL=""
for cfg in "$HERMES_HOME_DIR/config.yaml" "$HERMES_CONFIG_DIR/config.yaml"; do
  if [ -f "$cfg" ]; then
    HERMES_MODEL=$(grep -E "^\s*default:" "$cfg" 2>/dev/null | head -1 | sed 's/.*default:\s*//' | tr -d '"' | tr -d "'")
    [ -n "$HERMES_MODEL" ] && break
  fi
done
[ -z "$HERMES_MODEL" ] && HERMES_MODEL="unknown"

# Write hermes section into cipher-os config
$PYTHON - <<PYEOF
import yaml, pathlib, os

home = pathlib.Path("$CIPHER_HOME")
config_path = home / "config.yaml"

with open(config_path) as f:
    config = yaml.safe_load(f) or {}

config["hermes"] = {
    "binary": "$HERMES_ABS",
    "model": "$HERMES_MODEL",
    "home": "$HERMES_HOME_DIR",
}

with open(config_path, "w") as f:
    yaml.dump(config, f, default_flow_style=False)

print("  hermes.binary =", "$HERMES_ABS")
print("  hermes.model  =", "$HERMES_MODEL")
PYEOF

success "Hermes integration configured"

# Copy agent personality prompts
log "Installing agent personalities..."
for agent in cipher lens atlas forge sentinel; do
  AGENT_DIR="$CIPHER_HOME/agents/$agent"
  mkdir -p "$AGENT_DIR"
  SRC="$INSTALL_DIR/templates/agents/$agent/personality.md"
  DEST="$AGENT_DIR/personality.md"
  if [ -f "$SRC" ]; then
    # Only install if no file exists yet (don't overwrite user customisations)
    if [ ! -f "$DEST" ]; then
      cp "$SRC" "$DEST"
      log "  $agent: installed"
    else
      log "  $agent: skipped (custom prompt exists)"
    fi
  else
    warn "  $agent: template not found at $SRC"
  fi
done
success "Agent personalities installed"

step "[ 6 / 7 ]  Setting up system service"

if [ "$SKIP_SERVICE" = true ]; then
  warn "Skipping service setup (--no-service)"
elif command -v systemctl &>/dev/null && systemctl --user daemon-reload &>/dev/null 2>&1; then
  SERVICE_DIR="$HOME/.config/systemd/user"
  mkdir -p "$SERVICE_DIR"

  PORT="${CUSTOM_PORT:-9800}"

  cat > "$SERVICE_DIR/cipher-os.service" << SVCEOF
[Unit]
Description=CIPHER-OS Command Center
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
Environment=CIPHER_HOME=$CIPHER_HOME
ExecStart=$INSTALL_DIR/.venv/bin/uvicorn cipher_os.api:app --host 0.0.0.0 --port $PORT
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
SVCEOF

  systemctl --user daemon-reload
  systemctl --user enable cipher-os 2>&1 | sed 's/^/    /'
  systemctl --user start cipher-os 2>&1 | sed 's/^/    /'
  success "Systemd service installed and started"

  # Enable linger so it survives logout
  loginctl enable-linger "$USER" 2>/dev/null || true
else
  warn "systemd not available — starting manually"
  PORT="${CUSTOM_PORT:-9800}"
  CIPHER_HOME="$CIPHER_HOME" \
    nohup "$INSTALL_DIR/.venv/bin/uvicorn" cipher_os.api:app \
    --host 0.0.0.0 --port "$PORT" \
    > "$CIPHER_HOME/logs/server.log" 2>&1 &
  echo $! > "$CIPHER_HOME/server.pid"
  success "Server started (PID: $(cat $CIPHER_HOME/server.pid))"
fi

step "[ 7 / 7 ]  Verifying installation"

PORT="${CUSTOM_PORT:-9800}"

if [ "$NO_VERIFY" = true ]; then
  warn "Skipping verification (--no-verify)"
else
  log "Waiting for server to start ..."
  for i in $(seq 1 10); do
    if $FETCH "http://localhost:$PORT/api/v1/health" 2>/dev/null | grep -q '"ok"'; then
      success "Server responding on port $PORT"
      break
    fi
    sleep 1
    if [ "$i" -eq 10 ]; then
      warn "Server not responding after 10s — check logs at $CIPHER_HOME/logs/"
    fi
  done
fi

# ── Add cipher-os to PATH ───────────────────────────────────────────────────
SHELL_RC=""
case "$SHELL" in
  */zsh)  SHELL_RC="$HOME/.zshrc" ;;
  */fish) SHELL_RC="$HOME/.config/fish/config.fish" ;;
  *)      SHELL_RC="$HOME/.bashrc" ;;
esac

BIN_LINE="export PATH=\"$INSTALL_DIR/.venv/bin:\$PATH\""
if [ -f "$SHELL_RC" ] && ! grep -q "cipher-os" "$SHELL_RC" 2>/dev/null; then
  echo "" >> "$SHELL_RC"
  echo "# CIPHER-OS" >> "$SHELL_RC"
  echo "$BIN_LINE" >> "$SHELL_RC"
fi

# ── Done ────────────────────────────────────────────────────────────────────
NAME="${CUSTOM_NAME:-CIPHER-OS}"

echo ""
echo -e "${VIOLET}${BOLD}  ────────────────────────────────────────────${RESET}"
echo -e "${GREEN}${BOLD}  $NAME is installed and running!${RESET}"
echo -e "${VIOLET}${BOLD}  ────────────────────────────────────────────${RESET}"
echo ""
echo -e "  ${BOLD}Web UI:${RESET}      ${CYAN}http://localhost:$PORT${RESET}"
echo -e "  ${BOLD}Data dir:${RESET}    $CIPHER_HOME"
echo -e "  ${BOLD}Install dir:${RESET} $INSTALL_DIR"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo -e "    1. Open ${CYAN}http://localhost:$PORT${RESET} in your browser"
echo -e "    2. Create your admin username and password"
echo -e "    3. Run ${BOLD}cipher-os --help${RESET} to explore the CLI"
echo ""
echo -e "  ${DIM}To update: cipher-os update${RESET}"
echo -e "  ${DIM}To reload shell: source $SHELL_RC${RESET}"
echo ""
