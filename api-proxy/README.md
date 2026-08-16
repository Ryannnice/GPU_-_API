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
