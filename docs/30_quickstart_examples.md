# Quick Start Examples

## Overview

This guide provides practical examples to help you quickly get started with MCP-ZERO. Each example includes complete code and explanations.

## Prerequisites

- Python 3.9+
- MCP-ZERO SDK installed (`pip install mcp-zero-sdk`)
- API key for MCP-ZERO

## Example 1: Create Your First Agent

```python
# simple_agent.py
from mcp_zero.sdk import Agent, configure

# Configure SDK with your API key
configure(api_key="your_api_key_here")

# Create a new agent
agent = Agent.spawn(
    constraints={"cpu": 0.1, "memory": 64}  # Uses 10% of single core, 64MB RAM
)
print(f"Agent created with ID: {agent.id}")

# Attach a standard plugin
agent.attach_plugin("echo")

# Execute a simple operation
result = agent.execute("echo", {"message": "Hello, MCP-ZERO!"})
print(f"Result: {result}")

# Terminate agent when done
agent.terminate()
```

Run the example:

```bash
python simple_agent.py
```

## Example 2: Working with Plugins

```python
# plugin_example.py
from mcp_zero.sdk import Agent, Plugin, configure, export

configure(api_key="your_api_key_here")

# Create a custom plugin
class MathPlugin(Plugin):
    @export
    def add(self, params):
        """Add two numbers"""
        return params["a"] + params["b"]
    
    @export
    def multiply(self, params):
        """Multiply two numbers"""
        return params["a"] * params["b"]

# Build the plugin
plugin_path = MathPlugin.build("math_plugin")
print(f"Plugin built at: {plugin_path}")

# Create an agent and attach the plugin
agent = Agent.spawn()
agent.attach_plugin_file(plugin_path)

# Use the plugin
result1 = agent.execute("add", {"a": 5, "b": 3})
result2 = agent.execute("multiply", {"a": 5, "b": 3})

print(f"5 + 3 = {result1}")
print(f"5 * 3 = {result2}")
```

## Example 3: Agent State Management

```python
# state_management.py
from mcp_zero.sdk import Agent, configure
import json

configure(api_key="your_api_key_here")

# Create an agent with state
agent = Agent.spawn()
agent.attach_plugin("state_manager")

# Set some state
agent.execute("set_state", {"key": "counter", "value": 0})
agent.execute("set_state", {"key": "user", "value": "Alice"})

# Create a snapshot
snapshot_id = agent.snapshot()
print(f"Created snapshot: {snapshot_id}")

# Modify state
agent.execute("set_state", {"key": "counter", "value": 10})

# Export state
current_state = agent.export_state()
print(f"Current state: {json.dumps(current_state, indent=2)}")

# Recover from snapshot
agent.recover(snapshot_id)
recovered_value = agent.execute("get_state", {"key": "counter"})
print(f"Recovered counter value: {recovered_value}")  # Should be 0
```

## Example 4: Working with Mesh Network

```python
# mesh_example.py
from mcp_zero.sdk import Agent, configure
from mcp_zero.mesh import MeshClient

configure(api_key="your_api_key_here")

# Connect to mesh network
mesh = MeshClient()
mesh.connect()

# Register our local agent as a mesh resource
agent = Agent.spawn()
agent.attach_plugin("image_processor")

# Register on mesh
mesh.register_resource(
    resource_id=agent.id,
    resource_type="agent",
    capabilities=["image_processing"],
    metadata={"version": "1.0"}
)

# Discover resources on the mesh
image_processors = mesh.query_resources(
    resource_type="agent",
    capabilities=["image_processing"]
)

print(f"Found {len(image_processors)} image processing resources")
for resource in image_processors:
    print(f"ID: {resource['resource_id']}")
    print(f"Location: {resource['location']}")
    print(f"Capabilities: {', '.join(resource['capabilities'])}")
    print()
```

## Example 5: Working with Agreements

```python
# agreement_example.py
from mcp_zero.sdk import Agent, Agreement, configure
from datetime import datetime, timedelta

configure(api_key="your_api_key_here")

# Create consumer and provider agents
consumer = Agent.spawn()
provider = Agent.spawn()
provider.attach_plugin("data_processor")

# Create an agreement
agreement = Agreement.create(
    consumer_id=consumer.id,
    provider_id=provider.id,
    template="standard",
    terms={
        "max_calls": 100,
        "max_cpu": 0.2,
        "max_memory": 100,
        "expiration": (datetime.now() + timedelta(days=1)).isoformat()
    }
)

print(f"Agreement created with ID: {agreement.id}")

# Consumer uses provider via agreement
result = consumer.execute_via_agreement(
    agreement_id=agreement.id,
    method="process_data",
    params={"input": "raw data"}
)

print(f"Result: {result}")

# Check agreement usage
usage = agreement.get_usage()
print(f"Calls used: {usage['calls']} of {usage['max_calls']}")
```

## Running the Examples

1. Save each example to a separate file
2. Replace `"your_api_key_here"` with your actual API key
3. Run with Python: `python example_file.py`

## Next Steps

- Review the [Architecture Overview](02_architecture_overview.md)
- Explore the [Developer Guide](03_developer_guide.md)
- Check the [API Reference](04_api_reference.md)
- Learn about [Security Model](17_security_model.md)

## Troubleshooting

- Ensure MCP-ZERO daemon is running: `mcp-zero-daemon status`
- Check API key is correctly configured
- Verify network connectivity for mesh examples
- See [Troubleshooting Guide](24_troubleshooting.md) for more help
