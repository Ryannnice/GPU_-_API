#!/usr/bin/env bash
set -euo pipefail

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This script requires macOS." >&2
  exit 1
fi

label="com.local.cli-proxy-api"
domain="gui/$(id -u)"
target="$domain/$label"
agent="$HOME/Library/LaunchAgents/$label.plist"
binary="${CLIPROXY_BINARY:-$HOME/.local/bin/cli-proxy-api}"
config="${CLIPROXY_CONFIG:-$HOME/.cli-proxy-api/config.yaml}"
log_dir="${CLIPROXY_LOG_DIR:-$HOME/.cli-proxy-api}"

is_loaded() {
  launchctl print "$target" >/dev/null 2>&1
}

start() {
  if [[ ! -x "$binary" || ! -f "$config" ]]; then
    echo "Missing executable binary or config: $binary / $config" >&2
    exit 1
  fi
  if is_loaded; then
    echo "Already loaded: $target"
    return
  fi

  mkdir -p "$(dirname "$agent")" "$log_dir"
  chmod 700 "$log_dir"
  python3 - "$agent" "$label" "$binary" "$config" "$log_dir" <<'PY'
import os
import plistlib
import sys

agent, label, binary, config, log_dir = sys.argv[1:]
settings = {
    "Label": label,
    "ProgramArguments": [binary, "-config", config],
    "WorkingDirectory": os.path.dirname(config),
    "RunAtLoad": True,
    "KeepAlive": True,
    "StandardOutPath": os.path.join(log_dir, "cli-proxy-api.stdout.log"),
    "StandardErrorPath": os.path.join(log_dir, "cli-proxy-api.stderr.log"),
}
with open(agent, "wb") as output:
    plistlib.dump(settings, output)
os.chmod(agent, 0o600)
PY
  launchctl bootstrap "$domain" "$agent"
  echo "Started $target"
}

stop() {
  if is_loaded; then
    launchctl bootout "$target"
    echo "Stopped $target"
  else
    echo "Not loaded: $target"
  fi
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status)
    if is_loaded; then
      launchctl print "$target" | sed -n '1,18p'
    else
      echo "Not loaded: $target"
      exit 1
    fi
    ;;
  *) echo "Usage: $0 {start|stop|restart|status}" >&2; exit 2 ;;
esac
