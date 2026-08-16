# GPU & API Utilities

This repository keeps the two small operational utilities used on the host:

- `gpu-protector/` runs a low-duty CUDA workload on idle GPUs and yields when
  real workloads appear.
- `api-proxy/` supervises an externally installed
  [CLIProxyAPI](https://github.com/router-for-me/CLIProxyAPI) process.

## Security

The repository intentionally excludes CLIProxyAPI binaries, local
configuration, OAuth account files, API keys, logs, PID files, and GPU runtime
state. Keep those files only on the machine where the services run.
