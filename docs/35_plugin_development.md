# MCP-ZERO Plugin Development

## Overview

MCP-ZERO's immutable core design relies on plugins for extensibility. This document covers how to develop, test, and deploy plugins that extend agent capabilities without modifying the core platform.

## Plugin Architecture

Plugins in MCP-ZERO use WASM + Signed ABI for secure, sandboxed execution:

```
┌───────────────────────────────────────────┐
│               MCP-ZERO Core               │
├───────────────────────────────────────────┤
│                Plugin ABI                 │
├───────┬─────────────┬────────────┬───────┤
│Plugin1│   Plugin2   │  Plugin3   │ ...   │
└───────┴─────────────┴────────────┴───────┘
```

## Plugin Types

MCP-ZERO supports several plugin categories:

1. **Capability Plugins**: Add new agent abilities
2. **Integration Plugins**: Connect to external services/APIs
3. **Tool Plugins**: Provide specific task tools
4. **Workflow Plugins**: Define multi-step processes
5. **Domain Plugins**: Add domain-specific knowledge

## Building Your First Plugin

### Plugin Structure

```
plugin-name/
├── manifest.json     # Plugin metadata
├── src/              # Source code
│   └── main.py       # Plugin entry point
├── tests/            # Unit tests
├── wasm/             # WASM build directory
└── README.md         # Documentation
```

### manifest.json Example

```json
{
  "name": "advanced-reasoning",
  "version": "1.0.0",
  "description": "Enhanced reasoning capabilities for MCP-ZERO agents",
  "entry_point": "src.main:initialize",
  "capabilities": ["deductive_reasoning", "inductive_reasoning"],
  "resource_requirements": {
    "cpu_percent": 5,
    "memory_mb": 50
  },
  "dependencies": [],
  "author": "Developer Name",
  "license": "MIT"
}
```

### Plugin Implementation

```python
# src/main.py
from mcp_zero.plugin import PluginBase

class ReasoningPlugin(PluginBase):
    def initialize(self, agent):
        self.agent = agent
        return True
        
    def deductive_reasoning(self, premises, conclusion):
        """Apply deductive reasoning to analyze conclusion validity"""
        # Implementation
        return {"valid": True, "confidence": 0.95}
        
    def inductive_reasoning(self, observations, hypothesis):
        """Apply inductive reasoning from observations to hypothesis"""
        # Implementation
        return {"probability": 0.87, "supporting_evidence": [...]}
        
def initialize(agent):
    plugin = ReasoningPlugin()
    return plugin.initialize(agent)
```

## Plugin Development Guidelines

### Resource Constraints

All plugins must adhere to MCP-ZERO's strict hardware constraints:

```python
# Resource monitoring in plugins
from mcp_zero.monitoring import ResourceMonitor

class MyPlugin(PluginBase):
    def initialize(self, agent):
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.set_limits(cpu_percent=5, memory_mb=50)
        return True
        
    def intensive_operation(self, data):
        # Start monitoring
        self.resource_monitor.start()
        
        # Perform operation
        result = self._process(data)
        
        # Check if limits exceeded
        if self.resource_monitor.limits_exceeded():
            return {"error": "Resource limits exceeded"}
            
        return result
```

### Security Guidelines

1. **Sandbox Containment**: Never attempt to escape the WASM sandbox
2. **Resource Monitoring**: Always check and honor resource limits
3. **Safe Dependencies**: Only use approved dependencies
4. **Input Validation**: Validate all inputs before processing
5. **Cryptographic Signing**: All plugins must be cryptographically signed

## Testing Plugins

MCP-ZERO provides a plugin testing framework:

```python
from mcp_zero.testing import PluginTester

# Initialize the tester
tester = PluginTester("advanced-reasoning")

# Test specific capabilities
results = tester.test_capability("deductive_reasoning")
assert results["passed"] == True

# Test resource usage
resource_compliance = tester.check_resource_compliance()
assert resource_compliance["compliant"] == True
```

## Deploying Plugins

### Building WASM Binary

```bash
# Build plugin to WASM
mcp-plugin-builder build advanced-reasoning

# Output: ./wasm/advanced-reasoning.wasm
```

### Registering in Plugin Registry

```python
from mcp_zero.registry import PluginRegistry

# Register plugin with cryptographic verification
registry = PluginRegistry(rpc_url="http://localhost:8081")
registry.register_plugin("./wasm/advanced-reasoning.wasm")
```

### Attaching to Agents

```python
from mcp_zero import Agent

# Create agent and attach plugin
agent = Agent.spawn("reasoning_agent")
agent.attach_plugin("advanced-reasoning", config={
    "mode": "high_precision"
})

# Use plugin capability
result = agent.use_capability(
    "deductive_reasoning",
    premises=["All humans are mortal", "Socrates is human"],
    conclusion="Socrates is mortal"
)
```

## Plugin Versioning and Updates

MCP-ZERO supports versioned plugins with automatic compatibility checks:

```python
# Attach specific version
agent.attach_plugin("advanced-reasoning", version="1.2.3")

# Update plugin
agent.update_plugin("advanced-reasoning", version="latest")
```

## Plugin Lifecycle Management

```python
# Check plugin status
status = agent.get_plugin_status("advanced-reasoning")

# Detach plugin
agent.detach_plugin("advanced-reasoning")
```

By following these guidelines, developers can create powerful, secure, and efficient plugins that extend MCP-ZERO's capabilities while maintaining its core principles of sustainability, security, and resource efficiency.
