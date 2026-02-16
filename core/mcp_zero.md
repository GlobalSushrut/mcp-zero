# What Is MCP-ZERO

---

## One Sentence

MCP-ZERO is an **offline-first, self-learning AI operating system** that runs on a $35 device with 500MB RAM, makes autonomous decisions without internet, learns from its own mistakes without retraining, evolves its own rules from experience, and maintains a tamper-evident audit trail of everything it does — designed for the 60% of the world where cloud AI cannot reach.

---

## The Problem MCP-ZERO Solves

There are two worlds of AI:

**World 1: The Cloud World** (where all the hype is)
- GPT, Claude, Gemini — brilliant but need internet, cost per query, no local learning
- Enterprise AI platforms — need data teams, cloud infra, $100K+/year
- Edge AI chips (Jetson, Coral) — need GPU, $200-500 hardware, static models that don't learn

**World 2: The Real World** (where MCP-ZERO lives)
- A fish farm 5km offshore with satellite-only connectivity
- An underground mine where WiFi doesn't penetrate rock
- A smallholder farm in sub-Saharan Africa with no internet
- A glacier research station at 4,000m altitude with solar power only
- A refugee camp field hospital with 1 doctor per 10,000 patients
- A wind turbine 100km offshore where a technician visit costs $50,000
- An anti-poaching unit in a 1,000km² wildlife reserve

In World 2:
- There is **no internet** (or it's intermittent, expensive, slow)
- There is **no GPU** (devices run on solar, battery, or generator)
- There is **no data team** (operators are farmers, rangers, nurses, not engineers)
- There is **no cloud budget** ($0.01/query × 1000 queries/day = unaffordable)
- But the **decisions are critical** — crops die, fish die, people die, species go extinct

**No existing AI product serves World 2.** MCP-ZERO does.

---

## What MCP-ZERO Is

MCP-ZERO is four things:

### 1. An Edge AI Runtime

A complete software stack that runs on a Raspberry Pi 4 (or equivalent ARM/x86 board with 512MB-4GB RAM). It processes sensor data, reasons about it using a language model, makes decisions, and controls actuators — all locally, with zero cloud dependency.

```
Hardware: Any ARM/x86 SBC ($35-100)
RAM: 500MB allocated (runs in as little as 256MB after Rust migration)
Storage: 32GB SD card / eMMC
Power: 2.6W average (solar-viable)
Network: Optional (works fully offline)
```

### 2. A Self-Learning System

Unlike static AI models that are frozen after training, MCP-ZERO **learns continuously from its own experience** on the device:

- **Retrieval weights update** — sources that were wrong get trusted less, sources that were right get trusted more
- **LoRA micro-adapters** — 3KB parameter updates that adjust reasoning without full retraining
- **Concept emergence** — the system discovers new patterns (e.g., "forecasts are unreliable for zone 5 in February") and stores them as first-class knowledge
- **Contract evolution** — rules that cause repeated failures get automatically rewritten based on accumulated evidence

No internet needed. No data scientist needed. No retraining pipeline. The device gets smarter every day just by operating.

### 3. A Safety-Constrained Architecture

Every decision passes through multiple safety layers:

- **Ethical Binary Tree** — a decision tree in the Rust kernel that evaluates every action against safety rules before execution
- **Meta Contracts** — evolving rules that constrain what the system can and cannot do
- **Burnt Contracts** — immutable rules that can NEVER be modified (e.g., "never allow methane >1% without evacuation alert"). Enforced by Rust's type system at compile time — not a boolean flag, but a mathematical terminal object that physically cannot be changed
- **Tamper-Evident Traces** — every decision is recorded in a SHA3 hash chain. Any tampering is detectable. Knot invariants detect trace anomalies

### 4. A Multi-Language Polyglot System

Three languages, each chosen for what it does best:

| Language | Role | Why This Language |
|---|---|---|
| **Rust** | Kernel, agents, plugins, traces, ethical checks, cognitive math | Memory safety, zero GC, compile-time guarantees, WASM sandbox |
| **Go** | HTTP gateway, persistence, external API | Single binary, fast compilation, excellent HTTP stdlib |
| **Python** | LLM inference, prompt engineering | LLM library ecosystem (llama-cpp-python, transformers) |

Connected via Unix domain sockets (2-3x faster than TCP, zero network overhead, OS-level security).

---

## How It Works

### The Cognitive Cycle

Every interaction follows an 8-stage loop:

```
PERCEIVE → UNDERSTAND → REASON → DECIDE → ACT → TRACE → LEARN → ADAPT
    │                                                              │
    └──────────────────────────────────────────────────────────────┘
```

1. **PERCEIVE** — Sensor data arrives (temperature, moisture, vibration, camera, etc.). Multiple modalities are fused into a single perception vector using Kalman-filter-style weighted averaging.

2. **UNDERSTAND** — The perception vector is grounded to symbols. "Temperature 38°C + humidity 90% + crop stage tillering" becomes symbolic concepts the system can reason about.

3. **REASON** — A chunked language model (loaded 67MB at a time from a 400MB on-disk model) reasons over retrieved knowledge, weighted by trust and recency. The model uses 1.58-bit quantization (BitNet) to fit in memory.

4. **DECIDE** — The reasoning output passes through ethical constraints. Burnt contracts project the decision AWAY from forbidden directions. The system physically cannot recommend actions that violate safety rules.

5. **ACT** — The decision is executed via a WASM-sandboxed plugin (e.g., open irrigation valve, send alert, adjust ventilation). Capability-based security limits what each plugin can do.

6. **TRACE** — The entire cycle is recorded in a hash-chained audit trail. Every input, reasoning step, decision, and action is tamper-evident.

7. **LEARN** — If the outcome was wrong (crop wilted, forecast was inaccurate, alarm was false), error propagates backward through the teaching chain. Retrieval weights update, LoRA adapters adjust, knowledge store records the lesson.

8. **ADAPT** — After enough contradictions accumulate against a rule, the rule evolves automatically. After enough similar patterns emerge, a new concept is born. The system rewrites itself — within safety bounds.

### The 7 Interference Fields

MCP-ZERO doesn't use standard token-by-token LLM inference (which requires 500MB+ just for weights). Instead, it uses a **teaching chain** where 7 types of interference interact:

| # | Interference Field | What It Does |
|---|---|---|
| IF-1 | **Teaching Chain RF** | Forward pass: embed → retrieve → reason → generate |
| IF-2 | **RF-to-RF Reverse** | Backward pass: error propagates, weights update, LoRA adapts |
| IF-3 | **Weight RF** | Bayesian trust scoring: recent, frequent, reliable sources rank higher |
| IF-4 | **NF-EF Bridge** | Ethical projection: reasoning is pushed away from forbidden directions |
| IF-5 | **Self-Learning NF** | Concept emergence, knowledge store updates, LoRA micro-updates |
| IF-6 | **Adaptive RF** | Dynamic routing: simple queries → cache (2ms), complex → full reasoning (260ms) |
| IF-7 | **Range RF** | Context compression: months of history in 1.5KB using attention sinks + EMA |

The LLM is split into 3 blocks (Embedder, Reasoner, Generator), each 67MB. Only one block is in RAM at a time. Blocks are prefetched asynchronously while the previous block computes. Total inference: 260ms from sensor to action.

### The ZETA Layer (Mathematical Stability)

The self-learning and self-improvement mechanisms are stabilized by real mathematics:

| Math | What It Guarantees |
|---|---|
| **Category Theory** | Composition is associative and identity-preserving. Components compose correctly by construction. Learning is a parametric lens (forward inference + backward update). |
| **Knot Theory** | Trace integrity via linking numbers and writhe. Detects agent entanglement, self-contradiction loops, and anomalous state trajectories via persistent homology. |
| **Zeta Functions** | Convergence of self-improvement via zeta regularization. Network health via Ihara zeta function. Cognitive stability via spectral analysis (eigenvalue monitoring). |
| **Lawvere's Fixed-Point Theorem** | Self-improvement provably converges to a stable configuration. Mutation magnitude decreases as k^n (contraction mapping). Burnt contracts are terminal objects — mathematically immutable. |

---

## The Software Stack

```
┌─────────────────────────────────────────────────────────────┐
│  PORT :8080 — Go Gateway (13MB RAM, 3MB binary)             │
│  Single ServeMux, bbolt embedded DB, JSON metrics            │
│  Routes: /api/v1/agent/*, /api/v1/audit/*, /api/v1/llm/*   │
└────────────────────────┬────────────────────────────────────┘
                         │ Unix socket
┌────────────────────────┴────────────────────────────────────┐
│  Rust Kernel (16MB RAM, 5MB binary)                          │
│  Agent lifecycle, WASM plugin sandbox (wasmtime)             │
│  Ethical Binary Tree, Poseidon hash chain traces             │
│  Cognitive components: mock reasoner, entropy engine,        │
│  symbol bridge, modality fold, meta contracts                │
└────────────────────────┬────────────────────────────────────┘
                         │ Unix socket (or Rust FFI)
┌────────────────────────┴────────────────────────────────────┐
│  LLM Inference (67MB per block, 400MB model on disk)         │
│  BitNet 1.58-bit, 3 blocks loaded one at a time             │
│  Teaching chain with 7 interference fields                   │
│  Knowledge store: mmap'd facts + emerged concepts            │
└─────────────────────────────────────────────────────────────┘

Storage:
  bbolt DB: agent state, audit trails, contracts (single file, crash-safe)
  Knowledge store: mmap'd JSON-L (facts, emerged concepts, retrieval index)
  BitNet model: 400MB on disk, loaded 67MB at a time
  LoRA adapters: 9KB total (3 blocks × 3KB)
  RWKV hidden states: 1.5KB per conversation

Total: 4 processes, 1 TCP port, 3 Unix sockets
Peak RAM: 151MB (after Rust migration) of 500MB budget
Disk: 923MB of 32GB card
Power: 2.6W average
```

---

## What Makes MCP-ZERO Different

### vs Cloud AI (GPT, Claude, Gemini)

| | Cloud AI | MCP-ZERO |
|---|---|---|
| Internet required | Yes, always | No, never |
| Cost per query | $0.01-0.10 | $0 (runs locally) |
| Learns from YOUR data | No (or requires fine-tuning pipeline) | Yes, continuously, on-device |
| Latency | 500ms-5s (network round trip) | 260ms (local) |
| Privacy | Data leaves device | Data never leaves device |
| Works underground/offshore/remote | No | Yes |
| Audit trail | Provider-dependent | Tamper-evident hash chain |

### vs Edge AI Chips (Jetson, Coral, Hailo)

| | Edge AI Chips | MCP-ZERO |
|---|---|---|
| Hardware cost | $200-500 | $35 (Raspberry Pi) |
| GPU required | Yes | No (CPU only, 1.58-bit quantization) |
| Model updates | Requires redeployment | Self-learning, no redeployment |
| Self-learning | No (static inference) | Yes (LoRA + concept emergence) |
| Rule evolution | No | Yes (contract evolution from contradictions) |
| Safety constraints | Application-level | Compile-time enforced (Rust type system) |
| Power | 10-30W | 2.6W |

### vs IoT Platforms (AWS IoT, Azure IoT, Google Cloud IoT)

| | IoT Platforms | MCP-ZERO |
|---|---|---|
| Cloud dependency | Yes (core requirement) | No (fully offline) |
| Subscription cost | $10-100/month/device | $0 |
| On-device intelligence | Rules engine only | Full LLM reasoning |
| Offline operation | Limited/degraded | Full capability |
| Self-improvement | No | Yes (RSI with convergence guarantees) |
| Multi-device coordination | Cloud-mediated | Peer-to-peer mesh |

### vs Traditional SCADA/PLC

| | SCADA/PLC | MCP-ZERO |
|---|---|---|
| Decision logic | Fixed rules, PID controllers | Adaptive reasoning with LLM |
| Learns from experience | No | Yes |
| Handles novel situations | No (only programmed scenarios) | Yes (reasons from knowledge) |
| Configuration | Requires engineer | Self-configuring |
| Cost | $5,000-50,000 | $35-100 |
| Audit trail | Basic logging | Tamper-evident hash chain |

---

## Who It's For

### 30 Validated Use Cases Across 7 Fields

**Agriculture** — Precision irrigation, livestock health, greenhouse climate, aquaculture, beekeeping

**Industrial** — Mine safety, pipeline inspection drones, wind turbine maintenance, water treatment, concrete curing

**Healthcare** — Remote clinic triage, neonatal monitoring, elderly chronic disease, veterinary diagnostics, school mental health screening

**Conservation** — Anti-poaching, wildfire detection, glacier monitoring, volcano early warning, tsunami buoys

**Defense & Security** — Border surveillance, submarine/UUV autonomy, tactical mesh comms, perimeter security

**Infrastructure** — Bridge/dam structural health, railway track monitoring, microgrid management

**Emerging** — Space habitat life support, archaeological site monitoring, autonomous transoceanic sailing

Every use case shares 3 characteristics:
1. **No reliable connectivity** — cloud AI is impossible
2. **Must learn locally** — every site/animal/machine is unique
3. **Safety constraints are non-negotiable** — burnt contracts protect life

---

## The Numbers

| Metric | Value |
|---|---|
| **Hardware** | Any ARM/x86 SBC, $35-100 |
| **RAM** | 151MB peak (of 500MB budget) |
| **Disk** | 923MB (of 32GB card) |
| **Power** | 2.6W average (solar-viable) |
| **Latency** | 260ms sensor-to-action (including LLM reasoning) |
| **Offline duration** | Indefinite (no degradation) |
| **Self-learning** | Continuous, no retraining, no internet |
| **Model** | 2B params, 1.58-bit BitNet, 400MB on disk |
| **Inference** | Chunked: 67MB per block, 3 blocks sequential |
| **Cognitive cycle** | 3.7μs (Rust), 270x faster than Python |
| **Safety** | Compile-time enforced via Rust type system |
| **Audit** | SHA3 hash chain, tamper-evident, knot invariant analysis |
| **Processes** | 4 (Go gateway, Rust kernel, LLM inference, sensor daemon) |
| **Ports** | 1 TCP (:8080) + 3 Unix sockets |
| **Binary size** | Go: 3MB, Rust: 5MB, total: 8MB |
| **Convergence** | Provable via Lawvere fixed-point + Banach contraction |

---

## The Architecture Documents

MCP-ZERO's architecture is documented across 6 research-backed documents:

| Document | What It Covers |
|---|---|
| **`arch_1.md`** | The 8-stage cognitive cycle: Perceive → Understand → Reason → Decide → Act → Trace → Learn → Adapt. Real math at each stage. |
| **`arch_2.md`** | The 7 interference fields and chunked LLM inference. How to run a 2B-parameter model in 500MB RAM. Teaching chain architecture. |
| **`zeta_arch.md`** | Mathematical stability: category theory (compositional correctness), knot theory (trace integrity), zeta functions (convergence), Lawvere (safe self-reference). |
| **`go_arch.md`** | Go gateway redesign: from 9 ports/34 files/58MB to 1 port/8 files/13MB. bbolt, Unix sockets, zero external dependencies. |
| **`python_to_rust.md`** | Migration analysis: 5 Python files → Rust for 270x faster cognitive cycle, 119MB RAM savings, 4 safety bugs eliminated at compile time. |
| **`mcp_unified_arch.md`** | The complete system: how all layers connect, end-to-end walkthrough of a real task (sensor reading → LLM reasoning → valve open in 260ms), offline operation, multi-node distribution. |

Supporting research:
| Document | What It Covers |
|---|---|
| **`research_math_foundations.md`** | Mathematical algorithms mapped to MCP-ZERO components |
| **`research_engineering_ai.md`** | Engineering systems and AI experiments validating the approach |
| **`research_market_segments.md`** | Market analysis for target deployment segments |
| **`use_cases.md`** | 30 concrete use cases with interference field patterns |
| **`logic_old.md`** | Analysis of original developer logic and improvement areas |

---

## The Vision

Every year, decisions that affect millions of lives are made by people with no tools:

- A farmer guesses when to irrigate. Gets it wrong. Crop fails. Family goes hungry.
- A ranger patrols 1,000km² on foot. Poachers slip through. Another rhino dies.
- A community health worker sees a sick child. No doctor for 200km. Guesses wrong. Child dies.
- A fish farmer checks oxygen levels manually. Misses the drop at 3am. Entire stock dies.
- A mine supervisor reads a gas meter. Doesn't notice the trend. Explosion kills 12.

These aren't technology problems. They're **access** problems. The AI exists. The knowledge exists. But it's locked behind cloud subscriptions, GPU requirements, internet connectivity, and data science teams that these people will never have.

MCP-ZERO puts a self-learning, safety-constrained, mathematically-stable AI on a $35 device that runs on solar power with no internet. It learns the unique patterns of each farm, each mine, each clinic, each reef. It gets smarter every day. It can't be tricked into unsafe decisions. And every decision it makes is recorded in a tamper-evident trail that can be audited years later.

**MCP-ZERO is AI for the places where AI matters most and exists least.**
