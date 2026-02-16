#!/bin/bash
# MCP-ZERO Start Script
# Starts the Rust kernel and Go gateway as a unified system.
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

# Configuration (override via environment)
export MCP_KERNEL_SOCKET="${MCP_KERNEL_SOCKET:-/tmp/mcp-kernel.sock}"
export MCP_STORAGE_DIR="${MCP_STORAGE_DIR:-/tmp/mcp-kernel-data}"
export MCP_COG_DIM="${MCP_COG_DIM:-64}"
export MCP_EMBED_DIM="${MCP_EMBED_DIM:-384}"
GATEWAY_ADDR="${GATEWAY_ADDR:-:8080}"
GATEWAY_DB="${GATEWAY_DB:-/tmp/mcp-gateway-data}"

KERNEL_BIN="$ROOT_DIR/src/kernel/target/release/mcp-kernel"
GATEWAY_BIN="$ROOT_DIR/src/gateway/gateway"

# Check binaries exist
if [ ! -f "$KERNEL_BIN" ]; then
    echo "ERROR: Kernel binary not found at $KERNEL_BIN"
    echo "Run: make build-kernel"
    exit 1
fi
if [ ! -f "$GATEWAY_BIN" ]; then
    echo "ERROR: Gateway binary not found at $GATEWAY_BIN"
    echo "Run: make build-gateway"
    exit 1
fi

# Create data directories
mkdir -p "$MCP_STORAGE_DIR" "$GATEWAY_DB"

# Cleanup function
cleanup() {
    echo "Shutting down MCP-ZERO..."
    [ -n "$KERNEL_PID" ] && kill "$KERNEL_PID" 2>/dev/null && wait "$KERNEL_PID" 2>/dev/null
    [ -n "$GATEWAY_PID" ] && kill "$GATEWAY_PID" 2>/dev/null && wait "$GATEWAY_PID" 2>/dev/null
    rm -f "$MCP_KERNEL_SOCKET"
    echo "MCP-ZERO stopped."
}
trap cleanup EXIT INT TERM

# Start Rust kernel (background)
echo "Starting Rust kernel..."
"$KERNEL_BIN" &
KERNEL_PID=$!

# Wait for kernel socket to appear (max 10s)
for i in $(seq 1 100); do
    [ -S "$MCP_KERNEL_SOCKET" ] && break
    sleep 0.1
done
if [ ! -S "$MCP_KERNEL_SOCKET" ]; then
    echo "ERROR: Kernel socket did not appear after 10s"
    exit 1
fi
echo "Kernel ready (PID $KERNEL_PID, socket $MCP_KERNEL_SOCKET)"

# Start Go gateway (foreground)
echo "Starting Go gateway on $GATEWAY_ADDR..."
"$GATEWAY_BIN" -addr "$GATEWAY_ADDR" -db "$GATEWAY_DB" -kernel "$MCP_KERNEL_SOCKET" &
GATEWAY_PID=$!

echo "============================================"
echo "  MCP-ZERO is running"
echo "  Gateway: http://localhost${GATEWAY_ADDR}"
echo "  Health:  http://localhost${GATEWAY_ADDR}/health"
echo "  Metrics: http://localhost${GATEWAY_ADDR}/metrics"
echo "  Kernel:  $MCP_KERNEL_SOCKET"
echo "============================================"

# Wait for either process to exit
wait -n "$KERNEL_PID" "$GATEWAY_PID" 2>/dev/null || true
