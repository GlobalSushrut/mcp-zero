# Glossary

## Overview

This glossary defines key terms used throughout the MCP-ZERO documentation and codebase.

## Terms and Definitions

### Agent
A computational entity within MCP-ZERO that can execute operations. Agents have lifecycle management, plugin capabilities, and trace verification.

### Agreement
A formal contract between resource consumers and providers defining usage terms, limits, and billing arrangements.

### AgreementValidator
Component that verifies agreement conditions are met during resource usage and triggers billing events.

### Capability
A permission or ability granted to a plugin or agent, using a capability-based security model.

### HeapBT
Specialized data structure used for efficient agent state storage and management alongside MongoDB.

### Kernel
The immutable core of MCP-ZERO written in Rust and C++, providing fundamental functionality that never changes.

### Mesh Bridge
Component connecting the P2P mesh network with the MCP-ZERO core infrastructure.

### Mesh Network
Decentralized peer-to-peer network for resource discovery and agent communication across nodes.

### MeshNode
Individual participant in the mesh network that maintains peer connections and shares resources.

### Plugin
WASM-based extension that adds capabilities to agents without modifying the immutable core.

### Poseidon
Cryptographic hash function used in the trace engine for zero-knowledge proof generation.

### Resource
Any shareable entity in MCP-ZERO, including agents, data sources, computation services, or storage.

### ResourceDirectory
Component that maintains a catalog of available local and remote resources in the mesh network.

### SDK
Python-based Software Development Kit for interacting with the MCP-ZERO infrastructure.

### Snapshot
Point-in-time capture of an agent's complete state that can be used for recovery or migration.

### Trace
Cryptographically verifiable record of an operation's execution, inputs, and outputs.

### ZK-Traceable
Ability to verify operation execution without revealing sensitive inputs or outputs using zero-knowledge proofs.

### ZKSync
Component used in the trace engine for generating and verifying zero-knowledge proofs.

## Acronyms

### ABI
Application Binary Interface - defines how plugins interact with the MCP-ZERO core.

### HSM
Hardware Security Module - specialized hardware for secure key storage.

### MCP
Model Context Protocol - the underlying protocol for agent communication.

### RBAC
Role-Based Access Control - security model for controlling access to resources.

### WASM
WebAssembly - binary instruction format used for plugins in MCP-ZERO.
