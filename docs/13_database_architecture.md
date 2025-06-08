# Database Architecture

## Overview

MCP-ZERO uses MongoDB+HeapBT for agent storage with abstractions supporting multiple database backends.

## Storage Layout

```
MongoDB                  HeapBT
┌─────────────┐          ┌─────────────┐
│  Agents     │          │ Agent State │
│  Collection │          │   Trees     │
└─────────────┘          └─────────────┘
┌─────────────┐          ┌─────────────┐
│  Resources  │          │ Snapshots   │
│  Collection │          │             │
└─────────────┘          └─────────────┘
┌─────────────┐
│ Agreements  │
│ Collection  │
└─────────────┘
┌─────────────┐
│   Traces    │
│ Collection  │
└─────────────┘
```

## Schema Examples

**Agent Document**:
```json
{
  "agent_id": "agent123",
  "created_at": "2025-06-01T12:00:00Z",
  "owner": "user456",
  "constraints": {"cpu": 0.1, "memory": 256},
  "plugins": ["data_processing", "natural_language"],
  "state_root": "1a2b3c4d..."
}
```

**Resource Document**:
```json
{
  "resource_id": "resource789",
  "resource_type": "agent",
  "owner": "user456",
  "capabilities": ["image_processing"],
  "location": "local",
  "metadata": {
    "version": "1.0.0",
    "created_at": "2025-06-01T12:00:00Z"
  }
}
```

## Usage Example

```python
from mcp_zero.db import DatabaseManager

# Get database manager
db = DatabaseManager()

# Store agent data
agent_id = "agent123"
agent_data = {
    "owner": "user456",
    "constraints": {"cpu": 0.1, "memory": 256}
}
db.agents.insert(agent_id, agent_data)

# Query resources
resources = db.resources.find({
    "capabilities": "image_processing",
    "location": "local"
})

# Update agreement
db.agreements.update(
    "agreement123",
    {"status": "active"}
)
```

## HeapBT Integration

HeapBT provides efficient state management:

```
        Root
       /    \
      /      \
     A        B
    / \      / \
   C   D    E   F
```

- Efficient state diff storage
- Fast snapshot creation
- Secure state verification
- Compact representation
