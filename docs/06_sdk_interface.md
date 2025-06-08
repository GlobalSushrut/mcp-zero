# MCP-ZERO SDK Interface

## Overview

The MCP-ZERO SDK Interface provides a Python-based developer interface to interact with the underlying Rust and C++ kernel. It abstracts the low-level details of the system while exposing the full power of the platform in a developer-friendly manner.

## Core Principles

1. **Simplicity**: Easy to learn and use for developers of all skill levels
2. **Completeness**: Exposes the full functionality of the MCP-ZERO system
3. **Safety**: Prevents common errors and enforces best practices
4. **Performance**: Thin layer with minimal overhead
5. **Cross-platform**: Works consistently across all supported platforms

## SDK Architecture

```
┌─────────────────────────────────────────────────┐
│               Application Code                  │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│               Python SDK Interface              │
│                                                 │
├───────────────┬───────────────┬─────────────────┤
│ Agent Interface│ Agreement API │ Resource API    │
├───────────────┼───────────────┼─────────────────┤
│ Plugin Manager│  Mesh Client  │  Trace Client   │
├───────────────┴───────────────┴─────────────────┤
│                                                 │
│             Native Extension Layer              │
│                                                 │
├─────────────────────────────────────────────────┤
│                                                 │
│                  MCP-ZERO Kernel                │
│                                                 │
└─────────────────────────────────────────────────┘
```

## Installation

The MCP-ZERO SDK can be installed via pip:

```bash
pip install mcp-zero-sdk
```

Or directly from source:

```bash
git clone https://github.com/your-org/mcp-zero-sdk.git
cd mcp-zero-sdk
pip install -e .
```

## Core Components

### Agent Interface

The Agent Interface provides methods to interact with MCP-ZERO agents:

```python
from mcp_zero.sdk import Agent

# Create a new agent
agent = Agent.spawn(constraints={"cpu": 0.1, "memory": 256})

# Attach plugins to the agent
agent.attach_plugin("data_processing")
agent.attach_plugin("natural_language")

# Execute a method on the agent
result = agent.execute("process_text", {"text": "Hello, world!"})
print(result)

# Create a snapshot of the agent's state
snapshot_id = agent.snapshot()

# Recover the agent from a snapshot
agent.recover(snapshot_id)

# Terminate the agent when done
agent.terminate()
```

### Agreement API

The Agreement API manages resource allocation agreements:

```python
from mcp_zero.sdk import Agreement

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
    }
)

# Sign the agreement as a consumer
agreement.sign(consumer_key="consumer_signing_key")

# Check if the agreement is valid for an operation
is_valid = agreement.validate_for_operation(
    resource_id="text_processing_service",
    operation="process_text"
)

# Record usage against the agreement
agreement.record_usage(metric="requests_per_day", quantity=1)
```

### Plugin Manager

The Plugin Manager handles plugin discovery, loading, and management:

```python
from mcp_zero.sdk import PluginManager

# Initialize the plugin manager
plugin_manager = PluginManager()

# List available plugins
available_plugins = plugin_manager.list_plugins()

# Get plugin details
plugin_details = plugin_manager.get_plugin_info("data_processing")

# Upload a new plugin
with open("my_plugin.wasm", "rb") as f:
    plugin_data = f.read()

plugin_manager.upload_plugin(
    plugin_id="my_plugin",
    plugin_data=plugin_data,
    metadata={
        "version": "1.0.0",
        "capabilities": ["data_transformation"]
    },
    signature="abcdef123456"
)
```

### Mesh Client

The Mesh Client enables interaction with the P2P mesh network:

```python
from mcp_zero.sdk import MeshNetwork

# Initialize the mesh network client
mesh = MeshNetwork()
mesh.connect()

# Add bootstrap peers
mesh.add_bootstrap_peer("ws://peer1.example.com:8765")

# Register agent as a resource
mesh.register_agent_resource(
    agent_id="agent123",
    capabilities=["data_processing", "natural_language"],
    constraints={"cpu": 0.1, "memory": 256}
)

# Query for resources
resources = mesh.query_resources(
    resource_type="agent",
    capabilities=["image_processing"]
)

# Execute a method on a remote agent
if resources:
    remote_agent_id = resources[0]["resource_id"]
    result = mesh.execute_remote_agent(
        agent_id=remote_agent_id,
        method="process_image",
        params={"image_url": "https://example.com/image.jpg"}
    )
```

### Trace Client

The Trace Client provides access to the ZK-traceable auditing system:

```python
from mcp_zero.sdk import TraceClient

# Initialize the trace client
trace_client = TraceClient()

# Get a specific trace
trace = trace_client.get_trace("trace123")

# Verify a trace
verification_result = trace_client.verify_trace("trace123")

# Generate a ZK proof for a trace
proof = trace_client.generate_proof("trace123")

# Export traces for a time range
traces = trace_client.export_traces(
    start_time="2025-06-01T00:00:00Z",
    end_time="2025-06-07T23:59:59Z"
)
```

## Agent Lifecycle Management

The SDK provides a complete interface for agent lifecycle management:

```python
from mcp_zero.sdk import Agent

# 1. Spawn a new agent
agent = Agent.spawn(constraints={"cpu": 0.1, "memory": 256})

# 2. Configure the agent
agent.configure(name="text_processor", description="Processes text input")

# 3. Attach plugins for capabilities
agent.attach_plugin("data_processing")
agent.attach_plugin("natural_language")

# 4. Execute agent operations
result = agent.execute("process_text", {"text": "Hello, world!"})

# 5. Create a snapshot for later recovery
snapshot_id = agent.snapshot()

# 6. Create agreement for resource sharing
agreement = agent.create_agreement(
    consumer_id="user123",
    resource_id=agent.id,
    template="standard"
)

# 7. Recover from a snapshot if needed
agent.recover(snapshot_id)

# 8. Terminate the agent when done
agent.terminate()
```

## Error Handling

The SDK provides structured error handling:

```python
from mcp_zero.sdk import Agent
from mcp_zero.sdk.errors import AgentError, PluginError, AgreementError

try:
    agent = Agent.spawn()
    agent.attach_plugin("nonexistent_plugin")
except AgentError as e:
    print(f"Agent error: {e}")
except PluginError as e:
    print(f"Plugin error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Configuration

The SDK can be configured through environment variables or a configuration file:

```python
from mcp_zero.sdk import configure

# Configure the SDK programmatically
configure(
    api_key="your-api-key",
    api_endpoint="https://api.mcp-zero.org/v1",
    trace_enabled=True,
    max_retries=3,
    timeout=30
)
```

Or through environment variables:

```bash
export MCP_API_KEY="your-api-key"
export MCP_API_ENDPOINT="https://api.mcp-zero.org/v1"
export MCP_TRACE_ENABLED=true
export MCP_MAX_RETRIES=3
export MCP_TIMEOUT=30
```

## Advanced Features

### Batch Operations

```python
from mcp_zero.sdk import Agent

agent = Agent.spawn()
agent.attach_plugin("data_processing")

# Process multiple items in batch
results = agent.execute_batch("process_text", [
    {"text": "Hello, world!"},
    {"text": "Processing batch items"},
    {"text": "Efficient execution"}
])
```

### Event Subscriptions

```python
from mcp_zero.sdk import Agent

def on_execution_complete(event):
    print(f"Execution completed: {event['operation_id']}")
    print(f"Result: {event['result']}")

agent = Agent.spawn()
agent.subscribe("execution_complete", on_execution_complete)

# Events will trigger the callback
agent.execute("process_text", {"text": "This will trigger an event"})
```

### Async Operations

```python
import asyncio
from mcp_zero.sdk.async_api import AsyncAgent

async def main():
    agent = await AsyncAgent.spawn()
    await agent.attach_plugin("data_processing")
    
    # Execute operations concurrently
    tasks = [
        agent.execute("process_text", {"text": "Concurrent task 1"}),
        agent.execute("process_text", {"text": "Concurrent task 2"}),
        agent.execute("process_text", {"text": "Concurrent task 3"})
    ]
    
    results = await asyncio.gather(*tasks)
    print(results)
    
    await agent.terminate()

asyncio.run(main())
```

## Resource Management

The SDK ensures proper resource cleanup:

```python
from mcp_zero.sdk import Agent

# Using context manager for automatic cleanup
with Agent.spawn() as agent:
    agent.attach_plugin("data_processing")
    result = agent.execute("process_text", {"text": "Hello, world!"})
    print(result)
    # Agent is automatically terminated when exiting the context
```

## Logging and Monitoring

```python
import logging
from mcp_zero.sdk import configure

# Configure SDK logging
configure(log_level=logging.DEBUG)

# Get the SDK logger
logger = logging.getLogger("mcp_zero.sdk")
logger.setLevel(logging.DEBUG)

# Add custom handler
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)
```

## SDK Extension

The SDK can be extended with custom functionality:

```python
from mcp_zero.sdk import Agent, plugin_decorator

# Create a custom plugin decorator
@plugin_decorator
def my_custom_plugin(agent):
    # Attach standard plugins
    agent.attach_plugin("data_processing")
    agent.attach_plugin("natural_language")
    
    # Return extended functionality
    return {
        "combined_process": lambda text: agent.execute(
            "process_text", {"text": text, "advanced": True}
        )
    }

# Use the custom plugin
agent = Agent.spawn()
agent.use(my_custom_plugin)

# Use the extended functionality
result = agent.combined_process("Process this text")
```

## Performance Considerations

1. **Reuse Agent Instances**: Create agents once and reuse them
2. **Batch Operations**: Use batch methods for multiple operations
3. **Connection Pooling**: The SDK uses connection pooling automatically
4. **Async API**: Use async API for concurrent operations
5. **Resource Limits**: Be mindful of resource constraints (CPU <27%, RAM <827MB)

## Security Best Practices

1. **API Key Protection**: Store API keys securely
2. **Verify Plugins**: Only use verified and signed plugins
3. **Agreement Validation**: Always validate agreements before operations
4. **Audit Traces**: Regularly review operation traces
5. **Principle of Least Privilege**: Only attach necessary plugins

## Further Reading

- [API Reference](04_api_reference.md)
- [Developer Guide](03_developer_guide.md)
- [Plugin System](08_plugin_system.md)
- [Agreement Templates](11_agreement_templates.md)
- [Security Model](17_security_model.md)
