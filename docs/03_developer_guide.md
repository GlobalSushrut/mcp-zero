# MCP-ZERO Developer Guide

## Introduction

This guide provides comprehensive information for developers working with the MCP-ZERO infrastructure. It covers agent development, using the SDK, extending the system with plugins, and best practices for sustainable development.

## Development Environment Setup

### Required Tools

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install Rust for plugin development
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source $HOME/.cargo/env

# Install WASM toolkit for plugin development
curl https://get.wasmer.io -sSfL | sh

# Install Go for RPC layer extensions
wget https://golang.org/dl/go1.18.linux-amd64.tar.gz
sudo tar -C /usr/local -xzf go1.18.linux-amd64.tar.gz
export PATH=$PATH:/usr/local/go/bin
```

### IDE Configuration

We recommend using Visual Studio Code with the following extensions:
- Python extension
- Rust Analyzer
- Go extension
- WebAssembly extension
- MongoDB extension

## MCP-ZERO SDK Usage

The Python SDK is the primary interface for agent development:

```python
from mcp_zero.sdk import Agent, Plugin, Agreement

# Create a new agent
agent = Agent.spawn()

# Attach capabilities
agent.attach_plugin("data_processing")
agent.attach_plugin("natural_language")

# Execute agent tasks
result = agent.execute("process_text", {"text": "Hello, world!"})

# Create a snapshot
snapshot_id = agent.snapshot()

# Recover from snapshot if needed
agent.recover(snapshot_id)
```

## Agent Lifecycle

Agents in MCP-ZERO follow a well-defined lifecycle:

1. **Spawn**: Create a new agent instance with a unique ID
2. **Configure**: Set parameters and constraints for the agent
3. **Attach Plugins**: Add capabilities through the plugin system
4. **Execute**: Run agent operations with traceable execution
5. **Snapshot**: Create restore points for agent state
6. **Update**: Modify agent configuration (within immutability rules)
7. **Recover**: Restore agent state from snapshots
8. **Terminate**: Remove the agent and clean up resources

## Plugin Development

Plugins extend agent capabilities while respecting the immutable core principles:

```rust
// Sample plugin in Rust
#[mcp_plugin]
pub struct DataProcessingPlugin {
    config: PluginConfig
}

#[mcp_methods]
impl DataProcessingPlugin {
    pub fn process_text(&self, text: String) -> Result<String, PluginError> {
        // Processing logic here
        Ok(processed_text)
    }
}

// Compile to WASM with signed ABI
mcp_build::build(|config| {
    config.plugin("data_processing")
        .version("1.0.0")
        .capability("text_processing")
        .signature_key(env!("PLUGIN_SIGNING_KEY"))
});
```

## Agreement Integration

Agents must operate within properly signed agreements:

```python
from mcp_zero.sdk import Agreement
from mcp_zero.billing import BillingPlan

# Create a new agreement for resource access
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

# Sign the agreement
agreement.sign(consumer_key="consumer_signing_key")

# Use the agreement for agent operations
agent.set_agreement(agreement.id)
result = agent.execute("process_text", {"text": "Hello, world!"})
```

## Mesh Network Integration

Connect agents to the mesh network for resource discovery and sharing:

```python
from mcp_zero.sdk import Agent
from mcp_zero.mesh import MeshNetwork

# Connect agent to mesh network
mesh = MeshNetwork()
mesh.connect()

# Register agent as a resource
mesh.register_agent_resource(
    agent_id=agent.id,
    capabilities=["data_processing", "natural_language"],
    constraints={"cpu": 0.1, "memory": 256}
)

# Discover resources on the network
resources = mesh.query_resources(resource_type="agent", 
                               capabilities=["image_processing"])

# Create agreement with remote resource
if resources:
    remote_agent = resources[0]
    agreement = Agreement.create(
        consumer_id=agent.id,
        provider_id=remote_agent["id"],
        resource_id=remote_agent["id"],
        template="peer_to_peer"
    )
    
    # Execute operation on remote agent
    result = agent.execute_remote(
        agent_id=remote_agent["id"],
        method="process_image",
        params={"image_url": "https://example.com/image.jpg"},
        agreement_id=agreement.id
    )
```

## Tracing and Verification

Every operation is traceable and verifiable:

```python
from mcp_zero.sdk import Agent
from mcp_zero.trace import VerificationProof

# Execute agent operation
result = agent.execute("process_text", {"text": "Hello, world!"})

# Get trace of the execution
trace = agent.get_operation_trace(result.operation_id)

# Verify execution trace
proof = VerificationProof.from_trace(trace)
is_valid = proof.verify()

# Output verification information
if is_valid:
    print("Operation verified successfully")
    print(f"ZK Proof: {proof.zk_proof_id}")
else:
    print("Operation verification failed")
```

## Security Best Practices

1. **Always use signed plugins**: Never use unsigned plugins in production
2. **Validate agreements**: Ensure agreements are properly signed before execution
3. **Constrain resources**: Set appropriate CPU and memory constraints
4. **Enable tracing**: Always keep tracing enabled for verifiability
5. **Regular snapshots**: Create periodic snapshots for critical agents
6. **Principle of least privilege**: Only attach necessary plugins
7. **Validate inputs**: Always validate agent inputs to prevent injection attacks
8. **Secure keys**: Keep signing keys in secure key storage
9. **Monitor usage**: Track agent resource usage for anomalies
10. **Update dependencies**: Keep all dependencies updated to latest secure versions

## Testing Framework

```python
import unittest
from mcp_zero.sdk import Agent
from mcp_zero.test import AgentTestCase

class MyAgentTest(AgentTestCase):
    def setUp(self):
        self.agent = Agent.spawn()
        self.agent.attach_plugin("data_processing")
        
    def test_text_processing(self):
        result = self.agent.execute("process_text", {"text": "Hello, world!"})
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "success")
        
    def tearDown(self):
        self.agent.terminate()

if __name__ == '__main__':
    unittest.main()
```

## Debugging

MCP-ZERO provides extensive debugging tools:

```python
from mcp_zero.sdk import Agent
from mcp_zero.debug import AgentDebugger

# Create debugger for agent
debugger = AgentDebugger(agent_id="agent123")

# Capture execution trace
with debugger.trace_execution():
    result = agent.execute("process_text", {"text": "Hello, world!"})

# View execution details
print(debugger.last_execution_trace)

# Replay execution with modified inputs
replay_result = debugger.replay_execution(
    operation_id=result.operation_id,
    modified_inputs={"text": "Modified input"}
)

# Compare executions
debugger.compare_executions(result.operation_id, replay_result.operation_id)
```

## Performance Optimization

1. **Minimize plugin switching**: Group operations by plugin
2. **Use efficient data structures**: Prefer binary formats for data exchange
3. **Implement caching**: Cache results of frequent operations
4. **Optimize memory usage**: Release resources when not needed
5. **Use async operations**: For I/O-bound operations
6. **Batch operations**: Group related operations for efficiency
7. **Profile regularly**: Use the built-in profiler to identify bottlenecks

## Further Resources

- [API Reference](04_api_reference.md)
- [Plugin System](08_plugin_system.md)
- [Agreement Templates](11_agreement_templates.md)
- [Trace Engine](12_trace_engine.md)
- [Performance Guide](16_performance_guide.md)
- [Security Model](17_security_model.md)
