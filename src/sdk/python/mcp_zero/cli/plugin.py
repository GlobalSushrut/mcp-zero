"""
MCP-ZERO Plugin CLI Commands

Commands for managing plugins: register, list, info.
"""

import os
import json
import sys
import click
import yaml
from typing import Dict, Any, List

from ..client import MCPClient
from ..plugins import Plugin, PluginCapabilities
from ..exceptions import PluginError


@click.group(name="plugin")
def plugin_cmd():
    """Plugin management commands."""
    pass


@plugin_cmd.command("register")
@click.argument("config_file", type=click.Path(exists=True))
@click.pass_context
def register_plugin(ctx, config_file):
    """Register a new plugin using configuration from YAML file."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Load plugin from YAML
            plugin = Plugin.from_yaml(client, config_file)
            
            # Register plugin
            success = plugin.register()
            
            if success:
                click.echo(f"Plugin {plugin.id} registered successfully")
                
                # Display capabilities
                click.echo("\nCapabilities:")
                click.echo(f"  State Access: {'Yes' if plugin.capabilities.state_access else 'No'}")
                click.echo(f"  Plugin Call: {'Yes' if plugin.capabilities.plugin_call else 'No'}")
                click.echo(f"  External Access: {'Yes' if plugin.capabilities.external_access else 'No'}")
                click.echo(f"  CPU Limit: {plugin.capabilities.cpu_limit}%")
                click.echo(f"  Memory Limit: {plugin.capabilities.memory_limit}MB")
            else:
                click.echo("Failed to register plugin", err=True)
                sys.exit(1)
            
            return success
    except Exception as e:
        click.echo(f"Error registering plugin: {e}", err=True)
        sys.exit(1)


@plugin_cmd.command("list")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_plugins(ctx, json_output):
    """List available plugins."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get plugin list
            plugins = client.list_plugins()
            
            # Display results
            if json_output:
                click.echo(json.dumps(plugins))
            else:
                if not plugins:
                    click.echo("No plugins found.")
                    return
                
                click.echo(f"Found {len(plugins)} plugins:")
                for plugin_id in plugins:
                    click.echo(f"- {plugin_id}")
            
            return plugins
    except Exception as e:
        click.echo(f"Error listing plugins: {e}", err=True)
        sys.exit(1)


@plugin_cmd.command("info")
@click.argument("plugin_id")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def plugin_info(ctx, plugin_id, json_output):
    """Get detailed information about a plugin."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get plugin
            plugin_info = client.get_plugin_info(plugin_id)
            
            if not plugin_info:
                click.echo(f"Plugin not found: {plugin_id}", err=True)
                sys.exit(1)
            
            # Display results
            if json_output:
                click.echo(json.dumps(plugin_info))
            else:
                click.echo(f"Plugin: {plugin_info.get('name', plugin_id)} ({plugin_id})")
                click.echo(f"Version: {plugin_info.get('version', 'unknown')}")
                click.echo(f"Author: {plugin_info.get('author', 'unknown')}")
                click.echo(f"Description: {plugin_info.get('description', '')}")
                
                if "hash" in plugin_info:
                    click.echo(f"Hash: {plugin_info.get('hash')}")
                
                if "capabilities" in plugin_info:
                    caps = plugin_info["capabilities"]
                    click.echo("\nCapabilities:")
                    click.echo(f"  State Access: {'Yes' if caps.get('state_access') else 'No'}")
                    click.echo(f"  Plugin Call: {'Yes' if caps.get('plugin_call') else 'No'}")
                    click.echo(f"  External Access: {'Yes' if caps.get('external_access') else 'No'}")
                    click.echo(f"  CPU Limit: {caps.get('cpu_limit', 'unknown')}%")
                    click.echo(f"  Memory Limit: {caps.get('memory_limit', 'unknown')}MB")
            
            return plugin_info
    except Exception as e:
        click.echo(f"Error getting plugin info: {e}", err=True)
        sys.exit(1)


@plugin_cmd.command("create-config")
@click.argument("plugin_id")
@click.argument("wasm_path", type=click.Path(exists=True))
@click.option("--output", "-o", type=click.Path(), required=True, help="Output config file path")
@click.option("--state-access/--no-state-access", default=False, help="Allow access to agent state")
@click.option("--plugin-call/--no-plugin-call", default=False, help="Allow calling other plugins")
@click.option("--external-access/--no-external-access", default=False, help="Allow external resource access")
@click.option("--cpu-limit", type=float, default=5.0, help="Maximum CPU percentage")
@click.option("--memory-limit", type=int, default=50, help="Maximum memory in MB")
@click.option("--name", help="Plugin name")
@click.option("--version", default="0.1.0", help="Plugin version")
@click.option("--author", help="Plugin author")
@click.option("--description", help="Plugin description")
@click.pass_context
def create_plugin_config(ctx, plugin_id, wasm_path, output, state_access, plugin_call, 
                        external_access, cpu_limit, memory_limit, name, version, 
                        author, description):
    """Create a plugin configuration file for registration."""
    try:
        # Create capabilities
        capabilities = {
            "state_access": state_access,
            "plugin_call": plugin_call,
            "external_access": external_access,
            "cpu_limit": cpu_limit,
            "memory_limit": memory_limit,
        }
        
        # Create metadata
        metadata = {
            "name": name or plugin_id,
            "version": version,
            "author": author or "unknown",
            "description": description or "",
        }
        
        # Create config
        config = {
            "id": plugin_id,
            "capabilities": capabilities,
            "metadata": metadata,
            "wasm_path": os.path.abspath(wasm_path),
        }
        
        # Write to file
        with open(output, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
        
        click.echo(f"Plugin configuration saved to {output}")
        
        return True
    except Exception as e:
        click.echo(f"Error creating plugin config: {e}", err=True)
        sys.exit(1)
