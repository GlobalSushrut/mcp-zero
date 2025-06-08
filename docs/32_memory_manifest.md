# Memory Manifest (.mf)

## Overview

The Memory Manifest (.mf) is MCP-ZERO's system for preserving architectural decisions, code patterns, and system knowledge across the 100+ year infrastructure lifetime.

## Purpose

The Memory Manifest stores:

1. Tree logic of system components
2. Design decisions and rationales
3. Integration patterns and dependencies
4. Architectural principles and constraints
5. Historical development context

## File Format

Memory Manifest files use a structured YAML format:

```yaml
# mcpzero.mf
version: "1.0"
last_updated: "2025-06-07T10:00:00Z"
components:
  kernel:
    tree:
      - name: "AgentManager"
        path: "src/kernel/agent_manager.rs"
        purpose: "Main agent lifecycle handler"
        constraints:
          - "Must run under 12% CPU single core"
          - "Maximum memory footprint 120MB"
        children:
          - name: "AgentFactory"
            path: "src/kernel/agent_factory.rs"
            purpose: "Creates agent instances with unique IDs"
          - name: "AgentMonitor" 
            path: "src/kernel/agent_monitor.rs"
            purpose: "Tracks agent health and resource usage"
      
      - name: "PluginSystem"
        path: "src/kernel/plugin_system.rs"
        purpose: "Manages WASM plugins and capabilities"
        design_decisions:
          - decision: "Use WASM for plugins"
            rationale: "Platform-independence and security sandboxing"
            alternatives_considered:
              - "Native plugins (rejected: security concerns)"
              - "JavaScript (rejected: performance constraints)"

  sdk:
    tree:
      - name: "AgentInterface"
        path: "sdk/python/mcp_zero/agent.py"
        purpose: "Python bindings for agent operations"
        
      - name: "PluginManager"
        path: "sdk/python/mcp_zero/plugins.py"
        purpose: "Plugin CRUD operations"
        integration_points:
          - component: "kernel.PluginSystem"
            method: "via RPC"

decisions:
  - id: "MCP-001"
    title: "Immutable core architecture"
    date: "2024-12-15"
    context: "Need for 100+ year sustainability"
    decision: "Core kernel will be immutable with all extensions via plugins"
    consequences:
      - "Enhanced stability and security"
      - "More complex plugin development"

  - id: "MCP-002"
    title: "Resource constraints"
    date: "2025-01-10"
    context: "Long-term hardware compatibility"
    decision: "Target <27% CPU (single i3 core) and <827MB RAM"
    consequences:
      - "Works on minimal hardware"
      - "Requires careful optimization"

dependencies:
  - name: "Rust"
    version: "1.75+"
    components:
      - "kernel"
    rationale: "Memory safety and performance"
    
  - name: "Python"
    version: "3.9+"
    components:
      - "sdk"
    rationale: "Developer accessibility"
```

## Usage

### Reading the Memory Manifest

```python
from mcp_zero.manifest import MemoryManifest

# Load the memory manifest
manifest = MemoryManifest.load("/path/to/mcpzero.mf")

# Access component tree
kernel_components = manifest.components["kernel"].tree
for component in kernel_components:
    print(f"Component: {component.name}")
    print(f"Purpose: {component.purpose}")
    
# Access design decisions
for decision in manifest.decisions:
    print(f"Decision {decision.id}: {decision.title}")
    print(f"Context: {decision.context}")
    print(f"Decision: {decision.decision}")
```

### Updating the Memory Manifest

```python
from mcp_zero.manifest import MemoryManifest

# Load existing manifest
manifest = MemoryManifest.load("/path/to/mcpzero.mf")

# Add new component
manifest.add_component(
    section="sdk",
    component={
        "name": "TraceClient",
        "path": "sdk/python/mcp_zero/trace.py",
        "purpose": "Client for interacting with trace system",
        "integration_points": [
            {"component": "kernel.TraceEngine", "method": "via RPC"}
        ]
    }
)

# Add new design decision
manifest.add_decision(
    decision={
        "id": "MCP-025",
        "title": "ZK-SNARK for trace verification",
        "date": "2025-06-07",
        "context": "Need for verifiable but private execution records",
        "decision": "Use Poseidon+ZKSync for zero-knowledge proofs",
        "consequences": [
            "Cryptographic verification of execution",
            "Privacy preservation for sensitive operations"
        ]
    }
)

# Save updated manifest
manifest.save("/path/to/mcpzero.mf")
```

## AI Compatibility

The Memory Manifest is specifically designed to be AI-readable and AI-updatable:

1. **Structured format**: YAML provides machine-readable structure
2. **Explicit relationships**: Component relationships are explicitly defined
3. **Decision context**: Includes context and rationales for AI understanding
4. **Design history**: Preserves alternatives considered and rejected
5. **Constraint documentation**: Documents system limitations and requirements

```python
from mcp_zero.manifest import MemoryManifest
from mcp_zero.ai import AIManifestProcessor

# Process manifest with AI
manifest = MemoryManifest.load("/path/to/mcpzero.mf")
ai_processor = AIManifestProcessor()

# Generate architecture summary
summary = ai_processor.generate_summary(manifest)
print(summary)

# Analyze impact of proposed change
change_impact = ai_processor.analyze_change_impact(
    manifest=manifest,
    change_description="Replace MongoDB with PostgreSQL"
)
print(f"Impact score: {change_impact.score}/10")
print("Affected components:")
for component in change_impact.affected_components:
    print(f"- {component}")
```

## Manifest Verification

```python
from mcp_zero.manifest import verify_manifest

# Verify manifest integrity
verification = verify_manifest("/path/to/mcpzero.mf")

if verification.valid:
    print("Manifest is valid")
else:
    print("Manifest validation errors:")
    for error in verification.errors:
        print(f"- {error}")
```

## Integration with Version Control

```bash
# Git hooks for manifest validation
#!/bin/bash
# pre-commit hook
mcp-zero manifest verify ./mcpzero.mf

if [ $? -ne 0 ]; then
  echo "Memory manifest validation failed. Commit aborted."
  exit 1
fi
```

## Manifest Visualization

```python
from mcp_zero.manifest import MemoryManifest
from mcp_zero.visualization import generate_diagram

# Generate component diagram
manifest = MemoryManifest.load("/path/to/mcpzero.mf")
diagram = generate_diagram(
    manifest=manifest,
    diagram_type="component",
    output_path="./component_diagram.svg"
)

# Generate decision timeline
timeline = generate_diagram(
    manifest=manifest,
    diagram_type="timeline",
    output_path="./decision_timeline.svg"
)
```
