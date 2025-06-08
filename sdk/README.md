# MCP-ZERO: Minimal Computing Protocol for AI Agents

[![PyPI version](https://img.shields.io/badge/pypi-v1.0.0-blue.svg)](https://pypi.org/project/mcp-zero/)
[![Python Versions](https://img.shields.io/badge/python-3.8%20%7C%203.9%20%7C%203.10-blue)](https://pypi.org/project/mcp-zero/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Documentation](https://img.shields.io/badge/docs-latest-brightgreen.svg)](https://docs.mcp-zero.org)

## Overview

MCP-ZERO provides a production-grade, sustainable foundation for AI agent development with strict resource constraints and built-in ethical governance.

**Core Design Principles:**
- Hardware constraints: <27% CPU (single i3 core), <827MB RAM
- 100+ year sustainability focus
- Immutable core with plugin-based extensibility
- Built-in ethical governance
- Cryptographic integrity and ZK-traceable auditing

## Quick Start

```bash
pip install mcp-zero
```

```python
from mcp_zero import Agent, Plugin

# Create a new agent with minimal footprint
agent = Agent.spawn(name="my-assistant")

# Attach capabilities through plugins
agent.attach_plugin(Plugin.from_registry("conversation"))
agent.attach_plugin(Plugin.from_registry("memory"))

# Execute with ethical governance and resource constraints
response = agent.execute(intent="Respond to user question", 
                         inputs={"question": "What's the weather today?"})

# Create a snapshot for future recovery
snapshot_id = agent.snapshot()

# Later, recover the agent's state
recovered_agent = Agent.recover(snapshot_id)
```

## Features

- **Minimal Resource Usage**: Optimized for edge devices and low-resource environments
- **Plugin Architecture**: Extend capabilities through sandboxed WASM plugins
- **Ethical Governance**: Built-in policy enforcement and auditing
- **State Snapshots**: Save and recover agent state securely
- **Cryptographic Integrity**: Sign and verify all operations
- **Cloud Integration**: Seamlessly connect to MCP-ZERO cloud services

## Hardware Requirements

MCP-ZERO is designed to run on virtually any hardware:

- **Minimum**: Raspberry Pi Zero or equivalent (1GHz single-core)
- **Recommended**: Raspberry Pi 4 or equivalent
- **Cloud**: Works with any cloud provider with minimal resources

## Documentation

For full documentation, visit [docs.mcp-zero.org](https://docs.mcp-zero.org).

## Examples

See the [examples](https://github.com/mcp-zero/sdk/tree/main/examples) directory for sample applications.

## License

MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions that maintain our core principles of minimal resource usage and sustainability are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
