//! MCP-ZERO Kernel Daemon
//!
//! Listens on a Unix domain socket for JSON-RPC requests from the Go gateway.
//! Protocol: newline-delimited JSON over Unix socket.
//!
//! Supported methods:
//!   - kernel.spawn_agent   { config: AgentConfig }           → { agent_id }
//!   - kernel.execute       { agent_id, intent }              → { result }
//!   - kernel.attach_plugin { agent_id, plugin_id }           → {}
//!   - kernel.snapshot      { agent_id }                      → {}
//!   - kernel.recover       { agent_id }                      → { status }
//!   - kernel.status        {}                                → { agents, uptime }

use std::path::PathBuf;
use std::sync::Arc;
use std::time::Instant;

use anyhow::Result;
use serde::{Serialize, Deserialize};
use tokio::io::{AsyncBufReadExt, AsyncWriteExt, BufReader};
use tokio::net::UnixListener;

use mcp_kernel::{MCPKernel, AgentConfig, KernelError};
use mcp_kernel::cognitive::{CogLoop, CogVec, EntropyGraph, BinaryKnowledgeStore};
use mcp_kernel::cognitive::cognitive_fabric::{CognitiveFabric, FabricConfig};
use mcp_kernel::cognitive::llm_bridge::{LLMBridge, LLMConfig, EmbeddingMode, DistilledFact};
use tokio::sync::Mutex;

/// Default socket path
const DEFAULT_SOCKET: &str = "/tmp/mcp-kernel.sock";

/// JSON-RPC request envelope
#[derive(Debug, Deserialize)]
struct RpcRequest {
    /// JSON-RPC version (always "2.0")
    jsonrpc: String,
    /// Method name
    method: String,
    /// Parameters (optional)
    #[serde(default)]
    params: serde_json::Value,
    /// Request ID
    id: serde_json::Value,
}

/// JSON-RPC response envelope
#[derive(Debug, Serialize)]
struct RpcResponse {
    jsonrpc: &'static str,
    #[serde(skip_serializing_if = "Option::is_none")]
    result: Option<serde_json::Value>,
    #[serde(skip_serializing_if = "Option::is_none")]
    error: Option<RpcError>,
    id: serde_json::Value,
}

/// JSON-RPC error
#[derive(Debug, Serialize)]
struct RpcError {
    code: i32,
    message: String,
}

impl RpcResponse {
    fn ok(id: serde_json::Value, result: serde_json::Value) -> Self {
        Self { jsonrpc: "2.0", result: Some(result), error: None, id }
    }

    fn err(id: serde_json::Value, code: i32, message: String) -> Self {
        Self { jsonrpc: "2.0", result: None, error: Some(RpcError { code, message }), id }
    }
}

/// Shared kernel state
struct KernelState {
    kernel: MCPKernel,
    cog: Mutex<CogLoop>,
    entropy_graph: Mutex<EntropyGraph>,
    binary_store: Mutex<BinaryKnowledgeStore>,
    fabric: Mutex<CognitiveFabric>,
    llm_bridge: Mutex<LLMBridge>,
    start_time: Instant,
}

#[tokio::main]
async fn main() -> Result<()> {
    // Initialize tracing
    let _ = tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| tracing_subscriber::EnvFilter::new("info"))
        )
        .compact()
        .try_init();

    // Determine socket path from env or default
    let socket_path = std::env::var("MCP_KERNEL_SOCKET")
        .unwrap_or_else(|_| DEFAULT_SOCKET.to_string());
    let socket_path = PathBuf::from(&socket_path);

    // Remove stale socket file
    if socket_path.exists() {
        std::fs::remove_file(&socket_path)?;
    }

    // Create parent directory if needed
    if let Some(parent) = socket_path.parent() {
        if !parent.exists() {
            std::fs::create_dir_all(parent)?;
        }
    }

    // Initialize storage
    let storage_dir = std::env::var("MCP_STORAGE_DIR")
        .unwrap_or_else(|_| "/tmp/mcp-kernel-data".to_string());
    mcp_kernel::storage_init(&storage_dir)?;

    // Create kernel
    let cog_dim: usize = std::env::var("MCP_COG_DIM")
        .ok()
        .and_then(|s| s.parse().ok())
        .unwrap_or(64);

    let cog = match std::env::var("MCP_KNOWLEDGE_FILE") {
        Ok(path) => CogLoop::with_knowledge_file(cog_dim, &path)
            .unwrap_or_else(|_| CogLoop::new(cog_dim)),
        Err(_) => CogLoop::new(cog_dim),
    };

    // Initialize entropy graph
    let entropy_graph = EntropyGraph::new(1000);

    // Initialize binary knowledge store
    let binary_store_path = std::env::var("MCP_BINARY_STORE")
        .unwrap_or_else(|_| format!("{}/knowledge.redb", storage_dir));
    let binary_store = BinaryKnowledgeStore::open(
        std::path::Path::new(&binary_store_path), cog_dim
    ).unwrap_or_else(|e| {
        tracing::warn!("Failed to open binary store at {}: {}, using in-memory", binary_store_path, e);
        BinaryKnowledgeStore::in_memory(cog_dim).expect("in-memory store")
    });

    // Initialize cognitive fabric
    let fabric_config = FabricConfig {
        cog_dim: cog_dim,
        embed_dim: std::env::var("MCP_EMBED_DIM")
            .ok().and_then(|s| s.parse().ok()).unwrap_or(384),
        ..FabricConfig::default()
    };
    let fabric = CognitiveFabric::new(fabric_config);

    // Initialize LLM bridge
    let llm_bridge = match std::env::var("MCP_LLM_URL") {
        Ok(url) => {
            let model = std::env::var("MCP_LLM_MODEL").unwrap_or_else(|_| "llama3.1:8b".into());
            LLMBridge::new(LLMConfig::compatible(&url, &model), EmbeddingMode::HybridFallback)
        }
        Err(_) => LLMBridge::offline(),
    };

    let state = Arc::new(KernelState {
        kernel: MCPKernel::new(),
        cog: Mutex::new(cog),
        entropy_graph: Mutex::new(entropy_graph),
        binary_store: Mutex::new(binary_store),
        fabric: Mutex::new(fabric),
        llm_bridge: Mutex::new(llm_bridge),
        start_time: Instant::now(),
    });

    // Bind Unix socket
    let listener = UnixListener::bind(&socket_path)?;
    tracing::info!("MCP-ZERO kernel listening on {}", socket_path.display());

    // Handle graceful shutdown
    let shutdown = async {
        tokio::signal::ctrl_c().await.ok();
        tracing::info!("Shutdown signal received");
    };

    tokio::select! {
        _ = accept_loop(listener, state) => {},
        _ = shutdown => {},
    }

    // Cleanup socket
    let _ = std::fs::remove_file(&socket_path);
    tracing::info!("MCP-ZERO kernel stopped");
    Ok(())
}

async fn accept_loop(listener: UnixListener, state: Arc<KernelState>) -> Result<()> {
    loop {
        match listener.accept().await {
            Ok((stream, _addr)) => {
                let state = Arc::clone(&state);
                tokio::spawn(async move {
                    if let Err(e) = handle_connection(stream, state).await {
                        tracing::error!("Connection error: {}", e);
                    }
                });
            }
            Err(e) => {
                tracing::error!("Accept error: {}", e);
            }
        }
    }
}

async fn handle_connection(
    stream: tokio::net::UnixStream,
    state: Arc<KernelState>,
) -> Result<()> {
    let (reader, mut writer) = stream.into_split();
    let mut lines = BufReader::new(reader).lines();

    while let Some(line) = lines.next_line().await? {
        let line = line.trim().to_string();
        if line.is_empty() {
            continue;
        }

        let response = match serde_json::from_str::<RpcRequest>(&line) {
            Ok(req) => dispatch(&state, req).await,
            Err(e) => RpcResponse::err(
                serde_json::Value::Null,
                -32700,
                format!("Parse error: {}", e),
            ),
        };

        let mut out = serde_json::to_vec(&response)?;
        out.push(b'\n');
        writer.write_all(&out).await?;
    }

    Ok(())
}

async fn dispatch(state: &KernelState, req: RpcRequest) -> RpcResponse {
    if req.jsonrpc != "2.0" {
        return RpcResponse::err(req.id, -32600, "Invalid JSON-RPC version".into());
    }

    match req.method.as_str() {
        // Kernel methods
        "kernel.spawn_agent" => handle_spawn_agent(state, req.params, req.id),
        "kernel.execute" => handle_execute(state, req.params, req.id),
        "kernel.attach_plugin" => handle_attach_plugin(state, req.params, req.id),
        "kernel.snapshot" => handle_snapshot(state, req.params, req.id),
        "kernel.recover" => handle_recover(state, req.params, req.id),
        "kernel.status" => handle_status(state, req.id),
        // Cognitive methods
        "cog.state" => handle_cog_state(state, req.id).await,
        "cog.cycle" => handle_cog_cycle(state, req.params, req.id).await,
        "cog.register_intention" => handle_cog_register_intention(state, req.params, req.id).await,
        "cog.activate_intention" => handle_cog_activate_intention(state, req.params, req.id).await,
        "cog.process_contradiction" => handle_cog_contradiction(state, req.params, req.id).await,
        "cog.add_fact" => handle_cog_add_fact(state, req.params, req.id).await,
        "cog.search" => handle_cog_search(state, req.params, req.id).await,
        "cog.register_symbol" => handle_cog_register_symbol(state, req.params, req.id).await,
        "cog.ground" => handle_cog_ground(state, req.params, req.id).await,
        // Entropy graph methods
        "entropy.record" => handle_entropy_record(state, req.params, req.id).await,
        "entropy.snapshot" => handle_entropy_snapshot(state, req.id).await,
        "entropy.bottlenecks" => handle_entropy_bottlenecks(state, req.params, req.id).await,
        "entropy.trend" => handle_entropy_trend(state, req.params, req.id).await,
        // Binary knowledge store methods
        "store.add" => handle_store_add(state, req.params, req.id).await,
        "store.search" => handle_store_search(state, req.params, req.id).await,
        "store.get" => handle_store_get(state, req.params, req.id).await,
        "store.update_weight" => handle_store_update_weight(state, req.params, req.id).await,
        "store.remove" => handle_store_remove(state, req.params, req.id).await,
        "store.count" => handle_store_count(state, req.id).await,
        // Cognitive Fabric methods
        "fabric.think" => handle_fabric_think(state, req.params, req.id).await,
        "fabric.learn" => handle_fabric_learn(state, req.params, req.id).await,
        "fabric.learn_symbol" => handle_fabric_learn_symbol(state, req.params, req.id).await,
        "fabric.train" => handle_fabric_train(state, req.params, req.id).await,
        "fabric.status" => handle_fabric_status(state, req.id).await,
        // Knowledge Knot Graph methods
        "knot.search" => handle_knot_search(state, req.params, req.id).await,
        "knot.path" => handle_knot_path(state, req.params, req.id).await,
        "knot.stats" => handle_knot_stats(state, req.id).await,
        "knot.contradict" => handle_knot_contradict(state, req.params, req.id).await,
        // LLM Bridge methods
        "llm.embed" => handle_llm_embed(state, req.params, req.id).await,
        "llm.distill" => handle_llm_distill(state, req.params, req.id).await,
        "llm.status" => handle_llm_status(state, req.id).await,
        // Hyperdimensional Engine methods
        "hd.teach" => handle_hd_teach(state, req.params, req.id).await,
        "hd.embed" => handle_hd_embed(state, req.params, req.id).await,
        "hd.similarity" => handle_hd_similarity(state, req.params, req.id).await,
        "hd.most_similar" => handle_hd_most_similar(state, req.params, req.id).await,
        "hd.stats" => handle_hd_stats(state, req.id).await,
        _ => RpcResponse::err(req.id, -32601, format!("Method not found: {}", req.method)),
    }
}

fn handle_spawn_agent(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let config: AgentConfig = match serde_json::from_value(params) {
        Ok(c) => c,
        Err(e) => return RpcResponse::err(id, -32602, format!("Invalid params: {}", e)),
    };

    match state.kernel.spawn_agent(config) {
        Ok(agent_id) => RpcResponse::ok(id, serde_json::json!({ "agent_id": agent_id })),
        Err(e) => kernel_err_to_rpc(id, e),
    }
}

fn handle_execute(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let agent_id = match params.get("agent_id").and_then(|v| v.as_str()) {
        Some(s) => s.to_string(),
        None => return RpcResponse::err(id, -32602, "Missing agent_id".into()),
    };
    let intent = match params.get("intent").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing intent".into()),
    };

    match state.kernel.execute(&agent_id, intent) {
        Ok(result) => RpcResponse::ok(id, serde_json::json!({ "result": result })),
        Err(e) => kernel_err_to_rpc(id, e),
    }
}

fn handle_attach_plugin(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let agent_id = match params.get("agent_id").and_then(|v| v.as_str()) {
        Some(s) => s.to_string(),
        None => return RpcResponse::err(id, -32602, "Missing agent_id".into()),
    };
    let plugin_id = match params.get("plugin_id").and_then(|v| v.as_str()) {
        Some(s) => s.to_string(),
        None => return RpcResponse::err(id, -32602, "Missing plugin_id".into()),
    };

    match state.kernel.attach_plugin(&agent_id, &plugin_id) {
        Ok(()) => RpcResponse::ok(id, serde_json::json!({})),
        Err(e) => kernel_err_to_rpc(id, e),
    }
}

fn handle_snapshot(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let agent_id = match params.get("agent_id").and_then(|v| v.as_str()) {
        Some(s) => s.to_string(),
        None => return RpcResponse::err(id, -32602, "Missing agent_id".into()),
    };

    match state.kernel.snapshot(&agent_id) {
        Ok(()) => RpcResponse::ok(id, serde_json::json!({})),
        Err(e) => kernel_err_to_rpc(id, e),
    }
}

fn handle_recover(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let agent_id = match params.get("agent_id").and_then(|v| v.as_str()) {
        Some(s) => s.to_string(),
        None => return RpcResponse::err(id, -32602, "Missing agent_id".into()),
    };

    match state.kernel.recover(&agent_id) {
        Ok(status) => RpcResponse::ok(id, serde_json::json!({ "status": format!("{:?}", status) })),
        Err(e) => kernel_err_to_rpc(id, e),
    }
}

fn handle_status(state: &KernelState, id: serde_json::Value) -> RpcResponse {
    let uptime = state.start_time.elapsed().as_secs();
    RpcResponse::ok(id, serde_json::json!({
        "uptime_secs": uptime,
        "version": env!("CARGO_PKG_VERSION"),
    }))
}

fn kernel_err_to_rpc(id: serde_json::Value, err: KernelError) -> RpcResponse {
    let code = match &err {
        KernelError::AgentNotFound(_) => -32001,
        KernelError::PluginNotFound(_) => -32002,
        KernelError::ResourceLimitExceeded(_) => -32003,
        KernelError::PermissionDenied(_) => -32004,
        KernelError::InvalidConfiguration(_) => -32005,
        KernelError::StorageError(_) => -32006,
        KernelError::ExecutionError(_) => -32007,
        KernelError::EthicalConstraintViolated(_) => -32008,
        KernelError::TraceError(_) => -32009,
        KernelError::Internal(_) => -32010,
    };
    RpcResponse::err(id, code, err.to_string())
}

// ---------------------------------------------------------------------------
// Cognitive RPC handlers
// ---------------------------------------------------------------------------

/// Helper: parse a JSON array of f32 into a CogVec.
/// Pads with zeros if input is shorter than COG_DIM, truncates if longer.
fn parse_vec(val: &serde_json::Value) -> Option<CogVec> {
    use mcp_kernel::cognitive::types::DEFAULT_DIM;
    val.as_array().map(|arr| {
        let mut floats = vec![0.0f32; DEFAULT_DIM];
        for (i, v) in arr.iter().enumerate() {
            if i >= DEFAULT_DIM { break; }
            if let Some(f) = v.as_f64() {
                floats[i] = f as f32;
            }
        }
        CogVec::from_slice(&floats)
    })
}

/// cog.state {} → { field, contradiction_level, dominant_symbols, active_intentions, cycle }
async fn handle_cog_state(state: &KernelState, id: serde_json::Value) -> RpcResponse {
    let cog = state.cog.lock().await;
    let s = cog.state();
    RpcResponse::ok(id, serde_json::to_value(&s).unwrap_or_default())
}

/// cog.cycle { input?: [f32...] } → CycleResult
async fn handle_cog_cycle(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let mut cog = state.cog.lock().await;
    let input = params.get("input").and_then(parse_vec);
    let result = cog.cycle(input.as_ref());
    RpcResponse::ok(id, serde_json::to_value(&result).unwrap_or_default())
}

/// cog.register_intention { name, priority } → { ok }
async fn handle_cog_register_intention(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let name = match params.get("name").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing name".into()),
    };
    let priority = params.get("priority")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.5) as f32;

    let mut cog = state.cog.lock().await;
    let ok = cog.register_intention(name, priority);
    RpcResponse::ok(id, serde_json::json!({ "ok": ok }))
}

/// cog.activate_intention { name } → { ok }
async fn handle_cog_activate_intention(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let name = match params.get("name").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing name".into()),
    };

    let mut cog = state.cog.lock().await;
    let ok = cog.activate_intention(name);
    RpcResponse::ok(id, serde_json::json!({ "ok": ok }))
}

/// cog.process_contradiction { vector: [f32...] } → CognitiveState
async fn handle_cog_contradiction(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let vec = match params.get("vector").and_then(parse_vec) {
        Some(v) => v,
        None => return RpcResponse::err(id, -32602, "Missing vector".into()),
    };

    let mut cog = state.cog.lock().await;
    let s = cog.process_contradiction(&vec);
    RpcResponse::ok(id, serde_json::to_value(&s).unwrap_or_default())
}

/// cog.add_fact { text, embedding: [f32...] } → { id }
async fn handle_cog_add_fact(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let embedding = match params.get("embedding").and_then(parse_vec) {
        Some(v) => v,
        None => return RpcResponse::err(id, -32602, "Missing embedding".into()),
    };

    let mut cog = state.cog.lock().await;
    match cog.knowledge.add_fact(text, embedding) {
        Ok(fact_id) => RpcResponse::ok(id, serde_json::json!({ "id": fact_id })),
        Err(e) => RpcResponse::err(id, -32010, format!("add_fact failed: {}", e)),
    }
}

/// cog.search { query: [f32...], top_k?: int } → { results }
async fn handle_cog_search(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let query = match params.get("query").and_then(parse_vec) {
        Some(v) => v,
        None => return RpcResponse::err(id, -32602, "Missing query".into()),
    };
    let top_k = params.get("top_k")
        .and_then(|v| v.as_u64())
        .unwrap_or(5) as usize;

    let mut cog = state.cog.lock().await;
    let results = cog.knowledge.search(&query, top_k);
    RpcResponse::ok(id, serde_json::json!({ "results": serde_json::to_value(&results).unwrap_or_default() }))
}

/// cog.register_symbol { domain, symbol, vector?: [f32...] } → { ok }
async fn handle_cog_register_symbol(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let domain = match params.get("domain").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing domain".into()),
    };
    let symbol = match params.get("symbol").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing symbol".into()),
    };
    let vector = params.get("vector").and_then(parse_vec);

    let mut cog = state.cog.lock().await;
    let ok = cog.symbols.register_symbol(domain, symbol, vector);
    RpcResponse::ok(id, serde_json::json!({ "ok": ok }))
}

/// cog.ground { vector: [f32...] } → GroundingResult
async fn handle_cog_ground(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let vec = match params.get("vector").and_then(parse_vec) {
        Some(v) => v,
        None => return RpcResponse::err(id, -32602, "Missing vector".into()),
    };

    let mut cog = state.cog.lock().await;
    let result = cog.symbols.ground_neural_to_symbolic(&vec);
    RpcResponse::ok(id, serde_json::json!({
        "top_symbols": result.top_symbols,
        "coherence": result.coherence,
        "emerged": result.emerged,
    }))
}

// ---------------------------------------------------------------------------
// Entropy Graph RPC handlers
// ---------------------------------------------------------------------------

/// Helper: parse a JSON array of arrays into layer activations.
fn parse_layers(val: &serde_json::Value) -> Option<Vec<(String, Vec<f32>)>> {
    val.as_array().map(|arr| {
        arr.iter().filter_map(|layer| {
            let name = layer.get("name")?.as_str()?.to_string();
            let activations: Vec<f32> = layer.get("activations")?
                .as_array()?
                .iter()
                .filter_map(|v| v.as_f64().map(|f| f as f32))
                .collect();
            Some((name, activations))
        }).collect()
    })
}

/// entropy.record { layers: [{name, activations: [f32...]}] } → EntropySnapshot
async fn handle_entropy_record(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let layers = match params.get("layers").and_then(parse_layers) {
        Some(l) if !l.is_empty() => l,
        _ => return RpcResponse::err(id, -32602, "Missing or empty layers".into()),
    };

    let refs: Vec<(&str, &[f32])> = layers.iter()
        .map(|(name, acts)| (name.as_str(), acts.as_slice()))
        .collect();

    let mut eg = state.entropy_graph.lock().await;
    let snap = eg.record_pass(&refs);
    RpcResponse::ok(id, serde_json::to_value(&snap).unwrap_or_default())
}

/// entropy.snapshot {} → latest EntropySnapshot
async fn handle_entropy_snapshot(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let eg = state.entropy_graph.lock().await;
    match eg.latest() {
        Some(snap) => RpcResponse::ok(id, serde_json::to_value(snap).unwrap_or_default()),
        None => RpcResponse::ok(id, serde_json::json!({ "empty": true })),
    }
}

/// entropy.bottlenecks { threshold?: f64 } → { bottlenecks, bursts }
async fn handle_entropy_bottlenecks(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let threshold = params.get("threshold")
        .and_then(|v| v.as_f64())
        .unwrap_or(0.5);

    let eg = state.entropy_graph.lock().await;
    let bottlenecks = eg.detect_bottlenecks(threshold);
    let bursts = eg.detect_bursts(threshold);
    RpcResponse::ok(id, serde_json::json!({
        "bottlenecks": bottlenecks,
        "bursts": bursts,
        "snapshot_count": eg.snapshot_count(),
    }))
}

/// entropy.trend { layer, count?: int } → { trend: [f64...] }
async fn handle_entropy_trend(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let layer = match params.get("layer").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing layer".into()),
    };
    let count = params.get("count")
        .and_then(|v| v.as_u64())
        .unwrap_or(10) as usize;

    let eg = state.entropy_graph.lock().await;
    let trend = eg.layer_trend(layer, count);
    let stats = eg.layer_stats(layer);
    RpcResponse::ok(id, serde_json::json!({
        "layer": layer,
        "trend": trend,
        "stats": stats.map(|(mean, var, min, max)| serde_json::json!({
            "mean": mean, "variance": var, "min": min, "max": max
        })),
    }))
}

// ---------------------------------------------------------------------------
// Binary Knowledge Store RPC handlers
// ---------------------------------------------------------------------------

/// store.add { text, embedding: [f32...] } → { id }
async fn handle_store_add(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let embedding: Vec<f32> = match params.get("embedding").and_then(|v| v.as_array()) {
        Some(arr) => arr.iter().filter_map(|v| v.as_f64().map(|f| f as f32)).collect(),
        None => return RpcResponse::err(id, -32602, "Missing embedding".into()),
    };

    let mut store = state.binary_store.lock().await;
    match store.add_fact(text, &embedding) {
        Ok(fact_id) => RpcResponse::ok(id, serde_json::json!({ "id": fact_id })),
        Err(e) => RpcResponse::err(id, -32010, format!("store.add failed: {}", e)),
    }
}

/// store.search { query: [f32...], top_k?: int } → { results }
async fn handle_store_search(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let query: Vec<f32> = match params.get("query").and_then(|v| v.as_array()) {
        Some(arr) => arr.iter().filter_map(|v| v.as_f64().map(|f| f as f32)).collect(),
        None => return RpcResponse::err(id, -32602, "Missing query".into()),
    };
    let top_k = params.get("top_k")
        .and_then(|v| v.as_u64())
        .unwrap_or(5) as usize;

    let store = state.binary_store.lock().await;
    match store.search(&query, top_k) {
        Ok(results) => RpcResponse::ok(id, serde_json::json!({ "results": serde_json::to_value(&results).unwrap_or_default() })),
        Err(e) => RpcResponse::err(id, -32010, format!("store.search failed: {}", e)),
    }
}

/// store.get { id } → BinaryFact
async fn handle_store_get(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let fact_id = match params.get("id").and_then(|v| v.as_u64()) {
        Some(i) => i,
        None => return RpcResponse::err(id, -32602, "Missing id".into()),
    };

    let store = state.binary_store.lock().await;
    match store.get_fact(fact_id) {
        Ok(Some(fact)) => RpcResponse::ok(id, serde_json::to_value(&fact).unwrap_or_default()),
        Ok(None) => RpcResponse::err(id, -32001, "Fact not found".into()),
        Err(e) => RpcResponse::err(id, -32010, format!("store.get failed: {}", e)),
    }
}

/// store.update_weight { id, weight } → { ok }
async fn handle_store_update_weight(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let fact_id = match params.get("id").and_then(|v| v.as_u64()) {
        Some(i) => i,
        None => return RpcResponse::err(id, -32602, "Missing id".into()),
    };
    let weight = match params.get("weight").and_then(|v| v.as_f64()) {
        Some(w) => w as f32,
        None => return RpcResponse::err(id, -32602, "Missing weight".into()),
    };

    let mut store = state.binary_store.lock().await;
    match store.update_weight(fact_id, weight) {
        Ok(ok) => RpcResponse::ok(id, serde_json::json!({ "ok": ok })),
        Err(e) => RpcResponse::err(id, -32010, format!("store.update_weight failed: {}", e)),
    }
}

/// store.remove { id } → { ok }
async fn handle_store_remove(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let fact_id = match params.get("id").and_then(|v| v.as_u64()) {
        Some(i) => i,
        None => return RpcResponse::err(id, -32602, "Missing id".into()),
    };

    let mut store = state.binary_store.lock().await;
    match store.remove_fact(fact_id) {
        Ok(ok) => RpcResponse::ok(id, serde_json::json!({ "ok": ok })),
        Err(e) => RpcResponse::err(id, -32010, format!("store.remove failed: {}", e)),
    }
}

/// store.count {} → { count }
async fn handle_store_count(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let store = state.binary_store.lock().await;
    match store.count() {
        Ok(count) => RpcResponse::ok(id, serde_json::json!({ "count": count })),
        Err(e) => RpcResponse::err(id, -32010, format!("store.count failed: {}", e)),
    }
}

// ---------------------------------------------------------------------------
// Cognitive Fabric RPC handlers
// ---------------------------------------------------------------------------

/// fabric.think { text } → ThinkResult
async fn handle_fabric_think(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let mut fabric = state.fabric.lock().await;
    let result = fabric.think(text);
    RpcResponse::ok(id, serde_json::to_value(&result).unwrap_or_default())
}

/// fabric.learn { text } → LearnResult
async fn handle_fabric_learn(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let mut fabric = state.fabric.lock().await;
    let result = fabric.learn(text);
    RpcResponse::ok(id, serde_json::to_value(&result).unwrap_or_default())
}

/// fabric.learn_symbol { name } → { node_id }
async fn handle_fabric_learn_symbol(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let name = match params.get("name").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing name".into()),
    };
    let mut fabric = state.fabric.lock().await;
    let node_id = fabric.learn_symbol(name);
    RpcResponse::ok(id, serde_json::json!({ "node_id": node_id }))
}

/// fabric.train { input, target, lr? } → { loss }
async fn handle_fabric_train(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let input = match params.get("input").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing input".into()),
    };
    let target = match params.get("target").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing target".into()),
    };
    let lr = params.get("lr").and_then(|v| v.as_f64()).unwrap_or(0.01) as f32;
    let mut fabric = state.fabric.lock().await;
    let loss = fabric.train_step(input, target, lr);
    RpcResponse::ok(id, serde_json::json!({ "loss": loss }))
}

/// fabric.status {} → FabricStatus
async fn handle_fabric_status(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let fabric = state.fabric.lock().await;
    let status = fabric.status();
    RpcResponse::ok(id, serde_json::to_value(&status).unwrap_or_default())
}

// ---------------------------------------------------------------------------
// Knowledge Knot Graph RPC handlers
// ---------------------------------------------------------------------------

/// knot.search { text, top_k? } → { results: [(node_id, similarity)] }
async fn handle_knot_search(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let top_k = params.get("top_k").and_then(|v| v.as_u64()).unwrap_or(5) as usize;
    let mut fabric = state.fabric.lock().await;
    let embedding = fabric.neural.embed(text);
    let results = fabric.knot_graph.search_by_embedding(&embedding.vector, top_k);
    let results_json: Vec<serde_json::Value> = results.iter().map(|(nid, sim)| {
        let node = fabric.knot_graph.get_node(*nid);
        serde_json::json!({
            "node_id": nid,
            "similarity": sim,
            "text": node.map(|n| n.text.as_str()).unwrap_or(""),
        })
    }).collect();
    RpcResponse::ok(id, serde_json::json!({ "results": results_json }))
}

/// knot.path { from, to } → TraversalResult
async fn handle_knot_path(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let from = match params.get("from").and_then(|v| v.as_u64()) {
        Some(n) => n,
        None => return RpcResponse::err(id, -32602, "Missing from".into()),
    };
    let to = match params.get("to").and_then(|v| v.as_u64()) {
        Some(n) => n,
        None => return RpcResponse::err(id, -32602, "Missing to".into()),
    };
    let fabric = state.fabric.lock().await;
    match fabric.knot_graph.find_path(from, to) {
        Some(result) => RpcResponse::ok(id, serde_json::to_value(&result).unwrap_or_default()),
        None => RpcResponse::ok(id, serde_json::json!({ "path": null, "reason": "no path found" })),
    }
}

/// knot.stats {} → KnotGraphStats
async fn handle_knot_stats(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let fabric = state.fabric.lock().await;
    let stats = fabric.knot_graph.stats();
    RpcResponse::ok(id, serde_json::to_value(&stats).unwrap_or_default())
}

/// knot.contradict { node_a, node_b, intensity } → { edge_idx }
async fn handle_knot_contradict(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let node_a = match params.get("node_a").and_then(|v| v.as_u64()) {
        Some(n) => n,
        None => return RpcResponse::err(id, -32602, "Missing node_a".into()),
    };
    let node_b = match params.get("node_b").and_then(|v| v.as_u64()) {
        Some(n) => n,
        None => return RpcResponse::err(id, -32602, "Missing node_b".into()),
    };
    let intensity = params.get("intensity").and_then(|v| v.as_f64()).unwrap_or(0.8) as f32;
    let mut fabric = state.fabric.lock().await;
    fabric.record_contradiction(node_a, node_b, intensity);
    RpcResponse::ok(id, serde_json::json!({ "ok": true }))
}

// ---------------------------------------------------------------------------
// LLM Bridge RPC handlers
// ---------------------------------------------------------------------------

/// llm.embed { text } → { vector, source, model, dim }
async fn handle_llm_embed(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let mut bridge = state.llm_bridge.lock().await;
    let emb = bridge.embed(text);
    RpcResponse::ok(id, serde_json::json!({
        "vector": emb.vector,
        "source": format!("{:?}", emb.source),
        "model": emb.model,
        "dim": emb.dim,
    }))
}

/// llm.distill { facts: [{text, embedding, confidence, source_prompt}] } → DistillationResult
async fn handle_llm_distill(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let facts_arr = match params.get("facts").and_then(|v| v.as_array()) {
        Some(a) => a,
        None => return RpcResponse::err(id, -32602, "Missing facts array".into()),
    };
    let lr = params.get("lr").and_then(|v| v.as_f64()).unwrap_or(0.01) as f32;

    let facts: Vec<DistilledFact> = facts_arr.iter().filter_map(|f| {
        let text = f.get("text")?.as_str()?.to_string();
        let embedding: Vec<f32> = f.get("embedding")?.as_array()?
            .iter().filter_map(|v| v.as_f64().map(|x| x as f32)).collect();
        let confidence = f.get("confidence").and_then(|v| v.as_f64()).unwrap_or(1.0) as f32;
        let source_prompt = f.get("source_prompt").and_then(|v| v.as_str())
            .unwrap_or("").to_string();
        Some(DistilledFact { text, embedding, confidence, source_prompt })
    }).collect();

    let mut bridge = state.llm_bridge.lock().await;
    let mut fabric = state.fabric.lock().await;
    let fab = &mut *fabric;
    let result = bridge.distill(&facts, &mut fab.knot_graph, &mut fab.adapter, lr);
    RpcResponse::ok(id, serde_json::to_value(&result).unwrap_or_default())
}

/// llm.status {} → BridgeStats
async fn handle_llm_status(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let bridge = state.llm_bridge.lock().await;
    RpcResponse::ok(id, serde_json::to_value(bridge.stats()).unwrap_or_default())
}

// ---------------------------------------------------------------------------
// Hyperdimensional Engine handlers
// ---------------------------------------------------------------------------

/// hd.teach { text } → { sentences_processed, vocabulary_size }
async fn handle_hd_teach(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let mut fabric = state.fabric.lock().await;
    fabric.teach(text);
    let stats = fabric.hd_stats();
    RpcResponse::ok(id, serde_json::json!({
        "sentences_processed": stats.sentences_processed,
        "vocabulary_size": stats.vocabulary_size,
        "semantic_vocabulary_size": stats.semantic_vocabulary_size,
    }))
}

/// hd.embed { text } → { vector (truncated to cog_dim), dim, backend }
async fn handle_hd_embed(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let text = match params.get("text").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing text".into()),
    };
    let mut fabric = state.fabric.lock().await;
    let cog_dim = fabric.config.cog_dim;
    let result = fabric.hd.embed(text, cog_dim);
    RpcResponse::ok(id, serde_json::json!({
        "vector": result.cog_vector,
        "dim": result.dim,
        "backend": format!("{:?}", result.backend),
    }))
}

/// hd.similarity { word_a, word_b } → { similarity }
async fn handle_hd_similarity(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let word_a = match params.get("word_a").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing word_a".into()),
    };
    let word_b = match params.get("word_b").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing word_b".into()),
    };
    let fabric = state.fabric.lock().await;
    match fabric.word_similarity(word_a, word_b) {
        Some(sim) => RpcResponse::ok(id, serde_json::json!({ "similarity": sim })),
        None => RpcResponse::ok(id, serde_json::json!({
            "similarity": null,
            "error": "One or both words not yet learned"
        })),
    }
}

/// hd.most_similar { word, top_k? } → { results: [{word, similarity}] }
async fn handle_hd_most_similar(
    state: &KernelState,
    params: serde_json::Value,
    id: serde_json::Value,
) -> RpcResponse {
    let word = match params.get("word").and_then(|v| v.as_str()) {
        Some(s) => s,
        None => return RpcResponse::err(id, -32602, "Missing word".into()),
    };
    let top_k = params.get("top_k").and_then(|v| v.as_u64()).unwrap_or(5) as usize;
    let fabric = state.fabric.lock().await;
    let results: Vec<serde_json::Value> = fabric.most_similar(word, top_k)
        .into_iter()
        .map(|(w, s)| serde_json::json!({ "word": w, "similarity": s }))
        .collect();
    RpcResponse::ok(id, serde_json::json!({ "results": results }))
}

/// hd.stats {} → HDEngineStats
async fn handle_hd_stats(
    state: &KernelState,
    id: serde_json::Value,
) -> RpcResponse {
    let fabric = state.fabric.lock().await;
    let stats = fabric.hd_stats();
    RpcResponse::ok(id, serde_json::to_value(&stats).unwrap_or_default())
}
