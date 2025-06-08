# Hardware Requirements

## Overview

MCP-ZERO is designed for minimal resource usage, ensuring 100+ year sustainability on modest hardware.

## Core Requirements

| Resource | Requirement | Notes |
|----------|-------------|-------|
| CPU | <27% of 1-core i3 (2.4GHz) | Single core sufficient |
| RAM | 827MB peak, 640MB avg | 1GB recommended |
| Storage | 500MB base + data | SSD preferred |
| Network | 10Mbps minimum | For mesh communication |

## Component-Specific Requirements

| Component | CPU | RAM | Storage | 
|-----------|-----|-----|---------|
| Kernel | 15% | 400MB | 200MB |
| API Server | 5% | 120MB | 50MB |
| Mesh Node | 5% | 100MB | 50MB |
| Agreement Executor | 2% | 80MB | 30MB |
| Database | Variable | Variable | Variable |

## Scaling Considerations

```
Single node: 1-10 concurrent agents
Small cluster: 10-100 concurrent agents
Large deployment: 100+ concurrent agents
```

## Virtualization Support

- Docker containers
- Virtual machines
- Cloud instances
- Bare metal

## Minimum Development Environment

```
CPU: Dual core, 2GHz+
RAM: 2GB
Storage: 1GB free
OS: Linux, macOS, or Windows
```

## Production Recommendations

- Dedicated hardware or VMs
- Isolated network interfaces
- Hardware security modules for keys
- Redundant power and networking
- RAID for database storage

## Performance Scaling

```python
# Example resource calculation
def calculate_resources(agent_count):
    cpu_percent = 15 + (agent_count * 0.5)  # Base + per agent
    ram_mb = 400 + (agent_count * 40)       # Base + per agent
    
    return {
        "cpu_percent": min(cpu_percent, 90),  # Cap at 90%
        "ram_mb": ram_mb
    }
```

## Monitoring Setup

Monitor these key metrics:

- CPU usage (keep below 27% per core)
- RAM usage (keep below 827MB peak)
- Disk I/O rates
- Network throughput
- Temperature (for embedded devices)
