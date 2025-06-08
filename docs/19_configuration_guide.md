# Configuration Guide

## Overview

MCP-ZERO uses a layered configuration approach: defaults < config files < environment variables.

## Configuration File

```yaml
# config.yaml
api:
  host: 0.0.0.0
  port: 8000
  workers: 4
  timeout: 30

database:
  type: mongodb
  host: localhost
  port: 27017
  name: mcpzero
  user: ${MCP_DB_USER}
  password: ${MCP_DB_PASSWORD}

mesh:
  enabled: true
  host: 0.0.0.0
  port: 8765
  bootstrap_peers:
    - ws://peer1.example.com:8765
    - ws://peer2.example.com:8765

logging:
  level: info
  format: json
  output: /var/log/mcp-zero/service.log
```

## Environment Variables

```bash
# Core settings
export MCP_API_HOST=0.0.0.0
export MCP_API_PORT=8000
export MCP_API_KEYS=key1,key2,key3

# Database connection
export MCP_DB_TYPE=mongodb
export MCP_DB_HOST=localhost
export MCP_DB_PORT=27017
export MCP_DB_NAME=mcpzero
export MCP_DB_USER=mcpadmin
export MCP_DB_PASSWORD=securepassword

# Mesh network
export MCP_MESH_ENABLED=true
export MCP_MESH_HOST=0.0.0.0
export MCP_MESH_PORT=8765
export MCP_BOOTSTRAP_PEERS=ws://peer1.example.com:8765,ws://peer2.example.com:8765

# Logging
export MCP_LOG_LEVEL=info
export MCP_LOG_FORMAT=json
export MCP_LOG_OUTPUT=/var/log/mcp-zero/service.log
```

## Configuration API

```python
from mcp_zero.config import Config

# Load configuration
config = Config.load("/etc/mcp-zero/config.yaml")

# Access configuration values
api_host = config.get("api.host")
api_port = config.get("api.port")
db_config = config.get("database")

# Override configuration
config.set("api.workers", 8)
```

## Secrets Management

```python
from mcp_zero.secrets import SecretManager

# Initialize secret manager
secrets = SecretManager()

# Get API key
api_key = secrets.get("api_key")

# Get database password
db_password = secrets.get("db_password")
```

## Configuration Validation

```python
# Validate configuration
validation = config.validate()

if not validation.valid:
    for error in validation.errors:
        print(f"Error in {error.path}: {error.message}")
    sys.exit(1)
```

## Dynamic Configuration

```python
# Register configuration change handler
@config.on_change("api.workers")
def on_workers_change(old_value, new_value):
    print(f"Workers changed from {old_value} to {new_value}")
    adjust_worker_pool(new_value)
    
# Update configuration at runtime
config.set("api.workers", 8)
```
