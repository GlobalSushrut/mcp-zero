# Mesh Network

## Overview

MCP-ZERO's mesh network enables decentralized resource discovery and P2P agent communication across nodes.

## Key Components

- **ResourceDirectory**: Catalogs local and remote resources
- **MeshNode**: Maintains peer connections
- **MeshBridge**: Connects mesh with MCP-ZERO core
- **ConnectionManager**: Handles WebSocket communications
- **MessageHandler**: Processes incoming messages

## Network Topology

```
   ┌─────┐     ┌─────┐
   │Node │◄───►│Node │
   │  A  │     │  B  │
   └──┬──┘     └──┬──┘
      │           │
      │           │
   ┌──▼──┐     ┌──▼──┐
   │Node │◄───►│Node │
   │  C  │     │  D  │
   └─────┘     └─────┘
```

## Resource Discovery

```python
# Register a resource
mesh.register_resource(
    resource_id="agent123",
    resource_type="agent",
    capabilities=["image_processing"]
)

# Query resources
resources = mesh.query_resources(
    resource_type="agent",
    capabilities=["image_processing"]
)
```

## P2P Communication

```python
# Connect to peers
mesh.connect_to_peer("ws://peer1.example.com:8765")

# Event subscription
mesh.subscribe("resource.added", on_resource_added)

# Remote execution
mesh.execute_remote(
    resource_id="agent123",
    method="process_image",
    params={"image_url": "https://example.com/image.jpg"}
)
```

## Security Model

- Signed resource registration
- Peer verification
- End-to-end encryption
- Agreement validation for resource access

## Resource Directory

ResourceDirectory maintains metadata about available resources:

```python
{
    "resource_id": "agent123",
    "resource_type": "agent",
    "location": "local",
    "owner": "user456",
    "capabilities": ["image_processing", "text_analysis"],
    "metadata": {
        "version": "1.0",
        "last_updated": "2025-06-01T12:00:00Z"
    }
}
```

## Message Format

```json
{
  "id": "msg123",
  "type": "query",
  "sender": "node456",
  "recipient": "node789",
  "timestamp": "2025-06-07T04:30:00Z",
  "payload": {
    "resource_type": "agent",
    "capabilities": ["image_processing"]
  },
  "signature": "abc123def456..."
}
```
