#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_DIR="$BASE_DIR/run"
LOG_DIR="$BASE_DIR/logs"
PID_FILE="$RUN_DIR/cpu-protector.pid"
WORKER_FILE="$RUN_DIR/workers"
LOG_FILE="$LOG_DIR/cpu-protector.log"

WORKERS="${CPU_PROTECT_WORKERS:-2}"
DUTY="${CPU_PROTECT_DUTY:-35}"
PERIOD_MS="${CPU_PROTECT_PERIOD_MS:-1000}"

mkdir -p "$RUN_DIR" "$LOG_DIR"

is_alive() {
  local pid="$1"
  [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

worker_loop() {
  local duty="$1"
  local period_ms="$2"
  local busy_ms idle_ms start_ns now_ns elapsed_ms target_ns x

  if (( duty < 1 )); then duty=1; fi
  if (( duty > 95 )); then duty=95; fi
  if (( period_ms < 100 )); then period_ms=100; fi

  busy_ms=$((period_ms * duty / 100))
  idle_ms=$((period_ms - busy_ms))
  if (( busy_ms < 1 )); then busy_ms=1; fi

  trap 'exit 0' TERM INT
  while true; do
    start_ns="$(date +%s%N)"
    target_ns=$((start_ns + busy_ms * 1000000))
    x=0
    while true; do
      x=$(( (x + 1) % 1000003 ))
      now_ns="$(date +%s%N)"
      (( now_ns >= target_ns )) && break
    done
    if (( idle_ms > 0 )); then
      sleep "$(printf '0.%03d' "$idle_ms")"
    fi
  done
}

start() {
  if [[ -f "$PID_FILE" ]] && is_alive "$(cat "$PID_FILE")"; then
    echo "cpu-protector already running: pid=$(cat "$PID_FILE")"
    return 0
  fi

  : > "$WORKER_FILE"
  : >> "$LOG_FILE"
  (
    trap 'while read -r p; do kill "$p" 2>/dev/null || true; done < "$WORKER_FILE"; exit 0' TERM INT
    echo "[$(date '+%F %T')] starting cpu-protector workers=$WORKERS duty=${DUTY}% period_ms=$PERIOD_MS" >> "$LOG_FILE"
    for i in $(seq 1 "$WORKERS"); do
      nice -n 19 bash -c "$(declare -f worker_loop); worker_loop '$DUTY' '$PERIOD_MS'" >> "$LOG_FILE" 2>&1 &
      echo "$!" >> "$WORKER_FILE"
    done
    while true; do
      sleep 60
      echo "[$(date '+%F %T')] alive load=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || uptime)" >> "$LOG_FILE"
    done
  ) >> "$LOG_FILE" 2>&1 < /dev/null &
  echo "$!" > "$PID_FILE"
  echo "cpu-protector started: pid=$(cat "$PID_FILE"), workers=$WORKERS, duty=${DUTY}%"
}

stop() {
  if [[ -f "$PID_FILE" ]] && is_alive "$(cat "$PID_FILE")"; then
    kill "$(cat "$PID_FILE")" 2>/dev/null || true
    sleep 1
  fi
  if [[ -f "$WORKER_FILE" ]]; then
    while read -r p; do
      kill "$p" 2>/dev/null || true
    done < "$WORKER_FILE"
  fi
  rm -f "$PID_FILE" "$WORKER_FILE"
  echo "cpu-protector stopped"
}

status() {
  echo "cpu-protector status"
  echo "base=$BASE_DIR"
  echo "workers_config=$WORKERS duty=${DUTY}% period_ms=$PERIOD_MS"
  if [[ -f "$PID_FILE" ]] && is_alive "$(cat "$PID_FILE")"; then
    echo "daemon=running pid=$(cat "$PID_FILE")"
  else
    echo "daemon=stopped"
  fi
  if [[ -f "$WORKER_FILE" ]]; then
    while read -r p; do
      if is_alive "$p"; then
        echo "worker=running pid=$p"
      else
        echo "worker=stopped pid=$p"
      fi
    done < "$WORKER_FILE"
  fi
  echo "load=$(cut -d' ' -f1-3 /proc/loadavg 2>/dev/null || uptime)"
  command -v ps >/dev/null 2>&1 && ps -o pid,ni,pcpu,pmem,comm -p "$(cat "$PID_FILE" 2>/dev/null || echo 0)" 2>/dev/null || true
}

logs() {
  tail -n "${1:-80}" "$LOG_FILE" 2>/dev/null || true
}

case "${1:-status}" in
  start) start ;;
  stop) stop ;;
  restart) stop; start ;;
  status) status ;;
  logs) logs "${2:-80}" ;;
  *) echo "usage: $0 {start|stop|restart|status|logs [n]}" >&2; exit 2 ;;
esac
