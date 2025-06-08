# Integration Patterns

## Overview

MCP-ZERO provides multiple integration patterns for connecting with external systems, services, and applications.

## Key Integration Methods

- SDK Integration
- REST API
- Mesh Network 
- Plugin Extension
- Event Streaming

## SDK Integration

```python
from mcp_zero.sdk import Agent, configure

# Configure SDK
configure(api_key="your_api_key")

# Create and use agent
agent = Agent.spawn()
agent.attach_plugin("data_processing")
result = agent.execute("process_data", {"input": "raw_data"})

# Use in application
def process_user_data(user_data):
    return agent.execute("process_data", {"input": user_data})
```

## REST API Integration

```python
import requests

# API configuration
API_URL = "https://api.mcp-zero.org/v1"
API_KEY = "your_api_key"

# Create agent
response = requests.post(
    f"{API_URL}/agents",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"constraints": {"cpu": 0.1, "memory": 256}}
)
agent_id = response.json()["agent_id"]

# Attach plugin
requests.post(
    f"{API_URL}/agents/{agent_id}/plugins",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"plugin_id": "data_processing"}
)

# Execute method
response = requests.post(
    f"{API_URL}/agents/{agent_id}/execute",
    headers={"Authorization": f"Bearer {API_KEY}"},
    json={"method": "process_data", "params": {"input": "raw_data"}}
)
result = response.json()["result"]
```

## Mesh Network Integration

```python
from mcp_zero.mesh import MeshClient

# Connect to mesh network
mesh = MeshClient()
mesh.connect()

# Discover resources
resources = mesh.query_resources(
    resource_type="agent",
    capabilities=["image_processing"]
)

# Use remote resource
if resources:
    remote_resource_id = resources[0]["resource_id"]
    result = mesh.execute_remote(
        resource_id=remote_resource_id,
        method="process_image",
        params={"url": "https://example.com/image.jpg"}
    )
```

## Plugin-Based Integration

```python
from mcp_zero.plugin import Plugin, export

# Create custom integration plugin
class ExternalSystemPlugin(Plugin):
    def __init__(self):
        self.client = ExternalSystemClient()
        
    @export
    def fetch_data(self, params):
        """Fetch data from external system"""
        return self.client.get_data(params["query"])
    
    @export
    def send_data(self, params):
        """Send data to external system"""
        return self.client.put_data(params["data"])

# Build plugin
ExternalSystemPlugin.build("external_system")

# Use plugin
agent.attach_plugin("external_system")
data = agent.execute("fetch_data", {"query": "customer_data"})
```

## Event Streaming

```python
from mcp_zero.events import EventStream

# Subscribe to events
stream = EventStream()
stream.subscribe("agent.created", on_agent_created)
stream.subscribe("resource.updated", on_resource_updated)

# Event handlers
def on_agent_created(event):
    agent_id = event["agent_id"]
    # Integrate with external monitoring
    notify_monitoring_system(f"New agent created: {agent_id}")

def on_resource_updated(event):
    # Update external resource catalog
    update_external_catalog(event["resource"])
```

## Database Integration

```python
from mcp_zero.db import DatabaseAdapter

# Create custom database adapter
class ExternalDBAdapter(DatabaseAdapter):
    def __init__(self, connection_string):
        self.db = ExternalDB(connection_string)
    
    def save_agent(self, agent_data):
        self.db.collection("agents").insert(agent_data)
    
    def load_agent(self, agent_id):
        return self.db.collection("agents").find_one({"agent_id": agent_id})

# Register custom adapter
DatabaseAdapter.register("external_db", ExternalDBAdapter)
```

## Authentication Integration

```python
from mcp_zero.auth import AuthProvider

# Create custom auth provider
class ExternalAuthProvider(AuthProvider):
    def __init__(self, auth_endpoint):
        self.endpoint = auth_endpoint
    
    def authenticate(self, credentials):
        # Verify credentials with external system
        response = requests.post(
            self.endpoint,
            json={"username": credentials.username, "password": credentials.password}
        )
        if response.status_code == 200:
            return AuthToken(response.json()["token"])
        return None

# Register auth provider
AuthProvider.register("external_auth", ExternalAuthProvider)
```

## Webhook Integration

```python
from mcp_zero.webhooks import register_webhook

# Register webhook for events
register_webhook(
    event_type="agent.state_changed",
    url="https://example.com/webhooks/agent",
    secret="webhook_signing_secret"
)
```

## Integration Best Practices

1. Use SDK for direct integration when possible
2. Implement proper error handling and retries
3. Secure API keys and credentials
4. Use webhook signing for security
5. Consider rate limits and backpressure
