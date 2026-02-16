# MCP-ZERO Troubleshooting Guide

## 1. Kernel Won't Start

**Symptom:** `mcp-kernel` exits immediately or socket doesn't appear.

**Check:**
```bash
# Check if socket already exists (stale)
ls -la /tmp/mcp-kernel.sock
rm -f /tmp/mcp-kernel.sock

# Check storage directory exists
mkdir -p /tmp/mcp-kernel-data

# Run with debug logging
RUST_LOG=debug /opt/mcpzero/bin/mcp-kernel
```

**Common causes:**
- Stale socket file from previous crash → delete it
- Storage directory doesn't exist → create it
- Port/socket permission denied → check user owns the path

---

## 2. Gateway Can't Connect to Kernel

**Symptom:** All API calls return `502 Bad Gateway` with "connect to kernel" error.

**Check:**
```bash
# Verify kernel is running
systemctl status mcpzero-kernel

# Verify socket exists
ls -la /tmp/mcp-kernel.sock

# Test socket directly
echo '{"jsonrpc":"2.0","method":"kernel.status","params":null,"id":1}' | socat - UNIX-CONNECT:/tmp/mcp-kernel.sock
```

**Fix:** Start kernel first, then gateway. The gateway's systemd unit has `Requires=mcpzero-kernel.service`.

---

## 3. Authentication Errors (401)

**Symptom:** API calls return `{"error": "missing Authorization header"}`.

**Check:**
```bash
# See if auth is enabled
grep MCP_API_KEY /etc/systemd/system/mcpzero-gateway.service

# Test with auth
curl -H "Authorization: Bearer YOUR_KEY" http://localhost:8080/api/v1/status
```

**Fix:** Either set the correct `Authorization: Bearer <key>` header, or unset `MCP_API_KEY` to disable auth.

---

## 4. Rate Limit Exceeded (429)

**Symptom:** `{"error": "rate limit exceeded"}` with `Retry-After: 60` header.

**Fix:** Wait 60 seconds for token bucket to refill, or increase `MCP_RATE_LIMIT`:
```bash
sudo systemctl edit mcpzero-gateway
# Add: Environment=MCP_RATE_LIMIT=500
sudo systemctl restart mcpzero-gateway
```

---

## 5. High Memory Usage

**Symptom:** Kernel RSS grows over time.

**Check:**
```bash
# Check process memory
ps aux | grep mcp
curl http://localhost:8080/metrics
```

**Likely causes:**
- Knowledge store growing → check `store.count` via `/api/v1/store/count`
- Knot graph growing → check `/api/v1/knot/stats`
- Entropy graph history → limited to 1000 snapshots by default

**Fix:** The binary store uses redb (memory-mapped), so RSS includes mapped pages. This is normal — the OS will reclaim pages under memory pressure.

---

## 6. LLM Bridge Returns Hash Embeddings

**Symptom:** `llm.embed` returns `"source": "HashFallback"` instead of real embeddings.

**Check:**
```bash
# Verify LLM URL is set
echo $MCP_LLM_URL

# Test LLM directly
curl http://localhost:11434/api/embeddings -d '{"model":"llama3.1:8b","prompt":"test"}'
```

**Fix:** Set `MCP_LLM_URL` to your LLM endpoint:
```bash
export MCP_LLM_URL=http://localhost:11434
```

Hash fallback is deterministic and functional — it just won't have semantic quality.

---

## 7. Cognitive Fabric Returns Empty Results

**Symptom:** `fabric.think` returns but with no meaningful grounding.

**Fix:** The fabric needs knowledge to reason about. Teach it first:
```bash
# Add knowledge
curl -X POST http://localhost:8080/api/v1/fabric/learn \
  -H "Content-Type: application/json" \
  -d '{"text": "Zone 5 needs irrigation when moisture drops below 20%"}'

# Now think
curl -X POST http://localhost:8080/api/v1/fabric/think \
  -H "Content-Type: application/json" \
  -d '{"text": "Zone 5 moisture is 15%"}'
```

---

## 8. Binary Store Errors

**Symptom:** `store.add` returns error about redb.

**Check:**
```bash
ls -la /tmp/mcp-kernel-data/knowledge.redb
```

**Common causes:**
- Disk full → free space
- File locked by another process → only one kernel should access the store
- Corrupted file → delete and restart (data loss)

**Fix for corruption:**
```bash
rm /tmp/mcp-kernel-data/knowledge.redb
systemctl restart mcpzero-kernel
```

---

## 9. Tests Failing After Update

**Check:**
```bash
# Run all Rust tests
cd src/kernel && cargo test 2>&1 | tail -5

# Run Go tests
cd src/gateway && go test ./...

# Check for compilation warnings
cd src/kernel && cargo build --release 2>&1 | grep warning
```

**Expected:** 225 Rust tests pass, 10 Go tests pass, 0 warnings.

---

## 10. systemd Service Won't Start

**Check:**
```bash
# View service logs
journalctl -u mcpzero-kernel -n 50 --no-pager
journalctl -u mcpzero-gateway -n 50 --no-pager

# Check service file syntax
systemd-analyze verify /etc/systemd/system/mcpzero-kernel.service
```

**Common causes:**
- Binary not found at `/opt/mcpzero/bin/` → run `sudo make install`
- `mcpzero` user doesn't exist → run install.sh
- Directory permissions → `chown -R mcpzero:mcpzero /var/lib/mcpzero`

---

## Diagnostic Commands

```bash
# Full system check
curl -s http://localhost:8080/health | jq .
curl -s http://localhost:8080/metrics | jq .
curl -s http://localhost:8080/api/v1/fabric/status | jq .
curl -s http://localhost:8080/api/v1/knot/stats | jq .
curl -s http://localhost:8080/api/v1/llm/status | jq .
curl -s http://localhost:8080/api/v1/store/count | jq .

# Process info
ps aux | grep -E "(mcp-kernel|gateway)"
ls -la /tmp/mcp-kernel.sock

# Binary sizes
ls -lh /opt/mcpzero/bin/
```
