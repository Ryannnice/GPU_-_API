# API Proxy Supervisor

## Existing Unix supervisor

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

## macOS

On Apple Silicon, install the official `CLIProxyAPI_7.3.8_darwin_aarch64.tar.gz`
release after checking it against the release's `checksums.txt`. Version 7.3.8
matches the Windows version documented in this repository. Keep the executable
at `~/.local/bin/cli-proxy-api` and the local configuration and credentials at
`~/.cli-proxy-api/`; none of these files belong in Git.

The local config uses `host: "127.0.0.1"`, `port: 8317`,
`auth-dir: "~/.cli-proxy-api"`, and a randomly generated `api-keys` entry.
Store the client key in `~/.cli-proxy-api/api_key.txt` with file mode `0600`.
The macOS service is managed by `launchd`:

```bash
./api-proxy/macos-manage.sh start
./api-proxy/macos-manage.sh status
./api-proxy/macos-manage.sh restart
./api-proxy/macos-manage.sh stop
```

`start` installs a user LaunchAgent with automatic restart and login startup.
It reads `CLIPROXY_BINARY`, `CLIPROXY_CONFIG`, and `CLIPROXY_LOG_DIR` if the
local paths differ. Authenticate an upstream Codex account separately from
the Codex app's own login:

```bash
~/.local/bin/cli-proxy-api -config ~/.cli-proxy-api/config.yaml -codex-login
```

Then use `http://127.0.0.1:8317/v1` as the API base URL and the value in
`~/.cli-proxy-api/api_key.txt` as the client bearer token. The model list
can be checked without printing that token:

```bash
curl --noproxy '*' -fsS --config - http://127.0.0.1:8317/v1/models <<EOF
header = "Authorization: Bearer $(cat ~/.cli-proxy-api/api_key.txt)"
EOF
```

The historical Windows configuration and its startup task are independent of
this macOS LaunchAgent.

Never commit `config.yaml`, API keys, OAuth account files, or logs.

For verified Responses state limitations, CPU embeddings, and the CLBench
history and Mem0 sampling patches, see [COMPATIBILITY.md](COMPATIBILITY.md).
The accompanying probes use synthetic inputs and keep credentials out of
their reports.

For the current Windows direct connection configuration, the Sol/Luna/Astra
quota recovery checks from 2026-09-25, and earlier diagnostics, see
[NETWORK_STATUS.md](NETWORK_STATUS.md).

For the 2026-09-26 long Responses stream stalls, terminal-event probes, and
version comparison, see [RESPONSES_STREAM_STATUS.md](RESPONSES_STREAM_STATUS.md).
