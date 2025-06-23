# MCP Zero Demos

This directory contains a collection of demos showcasing the features and capabilities of MCP Zero.

## Demo Categories

### Basic Demos
Basic examples demonstrating core MCP Zero functionality.
- File operations
- Memory systems
- Simple editor features

### Advanced Demos
Advanced features and use cases.
- Enhanced project memory
- Code generation with templates
- Editor extensions

### Intelligence Demos
AI-powered code intelligence features.
- Code analysis and diagnostics
- Intelligent code completion
- Syntax-aware refactoring
- Project understanding

### Offline Resilience Demos
Showcasing MCP Zero's offline-first resilience patterns.
- Working without network connectivity
- Graceful degradation of features
- Local fallbacks for remote services

### Integration Demos
Examples of integrating MCP Zero with external services and tools.
- LLM integrations
- Database connections
- API gateway usage

## Running Demos

Most demos can be run directly with Python:

```bash
python3 /path/to/demo/script.py
```

For specific requirements and detailed instructions, see the README file in each demo directory.

## Offline-First Resilience

A key principle of MCP Zero is offline-first resilience. All components:
1. Start in offline mode by default
2. Attempt to connect to remote services only once
3. Fall back permanently to local processing on failure
4. Maintain functionality even when remote services are unavailable

This pattern ensures that MCP Zero remains functional in all environments, from fully connected cloud deployments to air-gapped systems with no external connectivity.
