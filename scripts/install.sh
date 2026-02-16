#!/bin/bash
# MCP-ZERO Installation Script
# Installs MCP-ZERO on a Linux system (x86_64 or ARM64).
set -e

INSTALL_DIR="/opt/mcpzero"
BIN_DIR="$INSTALL_DIR/bin"
CONF_DIR="$INSTALL_DIR/config"
DATA_DIR="/var/lib/mcpzero"
RUN_DIR="/run/mcpzero"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== MCP-ZERO Installer ==="

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: Must run as root (sudo ./install.sh)"
    exit 1
fi

# Create mcpzero user if not exists
if ! id -u mcpzero >/dev/null 2>&1; then
    echo "Creating mcpzero user..."
    useradd --system --no-create-home --shell /usr/sbin/nologin mcpzero
fi

# Create directories
echo "Creating directories..."
mkdir -p "$BIN_DIR" "$CONF_DIR" "$DATA_DIR/kernel" "$DATA_DIR/gateway" "$RUN_DIR"
chown -R mcpzero:mcpzero "$DATA_DIR" "$RUN_DIR"

# Copy binaries
echo "Installing binaries..."
KERNEL_BIN="$ROOT_DIR/src/kernel/target/release/mcp-kernel"
GATEWAY_BIN="$ROOT_DIR/src/gateway/gateway"

if [ -f "$KERNEL_BIN" ]; then
    cp "$KERNEL_BIN" "$BIN_DIR/mcp-kernel"
    chmod 755 "$BIN_DIR/mcp-kernel"
    echo "  Kernel: $(ls -lh "$BIN_DIR/mcp-kernel" | awk '{print $5}')"
else
    echo "  WARNING: Kernel binary not found. Run 'make build-kernel' first."
fi

if [ -f "$GATEWAY_BIN" ]; then
    cp "$GATEWAY_BIN" "$BIN_DIR/gateway"
    chmod 755 "$BIN_DIR/gateway"
    echo "  Gateway: $(ls -lh "$BIN_DIR/gateway" | awk '{print $5}')"
else
    echo "  WARNING: Gateway binary not found. Run 'make build-gateway' first."
fi

# Install systemd services
echo "Installing systemd services..."
cp "$SCRIPT_DIR/mcpzero-kernel.service" /etc/systemd/system/
cp "$SCRIPT_DIR/mcpzero-gateway.service" /etc/systemd/system/
systemctl daemon-reload

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Usage:"
echo "  sudo systemctl start mcpzero-kernel    # Start kernel"
echo "  sudo systemctl start mcpzero-gateway   # Start gateway (auto-starts kernel)"
echo "  sudo systemctl enable mcpzero-gateway  # Enable on boot"
echo ""
echo "  curl http://localhost:8080/health       # Health check"
echo "  curl http://localhost:8080/metrics      # System metrics"
echo ""
echo "Configuration:"
echo "  API key:    Set MCP_API_KEY in /etc/systemd/system/mcpzero-gateway.service"
echo "  Rate limit: Set MCP_RATE_LIMIT (default 100 req/min)"
echo "  LLM:        Set MCP_LLM_URL in /etc/systemd/system/mcpzero-kernel.service"
echo ""
echo "Binaries: $BIN_DIR"
echo "Data:     $DATA_DIR"
echo "Logs:     journalctl -u mcpzero-kernel -u mcpzero-gateway"
