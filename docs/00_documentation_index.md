# MCP-ZERO Documentation Index

## Overview

This index provides a guide to the comprehensive documentation for the MCP-ZERO AI agent infrastructure. The documentation is designed to support developers and operators in understanding, deploying, and maintaining the MCP-ZERO platform.

## Getting Started

- [01 Getting Started](01_getting_started.md) - Overview, prerequisites, and quick start guide

## Architecture

- [02 Architecture Overview](02_architecture_overview.md) - Core principles, system components, and security model
- [05 Kernel Architecture](05_kernel_architecture.md) - Immutable kernel design, components, and interfaces
- [06 SDK Interface](06_sdk_interface.md) - Python SDK for interacting with MCP-ZERO
- [07 Deployment Architecture](07_deployment_architecture.md) - Deployment models and configuration
- [09 RPC Layer](09_rpc_layer.md) - Go-based RPC system with Solidity agreement middleware
- [13 Database Architecture](13_database_architecture.md) - MongoDB+HeapBT storage design

## Core Components

- [08 Plugin System](08_plugin_system.md) - WASM plugin architecture and security
- [10 Mesh Network](10_mesh_network.md) - P2P resource discovery and communication
- [11 Agreement Templates](11_agreement_templates.md) - Resource usage agreements
- [12 Trace Engine](12_trace_engine.md) - Poseidon+ZKSync verifiable execution
- [31 Solidity Agreements](31_solidity_agreements.md) - Blockchain-based smart contract integration

## Operations

- [14 Testing Procedures](14_testing_procedures.md) - Testing methodology and practices
- [15 CI/CD Pipeline](15_ci_cd_pipeline.md) - Continuous integration and deployment
- [16 Performance Guide](16_performance_guide.md) - Optimization techniques
- [18 Hardware Requirements](18_hardware_requirements.md) - Resource constraints and planning
- [19 Configuration Guide](19_configuration_guide.md) - System configuration options
- [20 Monitoring Setup](20_monitoring_setup.md) - Metrics and observability
- [21 Backup Procedures](21_backup_procedures.md) - Data protection strategies
- [24 Troubleshooting](24_troubleshooting.md) - Common issues and resolutions
- [25 Upgrade Procedures](25_upgrade_procedures.md) - Safe enhancement process

## Security and Governance

- [17 Security Model](17_security_model.md) - Defense-in-depth security approach
- [22 Security Hardening](22_security_hardening.md) - Additional security measures
- [23 Ethical Governance](23_ethical_governance.md) - Built-in ethical frameworks

## Integration and Scalability

- [04 API Reference](04_api_reference.md) - Complete API documentation
- [26 Integration Patterns](26_integration_patterns.md) - Connecting with external systems
- [27 Scalability Guide](27_scalability_guide.md) - Horizontal and vertical scaling
- [28 Sustainability Planning](28_sustainability_planning.md) - 100+ year sustainability

## Reference

- [03 Developer Guide](03_developer_guide.md) - Comprehensive development handbook
- [29 Glossary](29_glossary.md) - Terms and definitions
- [30 Quickstart Examples](30_quickstart_examples.md) - Practical code examples for common use cases
- [32 Memory Manifest](32_memory_manifest.md) - System for preserving architectural knowledge (.mf files)

## Documentation Structure

The documentation follows a logical progression:

1. **Orientation**: Getting started and architecture overview
2. **Component Details**: Deep dives into each system component
3. **Operational Guidance**: Day-to-day operations and maintenance
4. **Advanced Topics**: Security, scalability, and integration

Each document is designed to be both standalone and part of the larger documentation set, with cross-references where appropriate.

## Using This Documentation

- **New Users**: Start with [01 Getting Started](01_getting_started.md)
- **Developers**: Focus on [03 Developer Guide](03_developer_guide.md) and [04 API Reference](04_api_reference.md)
- **Operators**: Review [07 Deployment Architecture](07_deployment_architecture.md) and operational guides
- **Security Teams**: Prioritize [17 Security Model](17_security_model.md) and [22 Security Hardening](22_security_hardening.md)

## Documentation Maintenance

This documentation is designed for long-term maintainability, with a focus on clarity, accuracy, and completeness. Each document follows a consistent structure and uses examples to illustrate concepts.

For corrections or updates, please follow the contribution guidelines in the MCP-ZERO repository.
