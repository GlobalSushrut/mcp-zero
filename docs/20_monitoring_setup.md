# Monitoring Setup

## Overview

Monitor MCP-ZERO components to ensure performance within resource constraints and long-term stability.

## Key Metrics

| Category | Metrics |
|----------|---------|
| System | CPU, RAM, Disk, Network |
| Kernel | Agent count, Resource usage, Plugin load |
| Mesh | Peer connections, Resource queries, Message rate |
| API | Request rate, Latency, Error rate |
| Database | Query performance, Size, Connections |

## Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'mcp-zero'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:9090']
```

## Metrics Endpoints

```python
from mcp_zero.metrics import metrics

# Register custom metrics
request_counter = metrics.counter(
    "api_requests_total",
    "Total API requests processed"
)

execution_time = metrics.histogram(
    "execution_time_seconds",
    "Time spent executing operations",
    buckets=[0.1, 0.5, 1.0, 5.0]
)

# Record metrics
@metrics.track()
def process_request():
    request_counter.inc()
    with execution_time.time():
        # Process request
        pass
```

## Grafana Dashboard

```
┌─────────────────────┐ ┌─────────────────────┐
│                     │ │                     │
│   CPU Usage (<27%)  │ │   Memory (827MB max)│
│                     │ │                     │
└─────────────────────┘ └─────────────────────┘
┌─────────────────────┐ ┌─────────────────────┐
│                     │ │                     │
│   Active Agents     │ │   Mesh Connections  │
│                     │ │                     │
└─────────────────────┘ └─────────────────────┘
┌─────────────────────┐ ┌─────────────────────┐
│                     │ │                     │
│   API Requests/s    │ │   Database Queries  │
│                     │ │                     │
└─────────────────────┘ └─────────────────────┘
```

## Alerting Rules

```yaml
groups:
- name: mcp-zero-alerts
  rules:
  - alert: HighCpuUsage
    expr: mcp_cpu_usage_percent > 25
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High CPU usage"
      description: "CPU usage above 25% for 5 minutes"

  - alert: HighMemoryUsage
    expr: mcp_memory_usage_mb > 800
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage above 800MB for 5 minutes"
```

## Logging Integration

```python
import logging
from mcp_zero.logging import setup_logging

# Configure structured logging
setup_logging(
    level=logging.INFO,
    format="json",
    service_name="api-server"
)

logger = logging.getLogger("mcp-zero")

# Log with context
logger.info("Processing request", extra={
    "request_id": "req123",
    "user_id": "user456",
    "operation": "query_resources"
})
```

## Health Checks

```python
from mcp_zero.health import health

# Register health checks
@health.check("database")
def check_database():
    if db.is_connected():
        return health.Status.HEALTHY
    return health.Status.UNHEALTHY, "Database connection failed"

@health.check("mesh")
def check_mesh():
    if mesh.connected_peers > 0:
        return health.Status.HEALTHY
    return health.Status.DEGRADED, "No mesh peers connected"
```
