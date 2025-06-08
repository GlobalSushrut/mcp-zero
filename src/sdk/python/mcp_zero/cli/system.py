"""
MCP-ZERO System CLI Commands

Commands for system management: status, resource monitoring, and infrastructure operations.
"""

import os
import json
import sys
import time
import click
from typing import Dict, Any, List

from ..client import MCPClient
from ..exceptions import MCPError


@click.group(name="system")
def system_cmd():
    """System management commands."""
    pass


@system_cmd.command("status")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
@click.pass_context
def system_status(ctx, json_output):
    """Get MCP-ZERO system status."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            # Get system status
            status = client.get_system_status()
            
            # Display results
            if json_output:
                click.echo(json.dumps(status))
            else:
                click.echo(f"MCP-ZERO Status: {status['status']}")
                click.echo(f"Version: {status.get('version', 'unknown')}")
                
                if "uptime" in status:
                    click.echo(f"Uptime: {status['uptime']} seconds")
                
                if "resources" in status:
                    res = status["resources"]
                    click.echo("\nResource Usage:")
                    click.echo(f"  CPU: {res.get('cpu_percent', 0)}% of limit")
                    click.echo(f"  Memory: {res.get('memory_mb', 0)}MB of {res.get('memory_limit_mb', 0)}MB")
                
                if "agents" in status:
                    click.echo(f"\nActive Agents: {status['agents'].get('active', 0)}")
                    click.echo(f"Total Agents: {status['agents'].get('total', 0)}")
                
                if "plugins" in status:
                    click.echo(f"\nLoaded Plugins: {status['plugins'].get('loaded', 0)}")
                    click.echo(f"Registered Plugins: {status['plugins'].get('registered', 0)}")
            
            return status
    except Exception as e:
        click.echo(f"Error getting system status: {e}", err=True)
        sys.exit(1)


@system_cmd.command("resources")
@click.option("--watch", "-w", is_flag=True, help="Continuously monitor resources")
@click.option("--interval", type=float, default=2.0, help="Update interval for watch mode (seconds)")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format (disables watch)")
@click.pass_context
def system_resources(ctx, watch, interval, json_output):
    """Monitor system resource usage."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            if watch and not json_output:
                # Watch mode
                try:
                    while True:
                        # Clear screen (Unix/Windows compatible)
                        click.clear()
                        
                        # Get resource stats
                        stats = client.get_resource_stats()
                        
                        # Display header
                        click.echo("MCP-ZERO Resource Monitor")
                        click.echo("=" * 40)
                        click.echo(f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
                        click.echo("=" * 40)
                        
                        # Display CPU info
                        click.echo("\nCPU Usage:")
                        click.echo(f"  System: {stats.get('system_cpu_percent', 0)}%")
                        click.echo(f"  MCP-ZERO: {stats.get('cpu_percent', 0)}%")
                        click.echo(f"  Limit: {stats.get('cpu_limit_percent', 30)}%")
                        
                        # Display memory info
                        click.echo("\nMemory Usage:")
                        click.echo(f"  Used: {stats.get('memory_mb', 0):.1f}MB")
                        click.echo(f"  Limit: {stats.get('memory_limit_mb', 1000)}MB")
                        click.echo(f"  Utilization: {stats.get('memory_utilization', 0):.1f}%")
                        
                        # Display load info if available
                        if "load_avg" in stats:
                            click.echo("\nLoad Average:")
                            load = stats["load_avg"]
                            click.echo(f"  1 min: {load[0]:.2f}")
                            click.echo(f"  5 min: {load[1]:.2f}")
                            click.echo(f"  15 min: {load[2]:.2f}")
                        
                        # Display agent count if available
                        if "agent_count" in stats:
                            click.echo(f"\nActive Agents: {stats['agent_count']}")
                        
                        click.echo("\nPress Ctrl+C to exit")
                        
                        # Wait for next update
                        time.sleep(interval)
                except KeyboardInterrupt:
                    click.echo("\nMonitoring stopped")
                    return
            else:
                # Single view or JSON output
                stats = client.get_resource_stats()
                
                if json_output:
                    click.echo(json.dumps(stats))
                else:
                    click.echo("MCP-ZERO Resource Stats:")
                    click.echo(f"  CPU Usage: {stats.get('cpu_percent', 0)}% (limit: {stats.get('cpu_limit_percent', 30)}%)")
                    click.echo(f"  Memory: {stats.get('memory_mb', 0):.1f}MB (limit: {stats.get('memory_limit_mb', 1000)}MB)")
                    click.echo(f"  Memory Utilization: {stats.get('memory_utilization', 0):.1f}%")
                    
                    if "agent_count" in stats:
                        click.echo(f"  Active Agents: {stats['agent_count']}")
                
                return stats
    except Exception as e:
        click.echo(f"Error monitoring resources: {e}", err=True)
        sys.exit(1)


@system_cmd.command("logs")
@click.option("--tail", "-t", is_flag=True, help="Tail logs (follow)")
@click.option("--lines", "-n", type=int, default=50, help="Number of lines to show")
@click.option("--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]), 
              help="Minimum log level")
@click.pass_context
def system_logs(ctx, tail, lines, level):
    """View system logs."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            if tail:
                try:
                    for log_entry in client.tail_logs(level=level):
                        click.echo(log_entry)
                except KeyboardInterrupt:
                    click.echo("\nLog viewing stopped")
                    return
            else:
                logs = client.get_logs(lines=lines, level=level)
                for log_entry in logs:
                    click.echo(log_entry)
                
                return logs
    except Exception as e:
        click.echo(f"Error viewing logs: {e}", err=True)
        sys.exit(1)


@system_cmd.command("health")
@click.pass_context
def system_health(ctx):
    """Check system health status."""
    try:
        # Create client connection
        with MCPClient(**ctx.obj["config"]) as client:
            health = client.check_health()
            
            if health.get("status") == "ok":
                click.echo("System health status: OK")
                click.echo(f"API Version: {health.get('api_version', 'unknown')}")
                if "checks" in health:
                    click.echo("\nComponent Status:")
                    for component, status in health["checks"].items():
                        status_str = "✓ OK" if status else "✗ FAIL"
                        click.echo(f"  {component}: {status_str}")
                return 0
            else:
                click.echo("System health status: DEGRADED", err=True)
                click.echo(f"API Version: {health.get('api_version', 'unknown')}")
                if "checks" in health:
                    click.echo("\nComponent Status:")
                    for component, status in health["checks"].items():
                        status_str = "✓ OK" if status else "✗ FAIL"
                        click.echo(f"  {component}: {status_str}")
                
                # Non-zero exit code for failed health check
                sys.exit(1)
    except Exception as e:
        click.echo(f"Error checking health: {e}", err=True)
        sys.exit(2)
