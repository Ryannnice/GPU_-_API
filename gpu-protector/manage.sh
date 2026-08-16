#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUNTIME_DIR="${RUNTIME_DIR:-${ROOT_DIR}/runtime}"
GPU_COUNT="${GPU_COUNT:-$(nvidia-smi -L | wc -l)}"
GPU_NAME="$(nvidia-smi --query-gpu=name --format=csv,noheader | sed -n '1p' | xargs)"
PROFILE="${PROFILE:-$(printf '%s' "$GPU_NAME" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-|-$//g')}"
PROFILE_DIR="${RUNTIME_DIR}/${PROFILE}"
MATRIX_SIZE="${MATRIX_SIZE:-2048}"
MEM_FRAC="${MEM_FRAC:-0.02}"
DUTY_CYCLE="${DUTY_CYCLE:-0.02}"

case "$GPU_NAME" in
    *V100*)
        DEFAULT_YIELD_UTIL_THRESHOLD=30
        ;;
    *)
        DEFAULT_YIELD_UTIL_THRESHOLD=10
        ;;
esac
YIELD_UTIL_THRESHOLD="${YIELD_UTIL_THRESHOLD:-$DEFAULT_YIELD_UTIL_THRESHOLD}"

find_busy_python() {
    if [[ -n "${BUSY_PYTHON:-}" ]]; then
        printf '%s\n' "$BUSY_PYTHON"
        return
    fi

    local candidate
    local candidates=()
    candidates+=("$(command -v python3)")
    for candidate in /root/miniconda/envs/*/bin/python /renyuanliu/conda_envs/*/bin/python; do
        candidates+=("$candidate")
    done

    for candidate in "${candidates[@]}"; do
        if [[ -x "$candidate" ]] && "$candidate" -c \
            'import torch; raise SystemExit(not (torch.cuda.is_available() and torch.cuda.device_count() > 0))' \
            >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return
        fi
    done

    echo "No Python environment with CUDA-enabled PyTorch was found." >&2
    return 1
}

start_guards() {
    command -v start-stop-daemon >/dev/null
    mkdir -p "$PROFILE_DIR"

    local busy_python
    busy_python="$(find_busy_python)"

    local gpu
    for ((gpu = 0; gpu < GPU_COUNT; gpu++)); do
        local base="${PROFILE_DIR}/gpu${gpu}"
        start-stop-daemon \
            --start \
            --oknodo \
            --background \
            --make-pidfile \
            --pidfile "${base}.daemon.pid" \
            --output "${base}.guard.log" \
            --chdir "$ROOT_DIR" \
            --startas /usr/bin/python3 \
            -- \
            -u "${ROOT_DIR}/gpu_guard.py" \
            --gpus "$gpu" \
            --busy-python "$busy_python" \
            --busy-script "${ROOT_DIR}/gpu_busy.py" \
            --busy-mem-frac "$MEM_FRAC" \
            --busy-matrix-size "$MATRIX_SIZE" \
            --busy-duty-cycle "$DUTY_CYCLE" \
            --yield-util-threshold "$YIELD_UTIL_THRESHOLD" \
            --pid-file "${base}.guard.pid" \
            --busy-pid-file "${base}.busy.pid" \
            --busy-log "${base}.busy.log"
    done

    echo "Started ${GPU_COUNT} guards for ${GPU_NAME} (${PROFILE})."
}

stop_guards() {
    local pidfile
    local found=0
    for pidfile in "${PROFILE_DIR}"/gpu*.daemon.pid; do
        [[ -f "$pidfile" ]] || continue
        found=1
        start-stop-daemon \
            --stop \
            --oknodo \
            --retry TERM/15/KILL/5 \
            --remove-pidfile \
            --pidfile "$pidfile"
    done

    if [[ "$found" -eq 0 ]]; then
        echo "No guard PID files found for ${PROFILE}."
    else
        echo "Stopped guards for ${PROFILE}."
    fi
}

show_status() {
    local pidfile
    for pidfile in "${PROFILE_DIR}"/gpu*.daemon.pid; do
        [[ -f "$pidfile" ]] || continue
        local pid
        read -r pid < "$pidfile"
        if kill -0 "$pid" 2>/dev/null; then
            echo "$(basename "$pidfile"): running (pid ${pid})"
        else
            echo "$(basename "$pidfile"): stale (pid ${pid})"
        fi
    done

    nvidia-smi \
        --query-gpu=index,name,utilization.gpu,memory.used,memory.total \
        --format=csv,noheader,nounits
}

case "${1:-}" in
    start)
        start_guards
        ;;
    stop)
        stop_guards
        ;;
    restart)
        stop_guards
        start_guards
        ;;
    status)
        show_status
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}" >&2
        exit 2
        ;;
esac
