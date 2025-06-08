# MCP-ZERO Python SDK

A production-grade AI Agent Infrastructure SDK with extremely efficient resource usage.

## Overview

MCP-ZERO is a foundational infrastructure for AI agents with an immutable core designed for 100+ year sustainability. It provides a comprehensive framework for spawning, managing, and orchestrating AI agents with built-in:

- Strict hardware constraints (under 1GB RAM, under 30% CPU on an i3 processor)
- Ethical governance
- Modular plugin architecture
- Zero-Knowledge provable execution
- Cryptographic integrity

## Installation

```bash
# Install from source
cd /path/to/mcp_zero/src/sdk/python
pip install -e .

# Or via pip (when published)
pip install mcp-zero
```

## Quick Start

```python
from mcp_zero import MCPClient, AgentConfig

# Connect to MCP-ZERO server
client = MCPClient(host="localhost", port=50051)

# Spawn a new agent
config = AgentConfig(
    name="my-agent",
    entry_plugin="core",
    intents=["calculate", "store", "retrieve"]
)
agent = client.spawn_agent(config)

# Attach plugin
agent.attach_plugin("math")

# Execute intent
result = agent.execute("calculate", {"operation": "add", "values": [1, 2, 3]})
print(f"Result: {result}")

# Take snapshot
snapshot_id = agent.snapshot()

# Later, recover from snapshot
agent.recover(snapshot_id)
```

## CLI Usage

The SDK includes a comprehensive command-line interface:

```bash
# Initialize configuration
mcp-zero init

# List available agents
mcp-zero agent list

# Spawn a new agent
mcp-zero agent spawn config.yaml

# Execute intent on agent
mcp-zero agent-ops execute agent-123 calculate --param operation=add --param values=[1,2,3]

# Register a plugin
mcp-zero plugin register plugin-config.yaml

# Check system status
mcp-zero system status

# Monitor resources
mcp-zero system resources --watch
```

## Architecture

MCP-ZERO follows a strict layered architecture:

- **Kernel**: Core system in Rust + C++
- **SDK Interface**: Python (this package)
- **RPC Layer**: Go-based service layer
- **Trace Engine**: Poseidon+ZKSync for traceable execution
- **Plugin ABI**: WebAssembly with signed ABI

## Hardware Requirements

MCP-ZERO is designed to operate within strict hardware constraints:

- CPU: <27% of a single-core i3 (2.4GHz)
- RAM: Peak 827MB, Average 640MB

## Agent Lifecycle

1. `agent.spawn()` → Creates agent ID, signs root
2. `agent.attach_plugin()` → Loads sandboxed capabilities
3. `agent.execute()` → Traceable, failsafe execution
4. `agent.snapshot()` → Auto runtime snapshots
5. `agent.recover()` → Recovers full state

## Documentation

For detailed API documentation, run:

```bash
# Generate documentation
cd /path/to/mcp_zero/src/sdk/python
pdoc --html --output-dir docs mcp_zero
```

Then open `docs/mcp_zero/index.html` in your browser.

## License

Copyright © 2025 Windsurf Engineering
All rights reserved.
