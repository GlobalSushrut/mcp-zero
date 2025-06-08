# Plugin System

## Overview

MCP-ZERO plugins extend functionality without modifying the immutable core. Plugins use WASM with a signed ABI for security and portability.

## Key Features

- Sandboxed execution
- Cryptographically signed
- Capability-based security
- Hot-swappable without system restart
- Version compatibility checking

## Plugin Structure

```
plugin_name/
├── manifest.json    # Metadata and capabilities
├── plugin.wasm      # WebAssembly binary
├── signature.bin    # Cryptographic signature
└── README.md        # Documentation
```

## Usage

```python
# Attach plugin to agent
agent.attach_plugin("data_processing")

# Execute plugin method
result = agent.execute("process_data", {"input": "raw data"})
```

## Development

Create plugins with the SDK:

```python
from mcp_zero.plugin import Plugin, export

class DataPlugin(Plugin):
    @export
    def process_data(self, params):
        # Process data here
        return {"result": "processed data"}

# Build plugin
DataPlugin.build("data_processing")
```

## Lifecycle

1. **Development**: Create plugin with SDK
2. **Build**: Compile to WASM
3. **Sign**: Apply cryptographic signature
4. **Distribution**: Share via registry
5. **Verification**: Validate signature and capabilities
6. **Attachment**: Connect to agent
7. **Execution**: Run within sandbox

## Security

- All plugins run in isolated sandboxes
- Resource limits enforced
- Signatures verified before execution
- Capability-based permission model
