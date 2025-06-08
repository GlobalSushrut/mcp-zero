# Getting Started with MCP-ZERO

## Overview

MCP-ZERO is a finalized core infrastructure for AI agents with an immutable foundation designed for 100+ year sustainability. This guide will help you get started with the MCP-ZERO infrastructure, understand its core components, and begin developing on the platform.

## Prerequisites

- **Operating System**: Linux (recommended), macOS, or Windows with WSL2
- **Python**: 3.9 or higher
- **Docker**: 20.10.0 or higher
- **Docker Compose**: 2.0.0 or higher
- **Git**: 2.30.0 or higher
- **Rust**: 1.56.0 or higher (for core components)
- **Go**: 1.17 or higher (for RPC layer)
- **MongoDB**: 5.0 or higher

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/your-org/mcp-zero.git
cd mcp-zero
```

### 2. Set Up Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure the System

```bash
# Create configuration file from template
cp config/settings.example.yaml config/settings.yaml

# Edit the configuration file with your preferred editor
# Set necessary environment variables for sensitive information
export MCP_API_KEYS="your-api-key"
```

### 4. Run the Infrastructure

```bash
# Start all services using Docker Compose
docker-compose up -d

# OR start individual components
python -m src.api.server
```

### 5. Verify Installation

```bash
# Check if the API is running
curl http://localhost:8000/api/v1/status

# Expected output:
# {"status": "ok", "version": "v7.0.0"}
```

## Core Components

MCP-ZERO consists of the following core components:

- **Kernel**: Built in Rust and C++ for performance and safety
- **SDK Interface**: Python-based interface for agent development
- **RPC Layer**: Lightweight Go implementation (<30MB)
- **Trace Engine**: Poseidon+ZKSync for verifiable operations
- **Agent Storage**: MongoDB with HeapBT for efficient agent state storage
- **Plugin ABI**: WASM with Signed ABI for secure plugin execution

## Next Steps

- Read the [Architecture Overview](02_architecture_overview.md) to understand the system design
- Follow the [Developer Guide](03_developer_guide.md) to start building agents
- Learn about the [Agreement System](10_agreement_system.md) for resource access control
- Explore the [Mesh Network](15_mesh_network.md) for distributed agent communication

## Support

If you encounter any issues or have questions, please:

- Check the [Troubleshooting Guide](25_troubleshooting.md)
- Read our [FAQ](26_faq.md)
- File an issue in our [GitHub repository](https://github.com/your-org/mcp-zero/issues)
- Join our [Developer Community](https://community.mcp-zero.org)
