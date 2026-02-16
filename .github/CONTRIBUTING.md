# Contributing to MCP-ZERO

Thank you for your interest in contributing to MCP-ZERO, the world's first unstoppable AI framework! This guide will help you understand our core principles and how to contribute effectively.

## 🛡️ Core Principle: Offline-First Resilience

MCP-ZERO's revolutionary offline-first resilience pattern is our most important design principle. All contributions must adhere to these guidelines:

1. **Single Connection Attempt**: Components should try to connect to external services exactly once, then permanently fall back to offline mode if unsuccessful
2. **Immediate Fallback**: On connection failure, components must switch to offline mode without retries
3. **Immutable Lock Files**: Create cryptographic proof of fallback for audit trails
4. **Local Processing**: Critical functionality must continue working offline, even with degraded capability

## 🧠 ZETA Component Guidelines

When modifying ZETA acceleration components:

1. **ZETACUDA**: Ensure Rust code follows memory safety best practices and includes proper error handling
2. **ZETATENSOR**: All tensor operations must have a non-GPU fallback path
3. **ZETAFACE**: Interface components must validate all contracts at runtime
4. **ZETA LLM**: Local language models must work without external dependencies

## 📑 Contract System

When working with the contract system:

1. Contract YAML files must be properly validated before burning
2. Lock files must be cryptographically signed
3. All changes must be compatible with the Terraform integration
4. Contract validation must work in both online and offline modes

## 🚀 Development Workflow

1. **Fork and Clone**: Fork the repository and clone it to your machine
2. **Set Up Environment**: Run `./install_mcp_zero.sh --dev` to set up your development environment
3. **Create Branch**: Create a feature branch: `git checkout -b feature/your-feature-name`
4. **Test Offline-First**: Always test your changes in offline mode
5. **Submit PR**: Create a pull request with clear descriptions and screenshots if applicable

## 🧪 Testing

All contributions must include tests that validate:

1. Functionality works in both online and offline modes
2. Single connection attempt pattern is properly implemented
3. Lock files are created correctly
4. Performance is not significantly degraded in offline mode

## 📋 Pull Request Process

1. Ensure all offline-first resilience tests pass
2. Update documentation to reflect changes
3. Fill out the PR template completely, especially the offline-first checklist
4. Request review from the appropriate team (see CODEOWNERS)
5. Address all reviewer feedback

## 💼 Code Style

1. Python: Follow PEP 8 guidelines
2. Rust: Follow Rust style guidelines
3. YAML: Use 2-space indentation for contracts
4. Documentation: Use markdown for all documentation

## 🌟 Join the Movement

By contributing to MCP-ZERO, you're joining a revolutionary movement to create truly unstoppable AI systems that work when everything else fails. Thank you for being part of this journey!
