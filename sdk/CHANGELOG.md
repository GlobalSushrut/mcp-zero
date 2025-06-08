# Changelog

All notable changes to the MCP-ZERO SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-06-07

### Added
- Initial production-grade release of the MCP-ZERO SDK
- Core Agent class with full lifecycle support:
  - `spawn`: Create new agents with unique IDs
  - `attach_plugin`: Add capabilities through sandboxed plugins
  - `execute`: Run operations with ethical governance and resource constraints
  - `snapshot`: Create runtime snapshots for state preservation
  - `recover`: Restore agent state from snapshots
- Plugin system with sandboxing and resource limiting
- ResourceMonitor for enforcing hardware constraints (<27% CPU, <827MB RAM)
- Cryptographic integrity verification with signing and verification
- RPC client with optimized resource usage and connection handling
- Test suite with comprehensive unit tests and resource monitoring
- Example applications demonstrating SDK usage
- Plugin registry interface for central plugin management

### Security
- Cryptographic integrity verification for all operations
- Resource constraint enforcement to prevent excessive usage
- Ethical policy validation and enforcement
- Sandboxed plugin execution environment
