# MCP-ZERO API Reference

## Introduction

This document provides a comprehensive reference for all APIs exposed by the MCP-ZERO infrastructure. It covers REST APIs, SDK methods, and internal interfaces used across the system.

## REST API Endpoints

### Authentication

All API endpoints require authentication via API keys passed in the `X-MCP-API-Key` header.

```
Authorization: Bearer <api_key>
```

### Base URL

```
https://api.mcp-zero.org/v1
```

### Status Endpoint

```
GET /status
```

Returns the current status and version of the MCP-ZERO API.

**Response:**
```json
{
  "status": "ok",
  "version": "v7.0.0",
  "uptime": 1234567,
  "components": {
    "kernel": "ok",
    "trace_engine": "ok",
    "mesh_network": "ok",
    "agreement_system": "ok"
  }
}
```

### Agents

#### Create Agent

```
POST /agents
```

Creates a new agent instance.

**Request:**
```json
{
  "constraints": {
    "cpu": 0.1,
    "memory": 256
  },
  "plugins": ["data_processing", "natural_language"]
}
```

**Response:**
```json
{
  "agent_id": "agent_12345",
  "created_at": "2025-06-07T08:34:43Z",
  "status": "created",
  "plugins": ["data_processing", "natural_language"],
  "trace_id": "trace_67890"
}
```

#### Get Agent

```
GET /agents/{agent_id}
```

Returns information about a specific agent.

**Response:**
```json
{
  "agent_id": "agent_12345",
  "created_at": "2025-06-07T08:34:43Z",
  "status": "active",
  "plugins": ["data_processing", "natural_language"],
  "constraints": {
    "cpu": 0.1,
    "memory": 256
  },
  "agreements": ["agreement_54321"],
  "snapshots": [
    {
      "id": "snapshot_98765",
      "created_at": "2025-06-07T09:34:43Z"
    }
  ]
}
```

#### Execute Agent Method

```
POST /agents/{agent_id}/execute
```

Executes a method on the agent.

**Request:**
```json
{
  "method": "process_text",
  "params": {
    "text": "Hello, world!"
  },
  "agreement_id": "agreement_54321"
}
```

**Response:**
```json
{
  "operation_id": "op_24680",
  "result": {
    "processed_text": "HELLO, WORLD!"
  },
  "status": "success",
  "execution_time": 0.123,
  "trace_id": "trace_13579"
}
```

#### Create Agent Snapshot

```
POST /agents/{agent_id}/snapshots
```

Creates a snapshot of the agent's current state.

**Response:**
```json
{
  "snapshot_id": "snapshot_98765",
  "created_at": "2025-06-07T09:34:43Z",
  "size_bytes": 12345,
  "hash": "sha256:1234567890abcdef..."
}
```

#### Recover Agent

```
POST /agents/{agent_id}/recover
```

Recovers an agent from a snapshot.

**Request:**
```json
{
  "snapshot_id": "snapshot_98765"
}
```

**Response:**
```json
{
  "agent_id": "agent_12345",
  "status": "recovered",
  "snapshot_id": "snapshot_98765",
  "recovery_time": 0.456,
  "trace_id": "trace_97531"
}
```

#### Terminate Agent

```
DELETE /agents/{agent_id}
```

Terminates an agent and releases its resources.

**Response:**
```json
{
  "agent_id": "agent_12345",
  "status": "terminated",
  "termination_time": "2025-06-07T10:34:43Z",
  "trace_id": "trace_86420"
}
```

### Agreements

#### Create Agreement

```
POST /agreements
```

Creates a new agreement between parties.

**Request:**
```json
{
  "template": "standard",
  "consumer_id": "user123",
  "provider_id": "provider456",
  "resource_id": "text_processing_service",
  "terms": {
    "duration_days": 30,
    "usage_limits": {
      "requests_per_day": 1000,
      "compute_units": 5000
    }
  },
  "billing_plan": "standard"
}
```

**Response:**
```json
{
  "agreement_id": "agreement_54321",
  "status": "created",
  "created_at": "2025-06-07T11:34:43Z",
  "expires_at": "2025-07-07T11:34:43Z",
  "signature_required": ["consumer", "provider"]
}
```

#### Sign Agreement

```
POST /agreements/{agreement_id}/sign
```

Signs an agreement.

**Request:**
```json
{
  "signer_id": "user123",
  "signature": "abc123signature"
}
```

**Response:**
```json
{
  "agreement_id": "agreement_54321",
  "status": "signed",
  "signers": ["user123"],
  "pending_signers": ["provider456"]
}
```

#### Get Agreement

```
GET /agreements/{agreement_id}
```

Returns information about a specific agreement.

**Response:**
```json
{
  "agreement_id": "agreement_54321",
  "status": "active",
  "created_at": "2025-06-07T11:34:43Z",
  "activated_at": "2025-06-07T12:34:43Z",
  "expires_at": "2025-07-07T11:34:43Z",
  "consumer_id": "user123",
  "provider_id": "provider456",
  "resource_id": "text_processing_service",
  "terms": {
    "duration_days": 30,
    "usage_limits": {
      "requests_per_day": 1000,
      "compute_units": 5000
    },
    "current_usage": {
      "requests_per_day": 123,
      "compute_units": 456
    }
  },
  "billing_plan": "standard",
  "signatures": {
    "consumer": "abc123signature",
    "provider": "def456signature"
  }
}
```

### Plugins

#### List Available Plugins

```
GET /plugins
```

Lists all available plugins.

**Response:**
```json
{
  "plugins": [
    {
      "id": "data_processing",
      "version": "1.0.0",
      "capabilities": ["text_processing", "data_transformation"],
      "signature": "sha256:abcdef...",
      "constraints": {
        "cpu": 0.05,
        "memory": 128
      }
    },
    {
      "id": "natural_language",
      "version": "2.1.0",
      "capabilities": ["text_generation", "text_classification"],
      "signature": "sha256:123456...",
      "constraints": {
        "cpu": 0.1,
        "memory": 256
      }
    }
  ]
}
```

#### Upload Plugin

```
POST /plugins
```

Uploads a new plugin.

**Request:**
```
Content-Type: multipart/form-data
plugin_file: [binary data]
plugin_metadata: {
  "id": "image_processing",
  "version": "1.0.0",
  "capabilities": ["image_transformation", "image_classification"],
  "constraints": {
    "cpu": 0.15,
    "memory": 384
  }
}
signature: abc123signature
```

**Response:**
```json
{
  "plugin_id": "image_processing",
  "version": "1.0.0",
  "status": "verified",
  "verification_trace": "trace_24680",
  "capabilities": ["image_transformation", "image_classification"]
}
```

### Mesh Network

#### Discover Resources

```
POST /mesh/discover
```

Discovers resources in the mesh network.

**Request:**
```json
{
  "resource_type": "agent",
  "capabilities": ["image_processing"],
  "local_only": false,
  "timeout": 5
}
```

**Response:**
```json
{
  "resources": [
    {
      "resource_id": "agent_abcde",
      "resource_type": "agent",
      "peer_id": "peer_12345",
      "metadata": {
        "capabilities": ["image_processing", "video_processing"],
        "constraints": {
          "cpu": 0.2,
          "memory": 512
        }
      },
      "location": "remote"
    },
    {
      "resource_id": "agent_fghij",
      "resource_type": "agent",
      "metadata": {
        "capabilities": ["image_processing"],
        "constraints": {
          "cpu": 0.15,
          "memory": 384
        }
      },
      "location": "local"
    }
  ]
}
```

#### Register Resource

```
POST /mesh/resources
```

Registers a resource in the mesh network.

**Request:**
```json
{
  "resource_id": "agent_klmno",
  "resource_type": "agent",
  "metadata": {
    "capabilities": ["text_processing"],
    "constraints": {
      "cpu": 0.1,
      "memory": 256
    }
  },
  "signature": "abc123signature"
}
```

**Response:**
```json
{
  "resource_id": "agent_klmno",
  "status": "registered",
  "registration_trace": "trace_13579"
}
```

### Traces

#### Get Trace

```
GET /traces/{trace_id}
```

Returns information about a specific trace.

**Response:**
```json
{
  "trace_id": "trace_13579",
  "timestamp": "2025-06-07T13:34:43Z",
  "node_id": "node_abcde",
  "event_type": "agent_execution",
  "resource_id": "agent_12345",
  "data": {
    "method": "process_text",
    "params": {
      "text": "Hello, world!"
    },
    "result_hash": "sha256:abcdef..."
  },
  "hash": "sha256:123456...",
  "prev_hash": "sha256:789012..."
}
```

#### Verify Trace

```
POST /traces/{trace_id}/verify
```

Verifies the authenticity of a trace.

**Response:**
```json
{
  "trace_id": "trace_13579",
  "verified": true,
  "verification_time": "2025-06-07T14:34:43Z",
  "chain_integrity": "valid",
  "zk_proof": "abc123proof"
}
```

## SDK Methods

### Agent Class

```python
# Create a new agent
agent = Agent.spawn(constraints={"cpu": 0.1, "memory": 256})

# Attach plugins
agent.attach_plugin("data_processing")
agent.attach_plugin("natural_language")

# Execute agent methods
result = agent.execute("process_text", {"text": "Hello, world!"})

# Create a snapshot
snapshot_id = agent.snapshot()

# Recover from snapshot
agent.recover(snapshot_id)

# Terminate agent
agent.terminate()
```

### Agreement Class

```python
# Create a new agreement
agreement = Agreement.create(
    consumer_id="user123",
    provider_id="provider456",
    resource_id="text_processing_service",
    template="standard",
    terms={
        "duration_days": 30,
        "usage_limits": {
            "requests_per_day": 1000,
            "compute_units": 5000
        }
    },
    billing_plan=BillingPlan.STANDARD
)

# Sign agreement
agreement.sign(signer_id="user123", signature="abc123signature")

# Check agreement status
status = agreement.status()

# Get agreement details
details = agreement.details()

# Validate agreement for operation
is_valid = agreement.validate_for_operation(
    resource_id="text_processing_service",
    operation="process_text",
    quantity=1
)

# Record usage
agreement.record_usage(metric="compute_units", quantity=5)
```

### MeshNetwork Class

```python
# Initialize mesh network
mesh = MeshNetwork()
mesh.connect()

# Add bootstrap peers
mesh.add_bootstrap_peer("ws://peer1.example.com:8765")

# Register resources
mesh.register_resource(
    resource_id="agent_12345",
    resource_type="agent",
    metadata={
        "capabilities": ["text_processing"],
        "constraints": {"cpu": 0.1, "memory": 256}
    }
)

# Query resources
resources = mesh.query_resources(
    resource_type="agent",
    metadata_filter={"capabilities": ["image_processing"]},
    local_only=False,
    timeout=5
)

# Connect to peer
connected = mesh.connect_to_peer("ws://peer2.example.com:8765")

# Subscribe to events
mesh.subscribe_to_event("resource_announced", on_resource_announced)
```

## Internal Interfaces

### Kernel Interface

```rust
// Agent lifecycle management
pub fn spawn_agent(constraints: HardwareConstraints) -> AgentId;
pub fn attach_plugin(agent_id: AgentId, plugin_id: PluginId) -> Result<(), AgentError>;
pub fn execute_agent(agent_id: AgentId, method: &str, params: &[u8]) -> Result<Vec<u8>, AgentError>;
pub fn snapshot_agent(agent_id: AgentId) -> Result<SnapshotId, AgentError>;
pub fn recover_agent(agent_id: AgentId, snapshot_id: SnapshotId) -> Result<(), AgentError>;
pub fn terminate_agent(agent_id: AgentId) -> Result<(), AgentError>;
```

### Trace Engine Interface

```rust
// Tracing operations
pub fn trace_event(event_type: &str, resource_id: &str, data: &[u8]) -> TraceId;
pub fn verify_trace(trace_id: TraceId) -> Result<bool, TraceError>;
pub fn generate_proof(trace_id: TraceId) -> Result<ZkProof, TraceError>;
pub fn validate_proof(zk_proof: ZkProof) -> bool;
```

### Plugin ABI Interface

```rust
// Plugin interface
#[no_mangle]
pub extern "C" fn init(config: *const u8, config_len: usize) -> i32;

#[no_mangle]
pub extern "C" fn execute(method: *const u8, method_len: usize, 
                          params: *const u8, params_len: usize,
                          result: *mut u8, result_len: *mut usize) -> i32;

#[no_mangle]
pub extern "C" fn capabilities(result: *mut u8, result_len: *mut usize) -> i32;

#[no_mangle]
pub extern "C" fn cleanup() -> i32;
```

## Error Codes

| Code | Description | HTTP Status |
|------|-------------|------------|
| 1000 | Invalid API key | 401 |
| 1001 | Permission denied | 403 |
| 1002 | Resource not found | 404 |
| 2000 | Agent error | 400 |
| 2001 | Plugin error | 400 |
| 3000 | Agreement error | 400 |
| 4000 | Mesh network error | 400 |
| 5000 | Trace error | 400 |
| 9000 | Internal server error | 500 |

## Rate Limits

| Endpoint | Rate Limit |
|----------|------------|
| POST /agents | 10 per minute |
| POST /agents/{agent_id}/execute | 100 per minute |
| POST /agents/{agent_id}/snapshots | 10 per minute |
| POST /agreements | 10 per minute |
| GET /mesh/discover | 60 per minute |
| Other endpoints | 300 per minute |

## API Versioning

The API version is included in the URL path. For example, `/v1/agents` represents version 1 of the agents API. The current version is `v1`.

## Further Resources

- [Developer Guide](03_developer_guide.md)
- [SDK Interface](06_sdk_interface.md)
- [REST API Examples](24_rest_api_examples.md)
