# MCP-ZERO Installation Guide

## Prerequisites

| Tool | Version | Check |
|---|---|---|
| Rust | 1.75+ | `rustc --version` |
| Go | 1.22+ | `go version` |
| Make | any | `make --version` |
| Linux | kernel 5.x+ | `uname -r` |

## Quick Start (Development)

```bash
# Clone
git clone https://github.com/GlobalSushrut/mcp-zero.git
cd mcp-zero

# Build everything
make all

# Run tests
make test

# Start system (dev mode)
make start
```

The system will be available at `http://localhost:8080`.

## Build from Source

### Build Rust Kernel

```bash
make build-kernel
# Output: src/kernel/target/release/mcp-kernel (~21MB)
```

### Build Go Gateway

```bash
make build-gateway
# Output: src/gateway/gateway (~7.8MB)
```

### Build Release (Optimized + Stripped)

```bash
make release
```

## Production Installation (Linux)

### Automated Install

```bash
# Build release binaries first
make release

# Install to /opt/mcpzero (requires root)
sudo bash scripts/install.sh
```

This will:
1. Create `mcpzero` system user
2. Install binaries to `/opt/mcpzero/bin/`
3. Create data directories at `/var/lib/mcpzero/`
4. Install systemd service files

### Start Services

```bash
# Start kernel + gateway
sudo systemctl start mcpzero-gateway

# Enable on boot
sudo systemctl enable mcpzero-gateway

# Check status
sudo systemctl status mcpzero-kernel mcpzero-gateway
```

### Verify Installation

```bash
# Health check
curl http://localhost:8080/health

# System metrics
curl http://localhost:8080/metrics

# Test cognitive fabric
curl -X POST http://localhost:8080/api/v1/fabric/think \
  -H "Content-Type: application/json" \
  -d '{"text": "test input"}'
```

## Configuration

All configuration is via environment variables. Edit the systemd service files to change:

```bash
sudo systemctl edit mcpzero-kernel
sudo systemctl edit mcpzero-gateway
```

Key variables:

| Variable | Default | Description |
|---|---|---|
| `MCP_KERNEL_SOCKET` | `/tmp/mcp-kernel.sock` | Kernel Unix socket path |
| `MCP_STORAGE_DIR` | `/tmp/mcp-kernel-data` | Data directory |
| `MCP_COG_DIM` | `64` | Cognitive vector dimension |
| `MCP_EMBED_DIM` | `384` | Embedding dimension |
| `MCP_API_KEY` | *(empty)* | API key for auth (empty = disabled) |
| `MCP_RATE_LIMIT` | `100` | Requests/min/IP (0 = disabled) |
| `MCP_LLM_URL` | *(empty)* | LLM API URL (empty = offline mode) |
| `MCP_LLM_MODEL` | `llama3.1:8b` | LLM model name |

See [docs/CONFIGURATION.md](CONFIGURATION.md) for full reference.

## Raspberry Pi 4 Deployment

### Requirements
- Raspberry Pi 4 (4GB+ RAM recommended)
- Raspberry Pi OS (64-bit) or Ubuntu 22.04 ARM64
- 1GB free disk space

### Cross-Compile (from x86 host)

```bash
# Rust kernel for ARM64
cd src/kernel
rustup target add aarch64-unknown-linux-gnu
cargo build --release --target aarch64-unknown-linux-gnu

# Go gateway for ARM64
cd src/gateway
GOOS=linux GOARCH=arm64 go build -ldflags="-s -w" -o gateway .
```

### Deploy to Pi

```bash
# Copy binaries
scp src/kernel/target/aarch64-unknown-linux-gnu/release/mcp-kernel pi@raspberrypi:/tmp/
scp src/gateway/gateway pi@raspberrypi:/tmp/
scp -r scripts/ pi@raspberrypi:/tmp/

# On the Pi
ssh pi@raspberrypi
sudo bash /tmp/scripts/install.sh
sudo systemctl start mcpzero-gateway
```

### Expected Resource Usage

| Component | RAM | Binary Size |
|---|---|---|
| Rust Kernel | ~16MB | 21MB |
| Go Gateway | ~13MB | 7.8MB |
| **Total** | **~29MB** | **28.8MB** |

## LLM Integration (Optional)

To connect MCP-ZERO to a local LLM (e.g., Ollama):

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.1:8b

# Configure kernel
export MCP_LLM_URL=http://localhost:11434
export MCP_LLM_MODEL=llama3.1:8b

# Or edit systemd service
sudo systemctl edit mcpzero-kernel
# Add: Environment=MCP_LLM_URL=http://localhost:11434
```

## Logs

```bash
# View kernel logs
journalctl -u mcpzero-kernel -f

# View gateway logs
journalctl -u mcpzero-gateway -f

# Both
journalctl -u mcpzero-kernel -u mcpzero-gateway -f
```

## Uninstall

```bash
sudo systemctl stop mcpzero-gateway mcpzero-kernel
sudo systemctl disable mcpzero-gateway mcpzero-kernel
sudo rm /etc/systemd/system/mcpzero-*.service
sudo rm -rf /opt/mcpzero /var/lib/mcpzero
sudo userdel mcpzero
sudo systemctl daemon-reload
```
