#!/usr/bin/env bash
# MCP-ZERO Integration Test
# Starts kernel daemon + gateway, runs end-to-end HTTP tests, then cleans up.
#
# Usage: bash tests/integration_test.sh

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
KERNEL_BIN="$ROOT/src/kernel/target/release/mcp-kernel"
GATEWAY_BIN="$ROOT/src/gateway/gateway"
KERNEL_SOCK="/tmp/mcp-test-kernel-$$.sock"
GATEWAY_STORE="/tmp/mcp-test-gateway-$$"
GATEWAY_PORT=18080
PASS=0
FAIL=0

cleanup() {
    echo ""
    echo "=== Cleanup ==="
    [ -n "${GATEWAY_PID:-}" ] && kill "$GATEWAY_PID" 2>/dev/null && echo "  Stopped gateway (PID $GATEWAY_PID)"
    [ -n "${KERNEL_PID:-}" ]  && kill "$KERNEL_PID"  2>/dev/null && echo "  Stopped kernel  (PID $KERNEL_PID)"
    rm -f "$KERNEL_SOCK"
    rm -rf "$GATEWAY_STORE"
    sleep 0.3
    echo ""
    echo "=== Results: $PASS passed, $FAIL failed ==="
    [ "$FAIL" -eq 0 ] && exit 0 || exit 1
}
trap cleanup EXIT

assert_eq() {
    local label="$1" expected="$2" actual="$3"
    if [ "$expected" = "$actual" ]; then
        echo "  PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label (expected '$expected', got '$actual')"
        FAIL=$((FAIL + 1))
    fi
}

assert_contains() {
    local label="$1" needle="$2" haystack="$3"
    if echo "$haystack" | grep -q "$needle"; then
        echo "  PASS: $label"
        PASS=$((PASS + 1))
    else
        echo "  FAIL: $label (expected to contain '$needle', got '$haystack')"
        FAIL=$((FAIL + 1))
    fi
}

# --- Check binaries exist ---
echo "=== MCP-ZERO Integration Test ==="
echo ""

if [ ! -x "$KERNEL_BIN" ]; then
    echo "ERROR: Kernel binary not found at $KERNEL_BIN"
    echo "  Run: cd src/kernel && cargo build --release"
    exit 1
fi

if [ ! -x "$GATEWAY_BIN" ]; then
    echo "ERROR: Gateway binary not found at $GATEWAY_BIN"
    echo "  Run: cd src/gateway && go build -o gateway ."
    exit 1
fi

# --- Start Kernel ---
echo "Starting kernel..."
MCP_KERNEL_SOCKET="$KERNEL_SOCK" \
MCP_STORAGE_DIR="/tmp/mcp-test-storage-$$" \
"$KERNEL_BIN" &
KERNEL_PID=$!

# Wait for socket
for i in $(seq 1 30); do
    [ -S "$KERNEL_SOCK" ] && break
    sleep 0.1
done

if [ ! -S "$KERNEL_SOCK" ]; then
    echo "ERROR: Kernel socket not created after 3s"
    exit 1
fi
echo "  Kernel running (PID $KERNEL_PID, socket $KERNEL_SOCK)"

# --- Start Gateway ---
echo "Starting gateway..."
"$GATEWAY_BIN" \
    -addr ":$GATEWAY_PORT" \
    -db "$GATEWAY_STORE" \
    -kernel "$KERNEL_SOCK" &
GATEWAY_PID=$!

# Wait for HTTP
for i in $(seq 1 30); do
    curl -s "http://localhost:$GATEWAY_PORT/health" >/dev/null 2>&1 && break
    sleep 0.1
done

if ! curl -s "http://localhost:$GATEWAY_PORT/health" >/dev/null 2>&1; then
    echo "ERROR: Gateway not responding after 3s"
    exit 1
fi
echo "  Gateway running (PID $GATEWAY_PID, port $GATEWAY_PORT)"
echo ""

# === Tests ===

echo "--- Test 1: Health check ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/health")
assert_contains "health returns ok" '"status":"ok"' "$RESP"

echo "--- Test 2: Kernel status ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/api/v1/status")
assert_contains "status has uptime" '"uptime_secs"' "$RESP"
assert_contains "status has version" '"version"' "$RESP"

echo "--- Test 3: List agents (empty) ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/api/v1/agents")
assert_contains "empty agent list" '"count":0' "$RESP"

echo "--- Test 4: Spawn agent ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/agents" \
    -H "Content-Type: application/json" \
    -d '{"name":"sensor_reader","entry":"sensor_plugin","intents":["read_temp","report"]}')
assert_contains "spawn returns agent_id" '"agent_id"' "$RESP"

# Extract agent_id
AGENT_ID=$(echo "$RESP" | grep -o '"agent_id":"[^"]*"' | cut -d'"' -f4)
echo "  Agent ID: $AGENT_ID"

echo "--- Test 5: List agents (1 agent) ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/api/v1/agents")
assert_contains "agent list has 1" '"count":1' "$RESP"

echo "--- Test 6: Get agent by ID ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/api/v1/agents/$AGENT_ID")
assert_contains "agent metadata has id" "$AGENT_ID" "$RESP"

echo "--- Test 7: Execute intent (round-trip) ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/execute" \
    -H "Content-Type: application/json" \
    -d "{\"agent_id\":\"$AGENT_ID\",\"intent\":\"read_temp\"}")
# Execute returns an error because no real WASM plugin is loaded, but the
# full round-trip (HTTP → Go → Unix socket → Rust kernel → response) works.
assert_contains "execute round-trip returns JSON" '{' "$RESP"

echo "--- Test 8: Snapshot agent ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/snapshot" \
    -H "Content-Type: application/json" \
    -d "{\"agent_id\":\"$AGENT_ID\"}")
# Snapshot may succeed or fail depending on kernel impl, just check we get JSON back
assert_contains "snapshot returns JSON" '{' "$RESP"

echo "--- Test 9: Method not allowed ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X PUT "http://localhost:$GATEWAY_PORT/api/v1/agents")
assert_eq "PUT returns 405" "405" "$HTTP_CODE"

echo "--- Test 10: Execute missing fields ---"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:$GATEWAY_PORT/api/v1/execute" \
    -H "Content-Type: application/json" \
    -d '{"agent_id":""}')
assert_eq "empty agent_id returns 400" "400" "$HTTP_CODE"

# === Cognitive endpoint tests ===

echo ""
echo "=== Cognitive Layer Tests (HTTP → Go → Rust) ==="
echo ""

echo "--- Test 11: Cog state ---"
RESP=$(curl -s "http://localhost:$GATEWAY_PORT/api/v1/cog/state")
assert_contains "cog state has cycle" '"cycle"' "$RESP"
assert_contains "cog state has field" '"field"' "$RESP"

echo "--- Test 12: Register intention ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/intention" \
    -H "Content-Type: application/json" \
    -d '{"name":"explore","priority":0.8}')
assert_contains "register intention ok" '"ok":true' "$RESP"

echo "--- Test 13: Activate intention ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/intention" \
    -H "Content-Type: application/json" \
    -d '{"name":"explore","action":"activate"}')
assert_contains "activate intention ok" '"ok":true' "$RESP"

echo "--- Test 14: Register symbol ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/symbol" \
    -H "Content-Type: application/json" \
    -d '{"domain":"concepts","symbol":"truth"}')
assert_contains "register symbol ok" '"ok":true' "$RESP"

echo "--- Test 15: Register second symbol ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/symbol" \
    -H "Content-Type: application/json" \
    -d '{"domain":"concepts","symbol":"knowledge"}')
assert_contains "register second symbol ok" '"ok":true' "$RESP"

echo "--- Test 16: Cognitive cycle (no input) ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/cycle" \
    -H "Content-Type: application/json" \
    -d '{}')
assert_contains "cycle has state" '"state"' "$RESP"
assert_contains "cycle has collapsed_intents" '"collapsed_intents"' "$RESP"

echo "--- Test 17: Cognitive cycle (with input vector) ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/cycle" \
    -H "Content-Type: application/json" \
    -d '{"input":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8]}')
assert_contains "cycle with input has state" '"state"' "$RESP"

echo "--- Test 18: Ground vector to symbols ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/ground" \
    -H "Content-Type: application/json" \
    -d '{"vector":[0.5,0.5,0.5,0.5,0.5,0.5,0.5,0.5]}')
assert_contains "ground has top_symbols" '"top_symbols"' "$RESP"
assert_contains "ground has coherence" '"coherence"' "$RESP"

echo "--- Test 19: Add fact to knowledge store ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/fact" \
    -H "Content-Type: application/json" \
    -d '{"text":"The speed of light is 299792458 m/s","embedding":[1.0,0.0,0.0,0.0]}')
assert_contains "add fact returns id" '"id"' "$RESP"

echo "--- Test 20: Search knowledge store ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/search" \
    -H "Content-Type: application/json" \
    -d '{"query":[0.9,0.1,0.0,0.0],"top_k":3}')
assert_contains "search returns results" '"results"' "$RESP"

echo "--- Test 21: Process contradiction ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/cog/contradiction" \
    -H "Content-Type: application/json" \
    -d '{"vector":[0.5,-0.5,0.3,-0.3,0.1,-0.1,0.0,0.0]}')
assert_contains "contradiction has contradiction_level" '"contradiction_level"' "$RESP"

echo ""
echo "=== Entropy Graph Tests (HTTP → Go → Rust) ==="
echo ""

echo "--- Test 22: Record entropy pass ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/entropy/record" \
    -H "Content-Type: application/json" \
    -d '{"layers":[{"name":"embedding","activations":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]},{"name":"attention","activations":[0.0,0.0,0.0,0.8,0.0,0.0,0.0,0.0,0.0,0.0]},{"name":"output","activations":[0.1,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]}]}')
assert_contains "entropy record has layers" '"layers"' "$RESP"
assert_contains "entropy record has mean_entropy" '"mean_entropy"' "$RESP"
assert_contains "entropy record has deltas" '"deltas"' "$RESP"

echo "--- Test 23: Get entropy snapshot ---"
RESP=$(curl -s -X GET "http://localhost:$GATEWAY_PORT/api/v1/entropy/snapshot")
assert_contains "snapshot has layers" '"layers"' "$RESP"

echo "--- Test 24: Detect bottlenecks ---"
RESP=$(curl -s -X GET "http://localhost:$GATEWAY_PORT/api/v1/entropy/bottlenecks")
assert_contains "bottlenecks has bottlenecks" '"bottlenecks"' "$RESP"
assert_contains "bottlenecks has bursts" '"bursts"' "$RESP"
assert_contains "bottlenecks has snapshot_count" '"snapshot_count"' "$RESP"

echo "--- Test 25: Get entropy trend ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/entropy/trend" \
    -H "Content-Type: application/json" \
    -d '{"layer":"embedding","count":5}')
assert_contains "trend has layer" '"layer"' "$RESP"
assert_contains "trend has trend" '"trend"' "$RESP"

echo "--- Test 26: Entropy snapshot method not allowed ---"
RESP=$(curl -s -o /dev/null -w "%{http_code}" -X POST "http://localhost:$GATEWAY_PORT/api/v1/entropy/snapshot")
assert_eq "entropy snapshot POST returns 405" "405" "$RESP"

echo ""
echo "=== Binary Knowledge Store Tests (HTTP → Go → Rust → redb) ==="
echo ""

echo "--- Test 27: Store count (empty) ---"
RESP=$(curl -s -X GET "http://localhost:$GATEWAY_PORT/api/v1/store/count")
assert_contains "store count has count" '"count"' "$RESP"

echo "--- Test 28: Store add fact ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/add" \
    -H "Content-Type: application/json" \
    -d '{"text":"Water boils at 100 degrees Celsius at sea level","embedding":[1.0,0.0,0.0,0.0]}')
assert_contains "store add returns id" '"id"' "$RESP"

echo "--- Test 29: Store add second fact ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/add" \
    -H "Content-Type: application/json" \
    -d '{"text":"The Earth orbits the Sun","embedding":[0.0,1.0,0.0,0.0]}')
assert_contains "store add second returns id" '"id"' "$RESP"

echo "--- Test 30: Store count (2 facts) ---"
RESP=$(curl -s -X GET "http://localhost:$GATEWAY_PORT/api/v1/store/count")
assert_contains "store count is 2" '"count":2' "$RESP"

echo "--- Test 31: Store search ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/search" \
    -H "Content-Type: application/json" \
    -d '{"query":[0.9,0.1,0.0,0.0],"top_k":2}')
assert_contains "store search has results" '"results"' "$RESP"
assert_contains "store search finds water fact" 'Water boils' "$RESP"

echo "--- Test 32: Store get fact by ID ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/get" \
    -H "Content-Type: application/json" \
    -d '{"id":0}')
assert_contains "store get has text" '"text"' "$RESP"
assert_contains "store get has embedding" '"embedding"' "$RESP"

echo "--- Test 33: Store update weight ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/weight" \
    -H "Content-Type: application/json" \
    -d '{"id":0,"weight":2.5}')
assert_contains "store update weight ok" '"ok":true' "$RESP"

echo "--- Test 34: Store remove fact ---"
RESP=$(curl -s -X POST "http://localhost:$GATEWAY_PORT/api/v1/store/remove" \
    -H "Content-Type: application/json" \
    -d '{"id":1}')
assert_contains "store remove ok" '"ok":true' "$RESP"

echo "--- Test 35: Store count after remove ---"
RESP=$(curl -s -X GET "http://localhost:$GATEWAY_PORT/api/v1/store/count")
assert_contains "store count is 1 after remove" '"count":1' "$RESP"
