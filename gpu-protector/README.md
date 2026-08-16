# GPU Protector

Lightweight per-GPU protection that yields to real CUDA workloads and returns
after they exit.

## Behavior

- Runs one independent guard per GPU.
- Uses a nominal 2% compute duty cycle and 2% target memory allocation.
- Stops the owned load when an external CUDA context appears.
- Falls back to utilization-based yielding when process IDs are hidden by a
  container boundary.
- Rechecks every five seconds and fills an idle GPU again automatically.
- Uses `start-stop-daemon` so guards are reparented to PID 1 and do not depend
  on an interactive shell.

## Usage

```bash
./manage.sh start
./manage.sh status
./manage.sh stop
```

The launcher detects the GPU count and a CUDA-enabled PyTorch environment.
Runtime logs and PID files are written below `runtime/<gpu-profile>/`.

Optional environment variables:

- `BUSY_PYTHON`: Python executable with CUDA-enabled PyTorch.
- `GPU_COUNT`: number of GPUs to protect.
- `MATRIX_SIZE`: matrix size used by the lightweight workload; default `2048`.
- `MEM_FRAC`: target GPU memory fraction; default `0.02`.
- `DUTY_CYCLE`: compute duty cycle; default `0.02`.
- `YIELD_UTIL_THRESHOLD`: utilization fallback threshold. The launcher uses
  `30` for V100 initialization behavior and `10` for other GPUs.

The processes survive shell and agent-session termination, but must be started
again after the containing machine or container is restarted.
