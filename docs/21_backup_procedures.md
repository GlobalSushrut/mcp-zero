# Backup Procedures

## Overview

MCP-ZERO requires robust backup procedures to ensure data integrity and system recoverability in a 100+ year timeframe.

## Backup Components

- Database (MongoDB)
- Agent snapshots (HeapBT)
- Configuration files
- Plugin registry
- Trace logs

## Database Backup

```bash
# MongoDB backup script
#!/bin/bash

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/mcp-zero/mongodb"
mkdir -p $BACKUP_DIR

# Create backup
mongodump --uri="mongodb://${MCP_DB_USER}:${MCP_DB_PASSWORD}@${MCP_DB_HOST}:${MCP_DB_PORT}/${MCP_DB_NAME}" --out="${BACKUP_DIR}/${DATE}"

# Compress backup
tar -czf "${BACKUP_DIR}/${DATE}.tar.gz" "${BACKUP_DIR}/${DATE}"
rm -rf "${BACKUP_DIR}/${DATE}"

# Rotate backups (keep last 30 days)
find "${BACKUP_DIR}" -name "*.tar.gz" -type f -mtime +30 -delete
```

## Agent State Backup

```python
from mcp_zero.sdk import Agent
from mcp_zero.backup import backup_agent_state

# Back up all agents
def backup_all_agents():
    agents = Agent.list_all()
    for agent_id in agents:
        # Create snapshot
        agent = Agent.load(agent_id)
        snapshot_id = agent.snapshot()
        
        # Export snapshot
        backup_agent_state(agent_id, snapshot_id, 
                          f"/var/backups/mcp-zero/agents/{agent_id}")
```

## Scheduled Backups

```
# crontab configuration
# Database backup: Daily at 2am
0 2 * * * /usr/local/bin/backup_mongodb.sh

# Agent snapshot backup: Daily at 3am
0 3 * * * /usr/local/bin/backup_agents.sh

# Configuration backup: Weekly on Sunday at 1am
0 1 * * 0 /usr/local/bin/backup_config.sh

# Plugin registry backup: Weekly on Sunday at 4am
0 4 * * 0 /usr/local/bin/backup_plugins.sh
```

## Backup Verification

```python
from mcp_zero.backup import verify_backup

# Verify database backup
result = verify_backup("/var/backups/mcp-zero/mongodb/20250607_020000.tar.gz")
if result.verified:
    print("Backup verified successfully")
    print(f"Contains {result.collections} collections")
    print(f"Total documents: {result.document_count}")
else:
    print(f"Backup verification failed: {result.error}")
```

## Restoration Procedure

```python
from mcp_zero.backup import restore_from_backup

# Restore database
restore_from_backup(
    source="/var/backups/mcp-zero/mongodb/20250607_020000.tar.gz",
    target_db="mongodb://localhost:27017/mcpzero",
    credentials={"user": "admin", "password": "securepass"}
)

# Restore agent state
agent = Agent.load("agent123")
agent.recover(snapshot_id="snapshot456")
```

## Backup Storage Strategy

1. **Local Storage**: Immediate backups
2. **Remote Storage**: Daily sync to secure location
3. **Cold Storage**: Monthly archive to immutable media
4. **Geo-Replication**: Distribute across multiple regions

## Backup Security

- Encrypt all backups
- Secure access to backup storage
- Regular integrity verification
- Proper key management for encrypted backups

## Recovery Testing

```python
# Schedule regular recovery tests
def test_recovery_procedure():
    # 1. Create test environment
    test_env = create_test_environment()
    
    # 2. Restore from latest backup
    restore_status = test_env.restore_from_latest_backup()
    
    # 3. Verify system functionality
    verification = test_env.verify_functionality()
    
    # 4. Report results
    send_report("backup_verification", {
        "restore_status": restore_status,
        "verification": verification,
        "timestamp": datetime.now().isoformat()
    })
```
