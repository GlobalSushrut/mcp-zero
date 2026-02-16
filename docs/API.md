# MCP-ZERO API Reference

> Complete HTTP API reference for the MCP-ZERO Go Gateway.  
> Base URL: `http://localhost:8080`

---

## Authentication

Set `MCP_API_KEY` environment variable to enable Bearer token auth.

```
Authorization: Bearer <your-api-key>
```

Exempt endpoints: `/health`, `/metrics`

If `MCP_API_KEY` is not set, authentication is disabled.

---

## Rate Limiting

Default: **100 requests/minute per IP** (configurable via `MCP_RATE_LIMIT`).

- Set `MCP_RATE_LIMIT=0` to disable
- Returns `429 Too Many Requests` with `Retry-After: 60` header when exceeded

---

## Request Size Limit

Maximum request body: **1 MB**. Returns `413` if exceeded.

---

## System Endpoints

### GET /health

Health check. Always returns 200.

**Response:**
```json
{"status": "ok", "service": "mcp-zero-gateway"}
```

### GET /api/v1/status

Kernel status including uptime.

**Response:**
```json
{"uptime_secs": 3600, "version": "0.1.0"}
```

### GET /metrics

Aggregated metrics from all subsystems.

**Response:**
```json
{
  "service": "mcp-zero",
  "version": "0.1.0",
  "kernel": {"uptime_secs": 3600, "version": "0.1.0"},
  "fabric": {"think_cycles": 42, "cog_cycles": 42, "inference_count": 100, ...},
  "knot_graph": {"total_nodes": 15, "total_edges": 8, "components": 3},
  "llm_bridge": {"mode": "offline", "embed_count": 50, "distill_count": 5},
  "binary_store": {"count": 120}
}
```

---

## Agent Endpoints

### POST /api/v1/agents

Spawn a new agent.

**Request:**
```json
{"name": "sensor-agent", "capabilities": ["read", "write"]}
```

**Response (201):**
```json
{"agent_id": "a1b2c3d4"}
```

### GET /api/v1/agents

List all agents.

**Response:**
```json
{"agents": ["a1b2c3d4", "e5f6g7h8"], "count": 2}
```

### GET /api/v1/agents/{id}

Get agent metadata.

### DELETE /api/v1/agents/{id}

Delete an agent.

### POST /api/v1/execute

Execute an intent on an agent.

**Request:**
```json
{"agent_id": "a1b2c3d4", "intent": "read_sensor zone=5"}
```

**Response:**
```json
{"result": "..."}
```

### POST /api/v1/snapshot

Persist agent state.

**Request:** `{"agent_id": "a1b2c3d4"}`

### POST /api/v1/recover

Restore agent from storage.

**Request:** `{"agent_id": "a1b2c3d4"}`

---

## Cognitive Endpoints (CogLoop)

### GET /api/v1/cog/state

Current cognitive state (field, contradiction level, symbols, intentions).

### POST /api/v1/cog/cycle

Run one cognitive cycle.

**Request:**
```json
{"input": [0.1, 0.2, 0.3, ...]}
```

**Response:** CycleResult with field state, emerged symbols, entropy.

### POST /api/v1/cog/intention

Register or activate a cognitive intention.

**Request:**
```json
{"name": "explore", "priority": 0.8, "action": "register"}
```

`action`: `"register"` (default) or `"activate"`

### POST /api/v1/cog/contradiction

Process a contradiction vector.

**Request:** `{"vector": [0.1, -0.3, ...]}`

### POST /api/v1/cog/fact

Add a fact to the knowledge store.

**Request:**
```json
{"text": "Zone 5 needs irrigation when moisture < 20", "embedding": [0.1, 0.2, ...]}
```

**Response (201):** `{"id": 1}`

### POST /api/v1/cog/search

Search knowledge store by vector similarity.

**Request:** `{"query": [0.1, 0.2, ...], "top_k": 5}`

### POST /api/v1/cog/symbol

Register a symbol in a domain.

**Request:** `{"domain": "agriculture", "symbol": "drought", "vector": [...]}`

### POST /api/v1/cog/ground

Ground a neural vector to symbolic representations.

**Request:** `{"vector": [0.1, 0.2, ...]}`

**Response:**
```json
{"top_symbols": [["drought", 0.92]], "coherence": 0.85, "emerged": false}
```

---

## Entropy Graph Endpoints

### POST /api/v1/entropy/record

Record a forward pass of layer activations.

**Request:**
```json
{"layers": [{"name": "embed", "activations": [0.1, 0.5, ...]}, {"name": "attn", "activations": [...]}]}
```

### GET /api/v1/entropy/snapshot

Latest entropy snapshot across all layers.

### GET|POST /api/v1/entropy/bottlenecks

Detect bottleneck and burst layers.

**Request (optional):** `{"threshold": 0.5}`

**Response:**
```json
{"bottlenecks": ["layer3"], "bursts": ["layer1"], "snapshot_count": 42}
```

### POST /api/v1/entropy/trend

Entropy trend for a specific layer.

**Request:** `{"layer": "attn", "count": 10}`

**Response:**
```json
{"layer": "attn", "trend": [2.1, 2.3, 2.0, ...], "stats": {"mean": 2.1, "variance": 0.02, "min": 1.9, "max": 2.4}}
```

---

## Binary Knowledge Store Endpoints

### POST /api/v1/store/add

Add a fact to the ACID binary store (redb).

**Request:** `{"text": "fact text", "embedding": [0.1, 0.2, ...]}`

**Response:** `{"id": 1}`

### POST /api/v1/store/search

Search by vector similarity.

**Request:** `{"query": [0.1, 0.2, ...], "top_k": 5}`

### POST /api/v1/store/get

Get fact by ID.

**Request:** `{"id": 1}`

### POST /api/v1/store/weight

Update retrieval weight.

**Request:** `{"id": 1, "weight": 1.5}`

### POST /api/v1/store/remove

Remove a fact.

**Request:** `{"id": 1}`

### GET /api/v1/store/count

Total fact count.

**Response:** `{"count": 120}`

---

## Cognitive Fabric Endpoints

The unified intelligence pipeline wiring all 18 cognitive modules.

### POST /api/v1/fabric/think

Run a full cognitive think cycle on text input.

**Request:**
```json
{"text": "Zone 5 moisture is 16%, threshold is 20%"}
```

**Response:**
```json
{
  "cycle": {"field": [...], "contradiction_level": 0.1, ...},
  "embedding_dim": 384,
  "cht_facets": 8,
  "knot_nodes": 15,
  "knot_edges": 8,
  "adapter_active": true,
  "topos_peers": 0,
  "think_cycle": 42
}
```

### POST /api/v1/fabric/learn

Teach a fact to the cognitive fabric (embeds, stores in knot graph, auto-links).

**Request:** `{"text": "Tomatoes need pH 6.0-6.8"}`

**Response (201):**
```json
{"fact_node_id": 5, "edges_created": 2, "knot_nodes": 16, "knot_edges": 10}
```

### POST /api/v1/fabric/symbol

Register a named symbol in the knot graph.

**Request:** `{"name": "irrigation"}`

**Response (201):** `{"node_id": 6}`

### POST /api/v1/fabric/train

Run one categorical adapter training step.

**Request:**
```json
{"input": "dry soil zone 5", "target": "irrigate zone 5", "lr": 0.01}
```

**Response:** `{"loss": 0.023}`

### GET /api/v1/fabric/status

Cognitive fabric status snapshot.

**Response:**
```json
{
  "think_cycles": 42,
  "cog_cycles": 42,
  "inference_count": 100,
  "knot_nodes": 15,
  "knot_edges": 8,
  "knot_components": 3,
  "adapter_name": "default",
  "adapter_steps": 50,
  "adapter_params": 512,
  "topos_peers": 0,
  "entropy_snapshots": 42
}
```

---

## Knowledge Knot Graph Endpoints

Topological knowledge graph with braid-encoded relationships.

### POST /api/v1/knot/search

Search knot graph by text (embeds text, then cosine similarity search).

**Request:** `{"text": "irrigation", "top_k": 5}`

**Response:**
```json
{"results": [{"node_id": 3, "similarity": 0.92, "text": "Zone 5 needs irrigation"}]}
```

### POST /api/v1/knot/path

Find shortest path between two nodes (BFS with knot invariants).

**Request:** `{"from": 1, "to": 5}`

**Response:**
```json
{"path": [1, 3, 5], "total_writhe": 2, "total_crossings": 4, "edge_count": 2}
```

### GET /api/v1/knot/stats

Graph statistics.

**Response:**
```json
{
  "total_nodes": 15,
  "total_edges": 8,
  "node_types": {"Fact": 10, "Concept": 3, "Symbol": 2},
  "relation_types": {"Implies": 4, "Contradicts": 1, "RelatedTo": 3},
  "avg_degree": 1.07,
  "components": 3
}
```

### POST /api/v1/knot/contradict

Record a contradiction between two nodes.

**Request:** `{"node_a": 1, "node_b": 5, "intensity": 0.9}`

---

## LLM Bridge Endpoints

Hybrid LLM integration (offline hash fallback, Ollama, OpenAI, vLLM).

### POST /api/v1/llm/embed

Get embedding for text. Uses LLM API if configured, falls back to deterministic hash.

**Request:** `{"text": "irrigation scheduling"}`

**Response:**
```json
{
  "vector": [0.1, -0.3, ...],
  "source": "HashFallback",
  "model": "hash-384",
  "dim": 384
}
```

### POST /api/v1/llm/distill

Distill LLM knowledge into the knot graph and adapter.

**Request:**
```json
{
  "facts": [
    {
      "text": "Tomatoes need 1 inch of water per week",
      "embedding": [0.1, 0.2, ...],
      "confidence": 0.95,
      "source_prompt": "agricultural knowledge"
    }
  ],
  "lr": 0.01
}
```

**Response:**
```json
{"facts_absorbed": 1, "nodes_created": 1, "adapter_loss": 0.015}
```

### GET /api/v1/llm/status

LLM bridge statistics.

**Response:**
```json
{
  "mode": "offline",
  "config": {"base_url": "", "model": ""},
  "embed_count": 50,
  "generate_count": 0,
  "distill_count": 5,
  "cache_hits": 30,
  "cache_size": 50
}
```

---

## Error Responses

All errors follow this format:

```json
{"error": "description of the error"}
```

| HTTP Code | Meaning |
|---|---|
| 400 | Bad request (invalid JSON, missing fields) |
| 401 | Unauthorized (missing/invalid API key) |
| 405 | Method not allowed |
| 413 | Request body too large (>1MB) |
| 429 | Rate limit exceeded |
| 502 | Kernel unavailable |

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `MCP_API_KEY` | *(empty = no auth)* | Bearer token for API authentication |
| `MCP_RATE_LIMIT` | `100` | Requests per minute per IP (0 = disabled) |
| `MCP_KERNEL_SOCKET` | `/tmp/mcp-kernel.sock` | Rust kernel Unix socket path |
| `MCP_STORAGE_DIR` | `/tmp/mcp-kernel-data` | Kernel data directory |
| `MCP_COG_DIM` | `64` | Cognitive vector dimension |
| `MCP_EMBED_DIM` | `384` | Neural embedding dimension |
| `MCP_LLM_URL` | *(empty = offline)* | LLM API base URL (e.g. `http://localhost:11434`) |
| `MCP_LLM_MODEL` | `llama3.1:8b` | LLM model name |
| `MCP_BINARY_STORE` | `{storage}/knowledge.redb` | Binary knowledge store path |
| `MCP_KNOWLEDGE_FILE` | *(empty)* | JSON knowledge file for CogLoop |
