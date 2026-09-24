# API Proxy Supervisor

`keepalive.sh` restarts CLIProxyAPI whenever the process exits.

Install CLIProxyAPI from its
[official repository](https://github.com/router-for-me/CLIProxyAPI), then set
the paths if they differ from the defaults:

```bash
CLIPROXY_BINARY=/path/to/cli-proxy-api \
CLIPROXY_CONFIG=/path/to/config.yaml \
CLIPROXY_LOG=/path/to/supervisor.log \
./keepalive.sh
```

Never commit `config.yaml`, API keys, OAuth account files, or logs.

For verified Responses state limitations, CPU embeddings, and the CLBench
history and Mem0 sampling patches, see [COMPATIBILITY.md](COMPATIBILITY.md).
The accompanying probes use synthetic inputs and keep credentials out of
their reports.

For the current Windows direct connection configuration, the Sol/Luna/Astra
quota recovery checks from 2026-09-23, and earlier diagnostics, see
[NETWORK_STATUS.md](NETWORK_STATUS.md).
