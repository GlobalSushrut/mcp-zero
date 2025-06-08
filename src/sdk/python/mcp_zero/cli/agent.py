"""
MCP-ZERO Agent CLI Commands

Commands for managing agent lifecycle: spawn, attach_plugin, execute, snapshot, recover.
"""

import os
import json
import sys
import click
import yaml
from typing import Dict, Any

from ..client import MCPClient
from ..agents import AgentConfig, AgentStatus
from ..exceptions import MCPError


@click.group(name="agent")
def agent_cmd():
    """Agent lifecycle management commands."""
    pass


@agent_cmd.command("spawn")
@click.argument("config_file", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), help="Output file for agent ID")
@click.pass_context
def spawn_agent(ctx, config_file, output):
    """Spawn a new agent using configuration from YAML file."""
    try:
        # Load agent config
        with open(config_file, "r") as f:
            config_dict = yaml.safe_load(f)
        
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Create agent config
            agent_config = AgentConfig.from_dict(config_dict)
            
            # Spawn agent
            agent = client.spawn_agent(agent_config)
            
            click.echo(f"Agent spawned successfully with ID: {agent.id}")
            
            # Save agent ID to file if requested
            if output:
                with open(output, "w") as f:
                    f.write(agent.id)
                click.echo(f"Agent ID saved to {output}")
                
            return agent.id
    except Exception as e:
        click.echo(f"Error spawning agent: {e}", err=True)
        sys.exit(1)


@agent_cmd.command("list")
@click.option("--limit", type=int, default=100, help="Maximum number of agents to list")
@click.option("--offset", type=int, default=0, help="Offset for pagination")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_agents(ctx, limit, offset, json_output):
    """List available agents."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get agent list
            agents = client.list_agents(limit=limit, offset=offset)
            
            # Display results
            if json_output:
                click.echo(json.dumps(agents))
            else:
                if not agents:
                    click.echo("No agents found.")
                    return
                
                click.echo(f"Found {len(agents)} agents:")
                for agent_id in agents:
                    click.echo(f"- {agent_id}")
                    
            return agents
    except Exception as e:
        click.echo(f"Error listing agents: {e}", err=True)
        sys.exit(1)
