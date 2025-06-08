# Upgrade Procedures

## Overview

MCP-ZERO uses an immutable core architecture where upgrades happen through plugins and addons without modifying the base system.

## Core Principles

- Core functionality never changes (immutable)
- All enhancements via plugin ecosystem
- Zero-downtime upgrades
- Backward compatibility guaranteed
- Cryptographic verification of all components

## Plugin Updates

```python
from mcp_zero.sdk import PluginManager

# Get plugin manager
plugin_manager = PluginManager()

# Check for updates
updates = plugin_manager.check_updates()

# View available updates
for plugin_id, update in updates.items():
    print(f"{plugin_id}: {update['current_version']} → {update['new_version']}")
    print(f"Changes: {update['changelog']}")

# Update specific plugin
plugin_manager.update_plugin("data_processing")

# Update all plugins
plugin_manager.update_all_plugins(restart_agents=False)
```

## Update Process

```
1. Verify current system integrity
2. Download plugin updates
3. Verify cryptographic signatures
4. Test in staging environment
5. Deploy to production
6. Verify functionality
```

## Zero-Downtime Updates

```python
from mcp_zero.sdk import Agent, PluginManager

# Rolling plugin update
def update_plugin_rolling(plugin_id, new_version):
    # Get all agents using this plugin
    agents = Agent.find_by_plugin(plugin_id)
    
    # Update plugin
    plugin_manager = PluginManager()
    plugin_manager.download_plugin(plugin_id, version=new_version)
    
    # Update agents in batches
    for batch in create_batches(agents, batch_size=5):
        for agent in batch:
            # Create a replacement agent
            new_agent = Agent.spawn(constraints=agent.constraints)
            
            # Attach plugins with new version
            for plugin in agent.plugins:
                if plugin == plugin_id:
                    new_agent.attach_plugin(plugin_id, version=new_version)
                else:
                    new_agent.attach_plugin(plugin)
            
            # Transfer state
            state = agent.export_state()
            new_agent.import_state(state)
            
            # Switch traffic to new agent
            agent.redirect_traffic_to(new_agent)
            
            # Terminate old agent when quiet
            agent.terminate_when_quiet()
```

## Configuration Updates

```yaml
# Apply configuration changes
configuration:
  update_strategy: rolling
  validate_before_apply: true
  backup_before_change: true
  components:
    - api_server
    - mesh_network
```

## Compatibility Verification

```python
from mcp_zero.sdk import compatibility

# Check if plugin versions are compatible
is_compatible = compatibility.check_plugin_compatibility(
    plugin_id="data_processing",
    version="2.0.0"
)

# Get compatible plugin versions
compatible_versions = compatibility.get_compatible_versions(
    plugin_id="data_processing"
)
```

## Rollback Procedure

```python
from mcp_zero.sdk import PluginManager

# Rollback plugin update
plugin_manager = PluginManager()
plugin_manager.rollback_plugin("data_processing", target_version="1.5.0")

# Rollback multiple plugins to a known-good state
plugin_manager.rollback_all_plugins(timestamp="2025-06-01T00:00:00Z")
```

## Update Notifications

```python
from mcp_zero.sdk import notifications

# Subscribe to update notifications
notifications.subscribe("plugin.updates", on_plugin_update)
notifications.subscribe("security.updates", on_security_update)

# Define handler
def on_plugin_update(data):
    plugin_id = data["plugin_id"]
    version = data["version"]
    print(f"New version {version} available for {plugin_id}")
    
    # Trigger automated update if needed
    if data.get("security_update", False):
        plugin_manager.update_plugin(plugin_id)
```

## Update Verification

```python
from mcp_zero.sdk import PluginManager

# Verify update integrity
plugin_manager = PluginManager()
verification = plugin_manager.verify_plugin(
    plugin_id="data_processing",
    version="2.0.0"
)

if verification.signature_valid and verification.compatibility_verified:
    print("Update verified and compatible")
else:
    print(f"Update verification failed: {verification.reason}")
```
