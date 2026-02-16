# MCP-ZERO

**A cognitive AI kernel that learns semantics from text — no neural network, no GPU, no cloud.**

15,000 lines of Rust + Go. Two static binaries totaling 29 MB. Runs in 18 MB of RAM. 276 tests. 43 HTTP endpoints. One Unix socket.

> **Status: Alpha** — Core cognitive pipeline is functional and tested. See [checklist](core/checklist.md).

---

## What It Actually Does

MCP-ZERO is an offline AI runtime. You feed it text. It learns what words mean by observing which words appear near each other. Then it can answer questions like "what is similar to X?" — and it gets them right.

This is not a wrapper around OpenAI. There is no neural network inside. The semantic engine uses **Hyperdimensional Computing** — a branch of mathematics where meaning is encoded as 4096-dimensional vectors and learned through co-occurrence statistics. The math is simple: words that appear in the same contexts get similar vectors.

**Measured results from the live demo (50 sentences, 129 words):**

```
cat ↔ dog   =  0.89   (appear in identical contexts → high similarity)
car ↔ bus   =  0.74   (appear in identical contexts → high similarity)
cat ↔ car   = -0.01   (different domains → near zero)
dog ↔ bus   = -0.01   (different domains → near zero)
cat ↔ soil  =  0.01   (completely unrelated → near zero)
```

The engine discovered that cats and dogs are similar — not because anyone told it, but because it observed "the cat sat on the mat" and "the dog sat on the rug" and accumulated the shared context. This is distributional semantics, the same principle behind Word2Vec, but implemented with hyperdimensional algebra instead of gradient descent.

---

## What's Inside

### Rust Kernel (13,000 lines, 251 tests)

The kernel is a single async binary that listens on a Unix socket and speaks JSON-RPC.

| Module | What it does | Lines |
|---|---|---|
| `hyperdimensional.rs` | Semantic engine — learns word meaning from context using 4096-dim vectors | ~950 |
| `cognitive_fabric.rs` | Orchestrates all cognitive modules into a unified pipeline | ~580 |
| `knowledge_knot.rs` | Graph database — nodes, edges, semantic search, path finding | ~650 |
| `llm_bridge.rs` | Optional LLM integration — Ollama, OpenAI, or offline hash fallback | ~700 |
| `cht.rs` | Categorical Holographic Tokens — compositional vector algebra | ~570 |
| `trainer.rs` | Online adapter training — learns from input/target pairs, no GPU | ~500 |
| `binary_store.rs` | ACID key-value store backed by redb — vector similarity search | ~350 |
| `entropy_graph.rs` | Tracks Shannon entropy per layer — detects bottlenecks and noise | ~480 |
| `cog_loop.rs` | Cognitive cycle — blending, entropy injection, collapse detection | ~300 |
| `ethical.rs` | Binary decision tree — compile-time safety constraints on agent actions | ~440 |
| `trace.rs` | Hash-chained audit trail — tamper-evident event logging | ~360 |
| `agent.rs` | Agent lifecycle — spawn, message, suspend, resume, terminate | ~260 |
| `plugin.rs` | WASM sandbox — run untrusted code with capability-based permissions | ~300 |

### Go Gateway (2,200 lines, 25 tests)

A single HTTP server that proxies requests to the kernel over Unix socket.

- 43 HTTP endpoints under `/api/v1/`
- bbolt embedded database for gateway-level persistence
- Auth middleware (API key via `MCP_API_KEY` env var)
- Rate limiting (token bucket, configurable via `MCP_RATE_LIMIT`)
- Request size limits (1 MB default)

### Hyperdimensional Engine (the core innovation)

The semantic engine replaces traditional neural embeddings with mathematically grounded operations:

| Operation | What it does | Complexity |
|---|---|---|
| **Random Indexing** | Assigns sparse bipolar vectors to words, accumulates context | O(n × w × d) |
| **Bind** (element-wise multiply) | Creates associations — bind(cat, pet) = "cat is a pet" | O(d), κ = 1 |
| **Bundle** (element-wise add) | Creates sets — bundle(cat, dog) = "animals" | O(d), κ = 1 |
| **Permute** (cyclic shift) | Encodes position — permute(word, 3) = "word at position 3" | O(d), κ = 1 |

κ = 1 means the condition number is 1 — these operations are perfectly numerically stable. No floating point drift, no vanishing gradients, no exploding activations.

The mathematical foundations are documented with 26 theorems and proofs in [mathematical_foundations.md](core/mathematical_foundations.md). Key guarantees:

- **Johnson-Lindenstrauss lemma**: Pairwise distances preserved to within 3% at D=4096
- **Hoeffding bound**: Similarity estimates concentrate around true values
- **Banach fixed-point theorem**: Resonator network converges in 3-5 iterations

---

## Architecture

```
                    HTTP :8080
                       │
               ┌───────┴───────┐
               │  Go Gateway   │  auth, rate limit, bbolt, metrics
               │  (7.8 MB)     │
               └───────┬───────┘
                  Unix socket
               ┌───────┴───────┐
               │  Rust Kernel  │  JSON-RPC dispatch, async Tokio
               │  (21 MB)      │
               └───────┬───────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Cognitive      Knowledge       Storage
   Fabric         Knot Graph      (redb ACID)
        │              │
   ┌────┴────┐    Nodes, edges,
   │         │    semantic search,
   HD      Neural  path finding
   Engine  Engine
   (real)  (hash fallback)
```

Two static binaries. No Python runtime. No Docker. No CUDA. No internet connection required.

### How It Learns (Long-Form Language → Critical Decisions)

```
  INPUT: Documents, logs, sensor reports, manuals — any text, any length
  ┌──────────────────────────────────────────────────────────────────┐
  │  "Soil moisture dropped to 12%. Irrigation pump B failed.       │
  │   Backup pump C is offline for maintenance. Crop stress is      │
  │   severe in sector 7. Rain forecast in 48 hours."               │
  └───────────────────────────┬──────────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  1. SPLIT + TOKENIZE + FILTER                                   │
  │     Long text → sentences → content words (stop words removed)  │
  │     "soil moisture dropped 12%" → [soil, moisture, dropped, 12] │
  │     "irrigation pump failed"    → [irrigation, pump, failed]    │
  │     "crop stress severe"        → [crop, stress, severe]        │
  │     Works on 5 words or 5000 sentences — same algorithm.        │
  └───────────────────────────┬──────────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  2. LEARN SEMANTIC VECTORS (accumulate context per word)        │
  │                                                                 │
  │     "pump" appears near: failed, backup, offline, irrigation    │
  │     "crop" appears near: stress, severe, sector, rain           │
  │     "soil" appears near: moisture, dropped, irrigation          │
  │                                                                 │
  │     → pump ≈ irrigation (shared context = high similarity)      │
  │     → crop ≈ stress     (co-occur in crisis sentences)          │
  │     → pump ≈ crop       (low — different operational domains)   │
  │                                                                 │
  │     More text fed over time → sharper word meanings.            │
  │     Each document refines the vectors. No retraining needed.    │
  └───────────────────────────┬──────────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  3. BUILD KNOWLEDGE GRAPH (facts + relationships)               │
  │                                                                 │
  │     [pump_B] ──failed──→ [irrigation]                           │
  │     [pump_C] ──offline──→ [maintenance]                         │
  │     [sector_7] ──status──→ [severe_stress]                      │
  │     [rain] ──forecast──→ [48_hours]                             │
  │                                                                 │
  │     Semantic search: "what relates to water?"                   │
  │     → irrigation(0.87), pump(0.82), moisture(0.79), rain(0.71)  │
  └───────────────────────────┬──────────────────────────────────────┘
                              ▼
  ┌──────────────────────────────────────────────────────────────────┐
  │  4. CRITICAL LOGIC — CONTRADICTION + SAFETY CHECKS              │
  │                                                                 │
  │  ┌─ Sheaf Checker ──────────────────────────────────────────┐   │
  │  │  "pump B failed" + "pump C offline" + "crop stress"      │   │
  │  │  → CONTRADICTION: no water source available              │   │
  │  │  → cohomology obstruction detected (H¹ ≠ 0)             │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                              │                                  │
  │  ┌─ Ethical Tree ────────────▼──────────────────────────────┐   │
  │  │  Action: "ignore and wait for rain"                      │   │
  │  │  → BLOCKED: crop loss risk exceeds safety threshold      │   │
  │  │  Action: "emergency manual irrigation"                   │   │
  │  │  → ALLOWED: preserves crop, within operational bounds    │   │
  │  └──────────────────────────────────────────────────────────┘   │
  │                              │                                  │
  │  This is where edge AI matters: the device on the farm makes   │
  │  this decision in 2ms with 18MB RAM, no cloud, no latency.     │
  └───────────────────────────┬──────────────────────────────────────┘
                              ▼
                        ┌───────────┐
                        │  DECISION │
                        │  + AUDIT  │
                        │  TRAIL    │
                        └───────────┘
  Every step is hash-chained in the trace log. Every decision
  is explainable. Every contradiction is recorded. No black box.
```

The pipeline handles any volume of text — field manuals, sensor streams, maintenance logs — and builds understanding incrementally. The critical difference from cloud AI: when both pumps fail at 2 AM on a farm with no internet, this system is the one making the call. It has to be right, it has to be fast, and it has to explain why.

### Same Learning, Different Math

The HD engine learns the same distributional semantics that transformers learn — words that co-occur in similar contexts get similar representations. The difference is *how*: transformers use gradient descent over millions of parameters with O(n²) attention and condition numbers around 1000; the HD engine uses algebraic accumulation over 4096-dimensional vectors with O(n) operations and a condition number of exactly 1. Same result, provably more stable, no training loop, no GPU. The full equivalence mapping is in [transformer_equivalence.md](core/transformer_equivalence.md).

### Distributed Edge AI

Each MCP-ZERO instance is a self-contained cognitive node — deploy one per device (Raspberry Pi, field sensor, drone, vehicle) and each learns independently from its local data. When nodes can communicate (mesh network, intermittent satellite, USB sync), they exchange learned semantic vectors and knowledge graph fragments to build collective intelligence. The architecture is already built for this: the kernel speaks JSON-RPC over Unix sockets today, and the same protocol works over TCP between nodes tomorrow. No central server, no cloud coordinator — just a mesh of small machines that each understand their own environment and can teach each other what they've learned.

---

## Quick Start

### Prerequisites

- Rust 1.75+ (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- Go 1.22+ (`https://go.dev/dl/`)

### Build

```bash
make all          # Build kernel (release) + gateway
make test         # Run all 276 tests (251 Rust + 25 Go)
```

### Run

```bash
# Terminal 1: Start kernel
MCP_KERNEL_SOCKET=/tmp/mcp.sock MCP_STORAGE_DIR=/tmp/mcp-data \
  ./src/kernel/target/release/mcp-kernel

# Terminal 2: Start gateway
./src/gateway/gateway -addr :8080 -kernel /tmp/mcp.sock -db /tmp/mcp-gw

# Terminal 3: Use it
curl http://localhost:8080/health
```

### Teach it something

```bash
# Teach the HD engine
curl -X POST http://localhost:8080/api/v1/hd/teach -d '{
  "text": "the cat sat on the mat. the dog sat on the rug. the cat chased the mouse. the dog chased the ball."
}'

# Check what it learned
curl -X POST http://localhost:8080/api/v1/hd/similarity -d '{
  "word_a": "cat", "word_b": "dog"
}'
# → {"similarity": 0.89}

# Find similar words
curl -X POST http://localhost:8080/api/v1/hd/most_similar -d '{
  "word": "cat", "top_k": 3
}'
# → {"results": [{"word": "dog", "similarity": 0.89}, ...]}
```

### Run the full demo

```bash
chmod +x demo.sh
./demo.sh
```

The demo starts both services, teaches text across three domains (animals, vehicles, agriculture), tests semantic similarity, and exercises all 11 cognitive modules.

---

## API Overview

All endpoints are under `http://localhost:8080/api/v1/`. Full reference: [docs/API.md](docs/API.md).

| Endpoint | Method | What it does |
|---|---|---|
| `/hd/teach` | POST | Teach text to the semantic engine |
| `/hd/similarity` | POST | Cosine similarity between two learned words |
| `/hd/most_similar` | POST | Find top-k most similar words |
| `/hd/embed` | POST | Get 4096-dim semantic vector for text |
| `/hd/stats` | GET | Engine statistics (vocab size, sentences processed) |
| `/fabric/think` | POST | Full cognitive cycle on text input |
| `/fabric/learn` | POST | Teach a fact to the cognitive fabric |
| `/fabric/train` | POST | One adapter training step (online learning) |
| `/knot/search` | POST | Semantic search over knowledge graph |
| `/knot/path` | POST | Find shortest path between two nodes |
| `/llm/embed` | POST | Get embedding via LLM bridge (or hash fallback) |
| `/llm/distill` | POST | Distill external LLM knowledge into local graph |
| `/store/add` | POST | Add fact to ACID binary store |
| `/store/search` | POST | Vector similarity search over stored facts |
| `/metrics` | GET | Aggregated metrics from all subsystems |
| `/health` | GET | Health check |

---

## What It Is Not

Honesty matters. Here's what MCP-ZERO does **not** do:

- **It is not GPT.** It cannot generate fluent text, write code, or hold a conversation. It learns word-level semantics, not language generation.
- **It is not a transformer.** There is no attention mechanism, no backpropagation, no training loop in the traditional sense. The math is different.
- **It does not scale to millions of words yet.** The current implementation stores full 4096-dim vectors in memory. At 129 words it uses 18 MB. Scaling to 100k+ words will need quantization or disk-backed storage.
- **The LLM bridge is optional.** Without an external LLM (Ollama/OpenAI), the system uses hash-based embeddings for the neural engine. The HD engine works independently.
- **It is alpha software.** The API may change. Some modules are more mature than others. The HD engine and knowledge graph are solid; the WASM plugin system is less tested.

---

## Project Structure

```
mcp-zero/
  src/
    kernel/             # Rust kernel — 13,000 lines, 251 tests
      src/
        cognitive/      # 20 cognitive modules
        main.rs         # JSON-RPC daemon (48 RPC methods)
        agent.rs        # Agent lifecycle
        ethical.rs      # Safety constraints
        trace.rs        # Audit trail
        plugin.rs       # WASM sandbox
    gateway/            # Go HTTP gateway — 2,200 lines, 25 tests
  core/                 # Architecture docs + research
    mathematical_foundations.md    # 26 theorems with proofs
    hyperdimensional_research.md  # 42 papers surveyed
    transformer_equivalence.md    # HDC ↔ transformer mapping
  docs/                 # User-facing documentation
    API.md              # Full API reference
    INSTALL.md          # Installation guide
    CONFIGURATION.md    # All config options
    TROUBLESHOOTING.md  # Common issues + fixes
  demo.sh              # Live demo script (builds + runs everything)
  tests/               # Integration tests
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/API.md](docs/API.md) | Complete API reference — all 43 endpoints |
| [docs/INSTALL.md](docs/INSTALL.md) | Installation and deployment guide |
| [docs/CONFIGURATION.md](docs/CONFIGURATION.md) | All environment variables and flags |
| [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [core/mathematical_foundations.md](core/mathematical_foundations.md) | 26 theorems proving HD engine stability |
| [core/hyperdimensional_research.md](core/hyperdimensional_research.md) | Research survey — 42 papers |
| [core/transformer_equivalence.md](core/transformer_equivalence.md) | How HDC maps to transformer operations |
| [core/mcp_zero.md](core/mcp_zero.md) | Project vision and overview |
| [core/checklist.md](core/checklist.md) | Build progress checklist |

---

## Numbers

| Metric | Value |
|---|---|
| Rust lines of code | 13,000 |
| Go lines of code | 2,200 |
| Rust tests passing | 251 |
| Go tests passing | 25 |
| Total tests | 276 |
| Kernel binary size | 21 MB |
| Gateway binary size | 7.8 MB |
| Runtime memory (50 sentences) | 18 MB |
| HTTP endpoints | 43 |
| JSON-RPC methods | 48 |
| Cognitive modules | 20 |
| HD vector dimension | 4,096 |
| External runtime dependencies | 0 |

---

## License

See [LICENSE](LICENSE).

---

Built by [GlobalSushrut](https://github.com/GlobalSushrut) | umeshlamton@gmail.com
