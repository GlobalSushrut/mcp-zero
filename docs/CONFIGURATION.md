# MCP-ZERO Configuration Reference

All configuration is via environment variables. No config files required.

---

## Rust Kernel Configuration

| Variable | Default | Type | Description |
|---|---|---|---|
| `MCP_KERNEL_SOCKET` | `/tmp/mcp-kernel.sock` | path | Unix domain socket path for JSON-RPC |
| `MCP_STORAGE_DIR` | `/tmp/mcp-kernel-data` | path | Directory for agent persistence and data |
| `MCP_COG_DIM` | `64` | int | Cognitive vector dimension (CogVec size) |
| `MCP_EMBED_DIM` | `384` | int | Neural embedding dimension |
| `MCP_BINARY_STORE` | `{MCP_STORAGE_DIR}/knowledge.redb` | path | Binary knowledge store (redb) path |
| `MCP_KNOWLEDGE_FILE` | *(empty)* | path | JSON knowledge file for CogLoop bootstrap |
| `MCP_LLM_URL` | *(empty)* | URL | LLM API base URL. Empty = offline mode (hash embeddings) |
| `MCP_LLM_MODEL` | `llama3.1:8b` | string | LLM model name for API calls |
| `RUST_LOG` | `info` | string | Log level: `error`, `warn`, `info`, `debug`, `trace` |

### Cognitive Dimensions

| `MCP_COG_DIM` | Use Case |
|---|---|
| `32` | Minimal edge device, fastest inference |
| `64` | Default — good balance of quality and speed |
| `128` | Higher fidelity reasoning, more memory |

| `MCP_EMBED_DIM` | Use Case |
|---|---|
| `128` | Lightweight, fast hash embeddings |
| `384` | Default — matches sentence-transformers |
| `768` | High-quality, matches BERT-base |

### LLM Integration Modes

| `MCP_LLM_URL` | Mode | Behavior |
|---|---|---|
| *(empty)* | Offline | Deterministic hash-based embeddings, no external calls |
| `http://localhost:11434` | Ollama | Local LLM via Ollama API |
| `http://localhost:8000` | vLLM | Local LLM via vLLM OpenAI-compatible API |
| `https://api.openai.com` | OpenAI | Cloud LLM (requires API key in headers) |

---

## Go Gateway Configuration

| Variable | Default | Type | Description |
|---|---|---|---|
| `MCP_API_KEY` | *(empty)* | string | Bearer token for API auth. Empty = auth disabled |
| `MCP_RATE_LIMIT` | `100` | int | Max requests per minute per IP. `0` = disabled |

### Command-Line Flags

The gateway binary accepts these flags:

| Flag | Default | Description |
|---|---|---|
| `-addr` | `:8080` | HTTP listen address |
| `-db` | `/tmp/mcp-gateway-data` | File-backed KV store directory |
| `-kernel` | `/tmp/mcp-kernel.sock` | Kernel Unix socket path |

### Authentication

When `MCP_API_KEY` is set, all API requests (except `/health` and `/metrics`) must include:

```
Authorization: Bearer <MCP_API_KEY>
```

Unauthenticated requests receive `401 Unauthorized`.

### Rate Limiting

Token bucket algorithm: each IP gets `MCP_RATE_LIMIT` tokens per minute. When exhausted, requests receive `429 Too Many Requests` with `Retry-After: 60` header.

### Request Size Limit

All request bodies are limited to **1 MB** via `http.MaxBytesReader`. Oversized requests receive `413 Request Entity Too Large`.

---

## systemd Service Configuration

Service files are installed to `/etc/systemd/system/`.

### Override Configuration

```bash
# Override kernel settings
sudo systemctl edit mcpzero-kernel
```

Add environment overrides:

```ini
[Service]
Environment=MCP_COG_DIM=128
Environment=MCP_LLM_URL=http://localhost:11434
Environment=RUST_LOG=debug
```

```bash
# Override gateway settings
sudo systemctl edit mcpzero-gateway
```

```ini
[Service]
Environment=MCP_API_KEY=my-secret-key-here
Environment=MCP_RATE_LIMIT=200
```

Apply changes:

```bash
sudo systemctl daemon-reload
sudo systemctl restart mcpzero-gateway
```

### Security Hardening (Default)

Both services run with:
- `NoNewPrivileges=true` — prevents privilege escalation
- `ProtectSystem=strict` — read-only filesystem except allowed paths
- `ProtectHome=true` — no access to /home
- `PrivateTmp=true` — isolated /tmp
- Dedicated `mcpzero` system user (no login shell)

---

## Development Configuration

For local development, use environment variables directly:

```bash
# Minimal dev setup
export MCP_KERNEL_SOCKET=/tmp/mcp-kernel.sock
export MCP_STORAGE_DIR=/tmp/mcp-kernel-data
export RUST_LOG=debug

# Start kernel
cd src/kernel && cargo run --release

# In another terminal, start gateway
cd src/gateway && go run . -addr :8080 -kernel /tmp/mcp-kernel.sock

# Or use the start script
make start
```

### Debug Logging

```bash
# Rust kernel: full debug output
RUST_LOG=debug cargo run --release

# Rust kernel: module-specific
RUST_LOG=mcp_kernel::cognitive=trace,info cargo run --release
```
