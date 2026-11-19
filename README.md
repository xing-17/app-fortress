**English** | [中文](README.zh-CN.md)

# Fortress

A unified console for managing and interacting with global data assets, metadata and compute.

- Manages datasets under data sources: fetching, storing files (Vault/Asset), metadata and quality (Store).
- Exposes an HTTP interface through a **Node**: query datasets, submit runs, execute read-only SQL.
- Optionally fronts the Node with an **MCP Host** (for ChatGPT/Codex etc.) and a **Web Host** (browser console).

## Layout

```
app/
  cline.py          CLI entry point (the `fortress` command)
  entrypoint/       Handlers invoked by a compute (e.g. Aliyun FC): run_dataset / run_datasets
  resource/         Resource layer: identity / vault+asset / store / source(+dataset) / global singletons
  service/          Service layer: machine / node / mcphost / webhost
  setting/          Pydantic setting models (schema of system.yaml / services.yaml)
  internal/         Infrastructure (logging, utilities, data models, ...)
settings/           Setting files (system.yaml, services.yaml; gitignored)
local/              Runtime data: .auth keys, .logs, vault, store, provision (gitignored)
docs/               Design docs (auth / cluster / network / node)
```

## Setup

### 1. Environment

Requires Python 3.11 and conda.

```bash
make env       # create/update the conda env `app-fortress`
conda activate app-fortress
```

### 2. Install dependencies

```bash
pip install -e ".[dev]"
```

Optional extras:

| extra | contents |
|---|---|
| `aliyun` | OSS / FC / Aliyun credentials (needed for OSS vault/store) |
| `tushare` | Tushare data source |
| `rba` | RBA data source |
| `node` | Run the Node (duckdb, starlette, uvicorn, psutil) |
| `mcphost` | Run the MCP Host (includes `node`) |
| `webhost` | Run the Web Host (includes `node`) |
| `dev` | Development and testing (pytest, ruff, moto, ...; includes `tushare`) |

For example, to run every service: `pip install -e ".[aliyun,rba,mcphost,webhost]"`.

> `make install` installs a non-editable copy into both the conda env and the current shell's pip. For development, prefer the `pip install -e` above.

### 3. Configure

The setting directory defaults to `settings/` (override with `--setting-path`). `system.yaml` and `services.yaml` hold secrets and tokens and are gitignored, so you need to create them yourself.

**`settings/system.yaml`** (required): node info and resource definitions.

```yaml
alias: Fortress
node: snt                    # node name
version: 0.6.6
timezone: Australia/Sydney

log:
  name: system
  level: DEBUG
  file_path: "./local/.logs/system"

# Credentials (only needed for Aliyun OSS)
identities:
  - name: my_aliyun
    platform: aliyun
    type: ak
    access_key_id: <ACCESS_KEY_ID>
    access_key_secret: <ACCESS_KEY_SECRET>
    region: cn-shanghai

# Sources: each one carries its own vault (files), store (metadata) and log
sources:
  - name: snt_local_abs
    provider: abs            # abs / nswvg / rba / tushare
    timezone: Australia/Sydney
    vault:
      name: snt_local_abs
      filesystem: local      # local or oss
      path: ./local/vault/source/abs/
    store:
      name: snt_local_abs
      storesystem: file      # file or oss
      path: ./local/store/source/abs/
    log:
      name: snt_local_abs
      level: DEBUG
      file_path: "./local/.logs/source/abs"
```

Notes:

- `provider: tushare` requires `key` (the Tushare token).
- For OSS, use `filesystem: oss` / `storesystem: oss` and provide `identity`, `bucket`, `region`, `prefix`, `in_vpc`.
- The top level also accepts standalone `identities` / `stores` / `vaults` / `computes` that sources can reference by name.

**`settings/services.yaml`** (optional; needed for authentication or the hosts): one block per service: `machine` / `node` / `mcphost` / `webhost`.

```yaml
node:
  enabled: true
  host: 127.0.0.1
  port: 8800
  auth:
    masterfile: ../local/.auth/node.key   # relative to the settings directory
    tokens:
      - name: mcphost
        version: 1
        expires: 2027-10-22
        delegate: true
mcphost:
  enabled: true
  port: 8801
  auth: { masterfile: ../local/.auth/mcphost.key, tokens: [...] }
  nodes:
    - name: snt
      endpoint: http://127.0.0.1:8800
      token: <token issued by the node>
webhost:
  enabled: true
  port: 8803
  auth: { masterfile: ../local/.auth/webhost.key, tokens: [...] }
  nodes:
    - name: snt
      endpoint: http://127.0.0.1:8800
      token: <token issued by the node>
```

### 4. Initialise tokens

A token is derived by HMAC from the master key, the entry name and its version; the server stores nothing (see [docs/auth/auth(token).md](docs/auth/auth(token).md)).

```bash
fortress auth init --service node        # create local/.auth/node.key (never overwrites)
fortress auth init --service mcphost
fortress auth init --service webhost

fortress auth list --service node           # show token states
fortress auth show mcphost --service node   # print a token, put it into nodes[].token of mcphost/webhost
```

Rotate: bump the entry's `version`. Revoke: `revoked: true`. Invalidate everything: replace the master key file.

## Usage

### Start the services

```bash
make start                 # same as `fortress up`
```

`fortress up` starts the Node first, waits for its port, then starts the MCP Host, and the Web Host when `webhost.enabled` is true. If any process exits, all are stopped.

Or start them individually:

```bash
fortress node start    [--host H] [--port P] [--setting-path DIR]
fortress mcphost start [--node NAME] [--host H] [--port P] [--log-level info]
fortress webhost start [--host H] [--port P] [--log-level info]
```

### Node HTTP API

Everything except `GET /health` requires `Authorization: Bearer <token>`.

```bash
TOKEN=$(fortress auth show webhost --service node)

curl localhost:8800/health
curl -H "Authorization: Bearer $TOKEN" localhost:8800/internal/sources
curl -H "Authorization: Bearer $TOKEN" localhost:8800/internal/datasets?source=snt_local_abs

# Submit a dataset run (returns 202, then poll runs/{id})
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"params": {}}' \
  localhost:8800/internal/datasets/snt_local_abs/labour_force_month/runs

# Read-only SQL query
curl -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sql": "SELECT 1"}' localhost:8800/internal/query
```

Main routes:

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check (no token) |
| GET | `/internal/sources[/{source}[/logs]]` | Sources and their logs |
| GET | `/internal/datasets[?source=]` | List datasets |
| GET | `/internal/datasets/{source}/{dataset}` | Dataset detail |
| GET | `.../{dataset}/assetfiles｜metadatas｜qualities｜definitions` | Files, metadata, quality, definitions (`since`/`until` supported) |
| GET/POST | `.../{dataset}/runs`, `.../runs/{id}` | List / submit runs |
| GET | `/internal/machine/snapshots[?hours=]` | Machine snapshots |
| POST | `/internal/query` | SQL query |

### Run a dataset from code

Without the Node, call the handler in `entrypoint` directly (it is also the entry used when deployed to a compute such as FC):

```python
from app.entrypoint.run_dataset import handler

handler(
    {
        "source": "snt_local_abs",
        "dataset": "labour_force_month",
        "params": {},
    }
)
# -> {"ok": True, "results": [{"source": ..., "dataset": ..., "assetfiles": [...]}]}
```

For batches use `app.entrypoint.run_datasets` with payload `{"items": [{"source", "dataset", "params"}, ...]}`.

### Available sources and datasets

| provider | example datasets |
|---|---|
| `abs` | `labour_force_month`, `price_index_cpi_quarter`, `population_erp_quarter`, ... |
| `rba` | `g1_cpi_quarter`, `f6_lending_rates_housing_month`, ... (needs the `rba` extra) |
| `nswvg` | `psi_week`, `psi_year` |
| `tushare` | `tradedates`, `etf_list` (needs the `tushare` extra and a key) |

See `app/resource/source/<provider>/datasets/` for the full list.

## Development

```bash
pytest                 # runs all tests under app/
ruff format . && ruff check . --fix   # or `make lint`
make clean             # remove build artifacts and caches
```

- Unit tests live in each module's `tests/` directory, named `test_*_unit.py`.
- To add a dataset: add a class under `app/resource/source/<provider>/datasets/` that extends the provider's Dataset base and sets `name: ClassVar[str]`.

## Docs

- [docs/summary.md](docs/summary.md): project overview
- [docs/auth/](docs/auth/): tokens and access control
- [docs/cluster/architecture.md](docs/cluster/architecture.md): cluster architecture
- [docs/network/cloudflare.md](docs/network/cloudflare.md): Cloudflare tunnel
