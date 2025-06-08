"""
MCP-ZERO Agent Operations CLI Commands

Commands for operations on existing agents: execute, attach, snapshot, recover.
"""

import os
import json
import sys
import click
import yaml
from typing import Dict, Any, Optional

from ..client import MCPClient
from ..agents import AgentStatus
from ..exceptions import MCPError


@click.group(name="agent-ops")
def agent_ops_cmd():
    """Operations on existing agents."""
    pass


@agent_ops_cmd.command("attach")
@click.argument("agent_id")
@click.argument("plugin_id")
@click.pass_context
def attach_plugin(ctx, agent_id, plugin_id):
    """Attach a plugin to an existing agent."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent
            agent = client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent not found: {agent_id}", err=True)
                sys.exit(1)
            
            # Attach plugin
            success = agent.attach_plugin(plugin_id)
            
            if success:
                click.echo(f"Plugin {plugin_id} attached to agent {agent_id}")
            else:
                click.echo(f"Failed to attach plugin {plugin_id}", err=True)
                sys.exit(1)
            
            return success
    except Exception as e:
        click.echo(f"Error attaching plugin: {e}", err=True)
        sys.exit(1)


@agent_ops_cmd.command("execute")
@click.argument("agent_id")
@click.argument("intent")
@click.option("--param", "-p", multiple=True, help="Intent parameters in format key=value")
@click.option("--json-params", type=click.Path(exists=True), help="Load parameters from JSON file")
@click.option("--output", "-o", type=click.Path(), help="Save result to file")
@click.pass_context
def execute_intent(ctx, agent_id, intent, param, json_params, output):
    """Execute an intent on an agent."""
    try:
        # Prepare parameters
        parameters = {}
        
        # Process --param options
        for p in param:
            if "=" not in p:
                click.echo(f"Invalid parameter format: {p}", err=True)
                sys.exit(1)
            k, v = p.split("=", 1)
            parameters[k] = v
        
        # Process JSON parameters if provided
        if json_params:
            with open(json_params, "r") as f:
                json_data = json.load(f)
            if not isinstance(json_data, dict):
                click.echo("JSON parameters must be a dictionary", err=True)
                sys.exit(1)
            parameters.update(json_data)
        
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent
            agent = client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent not found: {agent_id}", err=True)
                sys.exit(1)
            
            # Execute intent
            result = agent.execute(intent, parameters)
            
            # Output result
            if output:
                with open(output, "w") as f:
                    json.dump(result, f, indent=2)
                click.echo(f"Result saved to {output}")
            else:
                click.echo(json.dumps(result, indent=2))
            
            return result
    except Exception as e:
        click.echo(f"Error executing intent: {e}", err=True)
        sys.exit(1)


@agent_ops_cmd.command("snapshot")
@click.argument("agent_id")
@click.option("--output", "-o", type=click.Path(), help="Save snapshot ID to file")
@click.pass_context
def snapshot_agent(ctx, agent_id, output):
    """Create a snapshot of an agent's state."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent
            agent = client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent not found: {agent_id}", err=True)
                sys.exit(1)
            
            # Take snapshot
            snapshot_id = agent.snapshot()
            
            click.echo(f"Snapshot created with ID: {snapshot_id}")
            
            # Save snapshot ID to file if requested
            if output:
                with open(output, "w") as f:
                    f.write(snapshot_id)
                click.echo(f"Snapshot ID saved to {output}")
            
            return snapshot_id
    except Exception as e:
        click.echo(f"Error creating snapshot: {e}", err=True)
        sys.exit(1)


@agent_ops_cmd.command("recover")
@click.argument("agent_id")
@click.option("--snapshot-id", help="Specific snapshot ID to recover from")
@click.pass_context
def recover_agent(ctx, agent_id, snapshot_id):
    """Recover an agent from a snapshot."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent
            agent = client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent not found: {agent_id}", err=True)
                sys.exit(1)
            
            # Recover from snapshot
            success = agent.recover(snapshot_id)
            
            if success:
                click.echo(f"Agent {agent_id} recovered successfully")
            else:
                click.echo("Recovery failed", err=True)
                sys.exit(1)
            
            return success
    except Exception as e:
        click.echo(f"Error recovering agent: {e}", err=True)
        sys.exit(1)


@agent_ops_cmd.command("status")
@click.argument("agent_id")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def agent_status(ctx, agent_id, json_output):
    """Get the current status of an agent."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent
            agent = client.get_agent(agent_id)
            if not agent:
                click.echo(f"Agent not found: {agent_id}", err=True)
                sys.exit(1)
            
            # Get agent info as dictionary
            agent_info = {
                "id": agent.id,
                "name": agent.name,
                "status": agent.status.value,
                "plugins": list(agent.plugins),
                "created_at": agent.created_at,
                "updated_at": agent.updated_at,
            }
            
            # Add resource usage
            agent_info["resources"] = agent.get_resource_usage()
            
            # Display results
            if json_output:
                click.echo(json.dumps(agent_info, indent=2))
            else:
                click.echo(f"Agent: {agent.name} ({agent.id})")
                click.echo(f"Status: {agent.status.value}")
                click.echo(f"Created: {agent.created_at}")
                click.echo(f"Updated: {agent.updated_at}")
                click.echo(f"Plugins: {', '.join(agent.plugins) if agent.plugins else 'None'}")
                
                resources = agent.get_resource_usage()
                click.echo("\nResource Usage:")
                click.echo(f"  CPU: {resources['cpu_percent']}% ({resources['cpu_utilization']}% of limit)")
                click.echo(f"  Memory: {resources['memory_mb']}MB ({resources['memory_utilization']}% of limit)")
            
            return agent_info
    except Exception as e:
        click.echo(f"Error getting agent status: {e}", err=True)
        sys.exit(1)
