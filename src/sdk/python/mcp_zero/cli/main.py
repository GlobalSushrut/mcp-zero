"""
MCP-ZERO CLI Main Module

Entry point for the MCP-ZERO command line interface.
"""

import os
import sys
import logging
import click

from ..utils.logging import setup_logger
from ..utils.config import load_config
from .agent import agent_cmd
from .agent_ops import agent_ops_cmd
from .plugin import plugin_cmd
from .system import system_cmd

# Setup logger
logger = logging.getLogger("mcp_zero.cli")

@click.group()
@click.option("--host", help="MCP-ZERO server hostname or IP")
@click.option("--port", type=int, help="MCP-ZERO server port")
@click.option("--config", type=click.Path(exists=True), help="Path to config file")
@click.option("--verbose", is_flag=True, help="Enable verbose logging")
@click.option("--quiet", is_flag=True, help="Suppress all output except errors")
@click.version_option(version="0.1.0")
@click.pass_context
def cli(ctx, host, port, config, verbose, quiet):
    """MCP-ZERO AI Agent Infrastructure CLI"""
    # Setup context object for sharing data between commands
    ctx.ensure_object(dict)
    
    # Load configuration
    cfg = load_config()
    
    # Override with explicit parameters
    if host:
        cfg["host"] = host
    if port:
        cfg["port"] = port
    
    # Configure logging
    log_level = "ERROR" if quiet else ("DEBUG" if verbose else "INFO")
    setup_logger(level=log_level)
    
    # Store config in context
    ctx.obj["config"] = cfg
    
    if verbose:
        logger.debug(f"Using configuration: {cfg}")


# Add all command groups
cli.add_command(agent_cmd)
cli.add_command(agent_ops_cmd)
cli.add_command(plugin_cmd)
cli.add_command(system_cmd)


@cli.command("version")
def version():
    """Show MCP-ZERO version information."""
    click.echo("MCP-ZERO v9")
    click.echo("Copyright © 2025 Windsurf Engineering Team")
    click.echo("AI Agent Infrastructure with Hardware Constraints & Ethical Governance")


@cli.command("init")
@click.option("--output", "-o", type=click.Path(), default="./mcp-zero.yaml",
              help="Output config file path")
def init_config(output):
    """Initialize a new MCP-ZERO configuration file."""
    from ..utils.config import save_config_to_file
    
    # Create default config
    config = {
        "host": "localhost",
        "port": 50051,
        "timeout": 10.0,
        "log_level": "INFO",
    }
    
    # Save config
    try:
        save_config_to_file(config, output)
        click.echo(f"Created MCP-ZERO config file: {output}")
    except Exception as e:
        click.echo(f"Error creating config file: {e}", err=True)
        sys.exit(1)
        

def main():
    """Main entry point for CLI."""
    try:
        cli(obj={})
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
