# Troubleshooting Guide

## Overview

This guide helps diagnose and resolve common issues in the MCP-ZERO infrastructure.

## Diagnostic Tools

```bash
# Check system status
mcp-zero status

# Verify component health
mcp-zero health check

# Test connectivity
mcp-zero ping mesh

# View logs
mcp-zero logs --component=kernel --tail=100
```

## Common Issues

### Agent Creation Fails

```
Symptoms:
- Agent.spawn() returns error
- "Resource limit exceeded" message

Solutions:
1. Check system resources (CPU <27%, RAM <827MB)
2. Verify database connectivity
3. Ensure API key has sufficient permissions
```

### Plugin Attachment Fails

```
Symptoms:
- "Plugin verification failed" error
- "Invalid signature" message

Solutions:
1. Verify plugin signature with correct key
2. Check plugin compatibility with MCP-ZERO version
3. Ensure plugin WASM format is valid
```

### Mesh Network Connection Issues

```
Symptoms:
- No peers connecting
- "Connection refused" errors

Solutions:
1. Verify firewall allows port 8765
2. Check bootstrap peer configuration
3. Ensure mesh service is running
4. Verify TLS certificates are valid
```

## Debugging Mode

```python
from mcp_zero.debug import enable_debug

# Enable debugging
enable_debug(
    level="verbose",
    components=["kernel", "mesh"],
    log_file="/var/log/mcp-zero/debug.log"
)

# Monitor debug events
for event in debug.event_stream():
    print(f"{event.component}: {event.message}")
```

## Log Analysis

```python
from mcp_zero.logs import LogAnalyzer

# Analyze logs for errors
analyzer = LogAnalyzer("/var/log/mcp-zero/service.log")
errors = analyzer.find_errors(
    timeframe={"start": "2025-06-06T00:00:00Z", "end": "2025-06-07T23:59:59Z"},
    severity="error"
)

# Generate report
analyzer.generate_report("error_analysis.html")
```

## Performance Issues

```
Symptoms:
- High latency in operations
- CPU or memory approaching limits

Solutions:
1. Check for resource-intensive plugins
2. Analyze trace logs for slow operations
3. Verify database index optimization
4. Consider limiting concurrent agents
```

## Recovery Procedures

```python
from mcp_zero.recovery import recover_system

# Recover from database corruption
recover_system("database", backup_path="/var/backups/mcp-zero/mongodb/latest")

# Recover agent from snapshot
recover_system("agent", agent_id="agent123", snapshot_id="snap456")
```

## Diagnostic Commands

```bash
# Check kernel status
mcp-zero kernel status

# Inspect agent
mcp-zero agent inspect agent123

# Test plugin
mcp-zero plugin test data_processing

# Verify resource directory
mcp-zero mesh resources list
```

## Support Resources

- GitHub Issues: https://github.com/mcp-zero/issues
- Documentation: https://docs.mcp-zero.org
- Support Email: support@mcp-zero.org
