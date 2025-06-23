# MCP-ZERO Server Operations

## Server Overview

MCP-ZERO includes several server components that work together to provide the infrastructure for AI agent operations:

1. **Main MCP Server** (`mcp-server`): Core server handling agent lifecycle, plugin loading, and execution
2. **RPC Layer** (`mcp-rpc-minimal`): Lightweight RPC server for inter-agent communication and API access
3. **Trace Engine Server**: Handles ZK-traceable auditing and cryptographic verification

## Server Components

| Server Binary | Purpose | Default Port | Hardware Requirements |
|---------------|---------|--------------|----------------------|
| `mcp-server` | Core agent server | 8080 | <27% CPU, <827MB RAM |
| `mcp-rpc-minimal` | Minimal RPC server | 8081 | <5% CPU, <100MB RAM |
| `mcp-zero-server` | Combined server | 8080, 8081 | <27% CPU, <827MB RAM |

## Running MCP-ZERO Server

The recommended way to run the MCP-ZERO server is using the combined binary:

```bash
cd /home/umesh/Videos/mcp_zero/src/rpc-layer
./mcp-server
```

This will start the server with default configuration, which looks for a config file at `../../config.yaml`.

### Server Configuration

The server loads its configuration from `config.yaml`. To specify a custom configuration file:

```bash
./mcp-server -config /path/to/custom/config.yaml
```

### Common Issues

1. **Port already in use**: If you see "address already in use" errors, check for existing processes:
   ```bash
   ps aux | grep mcp
   ```

2. **Missing configuration**: Ensure your config.yaml exists and includes required settings for API endpoints

3. **Resource constraints**: MCP-ZERO enforces strict hardware constraints (<27% CPU, <827MB RAM) as part of its immutable core design

## Testing Server Connection

To test if the server is running correctly:

```bash
curl http://localhost:8080/health
curl http://localhost:8081/api/v1/status
```

## Recommended Deployment

For production deployments, run the server with systemd to ensure automatic restarts and proper logging:

```bash
# Example systemd service file: /etc/systemd/system/mcp-zero.service
[Unit]
Description=MCP-ZERO Server
After=network.target

[Service]
User=mcp
WorkingDirectory=/opt/mcp-zero/src/rpc-layer
ExecStart=/opt/mcp-zero/src/rpc-layer/mcp-server
Restart=always
RestartSec=5
LimitCPU=27%
LimitAS=827M

[Install]
WantedBy=multi-user.target
```

This ensures the server maintains its hardware constraints and provides 100+ year sustainability.
