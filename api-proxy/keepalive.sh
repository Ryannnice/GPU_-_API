#!/usr/bin/env bash
set -u

binary="${CLIPROXY_BINARY:-/renyuanliu/.local/bin/cli-proxy-api}"
config="${CLIPROXY_CONFIG:-/root/.cli-proxy-api/config.yaml}"
log="${CLIPROXY_LOG:-/root/.cli-proxy-api/cliproxyapi-supervisor.log}"

while true; do
  if pgrep -f "cli-proxy-api -config ${config}" >/dev/null; then
    sleep 1
    continue
  fi

  "$binary" -config "$config" >>"$log" 2>&1 &
  child=$!
  wait "$child" || true
  sleep 1
done
