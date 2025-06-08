"""
MCP-ZERO Client Module

Provides the main client interface for interacting with MCP-ZERO services.
"""

import os
import time
import logging
import threading
from typing import Dict, List, Optional, Any, Callable, Union

from .exceptions import ConnectionError, MCPError
from .agents import Agent, AgentConfig, AgentStatus
from .plugins import Plugin, PluginCapabilities
from .utils.config import ClientConfig, load_config_from_file
from .utils.logging import setup_logger
from .http_adapter import HttpAdapter

# Setup logger
logger = logging.getLogger("mcp_zero.client")

class MCPClient:
    """
    Main client interface for MCP-ZERO.
    
    Provides methods to interact with the MCP-ZERO infrastructure,
    including agent lifecycle management, plugin registration, and
    intent execution.
    
    Args:
        host: The hostname or IP address of the MCP-ZERO RPC server.
        port: The port of the MCP-ZERO RPC server.
        config_path: Path to a configuration file.
        secure: Whether to use a secure connection (TLS).
        timeout: Default timeout for operations in seconds.
    """
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        config_path: Optional[str] = None,
        secure: bool = False,
        timeout: float = 10.0,
        http_port: Optional[int] = None,
    ):
        self._config = ClientConfig()
        
        # Load from config file if provided
        if config_path:
            config_from_file = load_config_from_file(config_path)
            self._config.update(config_from_file)
            
        # Override with explicit parameters
        if host:
            self._config.host = host
        if port:
            self._config.port = port
        if timeout:
            self._config.timeout = timeout
            
        # Use environment variables as fallback
        self._config.host = self._config.host or os.environ.get("MCP_HOST", "localhost")
        self._config.port = self._config.port or int(os.environ.get("MCP_PORT", "50051"))
        
        # HTTP API port for Go RPC server (default 8081)
        self._http_port = http_port or int(os.environ.get("MCP_HTTP_PORT", "8081"))
        
        # Setup secure connection
        self._secure = secure
        
        # Connection state
        self._http_adapter = HttpAdapter(
            host=self._config.host,
            port=self._http_port,
            secure=self._secure,
            timeout=self._config.timeout
        )
        
        # Event monitoring
        self._event_thread = None
        self._event_handlers = {}
        self._stop_event = threading.Event()
        
        # Configure logging
        setup_logger(self._config.log_level, self._config.log_file)
        
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
        
    def connect(self) -> None:
        """
        Connect to MCP-ZERO server.
        
        Raises:
            ConnectionError: If connection fails.
        """
        if self._http_adapter.is_connected():
            logger.info("Already connected to MCP-ZERO")
            return
            
        try:
            logger.info(f"Connecting to MCP-ZERO HTTP API at {self._config.host}:{self._http_port}")
            self._http_adapter.connect()
        except Exception as e:
            raise ConnectionError(f"Failed to connect to MCP-ZERO: {e}")
            
    def disconnect(self) -> None:
        """Disconnect from MCP-ZERO server."""
        if self._http_adapter.is_connected():
            logger.info("Disconnecting from MCP-ZERO")
            
            # Stop event monitoring if active
            self.stop_event_monitoring()
            
            # Close the HTTP adapter
            self._http_adapter.disconnect()
            
    def is_connected(self) -> bool:
        """Check if connected to MCP-ZERO."""
        return self._http_adapter.is_connected()
        
    def _init_stubs(self) -> None:
        """Initialize gRPC service stubs."""
        # Will be implemented after protobuf generation
        # self._stubs["agent"] = mcp_pb2_grpc.MCPAgentServiceStub(self._channel)
        # self._stubs["hardware"] = mcp_pb2_grpc.MCPHardwareServiceStub(self._channel)
        # self._stubs["plugin"] = mcp_pb2_grpc.MCPPluginServiceStub(self._channel)
        pass
        
    def spawn_agent(self, config: Union[AgentConfig, Dict]) -> Agent:
        """
        Spawn a new agent with the given configuration.
        
        Args:
            config: Agent configuration.
            
        Returns:
            An Agent instance.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If agent creation fails.
        """
        if not self.is_connected():
            self.connect()
        
        # Convert to AgentConfig if dict provided
        if isinstance(config, dict):
            config = AgentConfig.from_dict(config)
        
        try:
            # Use HTTP adapter to make the API call
            result = self._http_adapter.spawn_agent(config.to_dict())
            agent_id = result.get("agent_id")
            if not agent_id:
                raise AgentError("Invalid response from server: missing agent_id")
                
            agent = Agent(self, agent_id, config)
            logger.info(f"Agent spawned with ID: {agent_id}")
            return agent
        except Exception as e:
            logger.error(f"Failed to spawn agent: {e}")
            raise AgentError(f"Failed to spawn agent: {e}")
        
    def load_agent(self, agent_id: str) -> Agent:
        """
        Load an existing agent by ID.
        
        Args:
            agent_id: The ID of the agent to load.
            
        Returns:
            An Agent instance.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If agent doesn't exist or fails to load.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to MCP-ZERO")
            
        logger.info(f"Loading agent with ID: {agent_id}")
        
        # Will be implemented after protobuf generation
        # request = mcp_pb2.GetAgentInfoRequest(agent_id=agent_id)
        # response = self._stubs["agent"].GetAgentInfo(request, timeout=self._config.timeout)
        # 
        # if not response.success:
        #     raise AgentError(f"Failed to load agent: {response.error}")
        # 
        # config = AgentConfig.from_proto(response.config)
        # return Agent(self, agent_id, config, status=response.status)
        
        # Placeholder implementation
        config = AgentConfig(name=f"agent-{agent_id}", entry_plugin="core")
        return Agent(self, agent_id, config, status=AgentStatus.ACTIVE)
        
    def list_agents(self, limit: int = 100, offset: int = 0) -> List[str]:
        """
        List available agent IDs.
        
        Args:
            limit: Maximum number of agents to return.
            offset: Offset for pagination.
            
        Returns:
            List of agent IDs.
            
        Raises:
            ConnectionError: If not connected.
            MCPError: On RPC failure.
        """
        if not self.is_connected():
            self.connect()
            
        try:
            # Use HTTP adapter to make the API call
            return self._http_adapter.list_agents(limit=limit, offset=offset)
        except Exception as e:
            logger.error(f"Failed to list agents: {e}")
            raise MCPError(f"Failed to list agents: {e}")     
    def register_plugin(
        self,
        plugin_id: str,
        wasm_path: str,
        capabilities: Union[PluginCapabilities, Dict],
        metadata: Dict[str, str] = None
    ) -> bool:
        """
        Register a new plugin.
        
        Args:
            plugin_id: Plugin ID.
            wasm_path: Path to WASM module file.
            capabilities: Plugin capabilities.
            metadata: Plugin metadata.
            
        Returns:
            True on success.
            
        Raises:
            ConnectionError: If not connected.
            PluginError: If plugin registration fails.
            FileNotFoundError: If WASM file not found.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to MCP-ZERO")
            
        # Convert dict to PluginCapabilities if needed
        if isinstance(capabilities, dict):
            capabilities = PluginCapabilities.from_dict(capabilities)
            
        logger.info(f"Registering plugin: {plugin_id}")
        
        # Read WASM file
        try:
            with open(wasm_path, 'rb') as f:
                wasm_module = f.read()
        except FileNotFoundError:
            raise FileNotFoundError(f"WASM file not found: {wasm_path}")
            
        # Will be implemented after protobuf generation
        # plugin_metadata = mcp_pb2.PluginMetadata(
        #     name=plugin_id,
        #     version=metadata.get("version", "0.1.0"),
        #     author=metadata.get("author", "unknown"),
        #     description=metadata.get("description", ""),
        #     additional=metadata or {},
        # )
        # 
        # request = mcp_pb2.RegisterPluginRequest(
        #     plugin_id=plugin_id,
        #     capabilities=capabilities.to_proto(),
        #     metadata=plugin_metadata,
        #     wasm_module=wasm_module,
        # )
        # 
        # response = self._stubs["plugin"].RegisterPlugin(request, timeout=self._config.timeout)
        # 
        # if not response.success:
        #     raise PluginError(f"Failed to register plugin: {response.error}")
        # 
        # return True
        
        # Placeholder implementation
        return True
        
    def start_event_monitoring(self, agent_id: str = None) -> None:
        """
        Start monitoring events from MCP-ZERO.
        
        Args:
            agent_id: Optional agent ID to filter events.
            
        Raises:
            ConnectionError: If not connected.
        """
        if not self.is_connected():
            raise ConnectionError("Not connected to MCP-ZERO")
            
        if self._event_thread and self._event_thread.is_alive():
            logger.warning("Event monitoring already active")
            return
            
        logger.info("Starting event monitoring")
        self._stop_event = threading.Event()
        self._event_thread = threading.Thread(
            target=self._event_monitor_loop,
            args=(agent_id,),
            daemon=True
        )
        self._event_thread.start()
        
    def stop_event_monitoring(self) -> None:
        """Stop monitoring events."""
        if not self._event_thread or not self._event_thread.is_alive():
            return
            
        logger.info("Stopping event monitoring")
        self._stop_event.set()
        self._event_thread.join(timeout=2.0)
        
    def _event_monitor_loop(self, agent_id: Optional[str]) -> None:
        """Event monitoring loop."""
        # Will be implemented after protobuf generation
        # try:
        #     request = mcp_pb2.StreamEventsRequest(
        #         agent_id=agent_id or "",
        #         buffer_size=100
        #     )
        #     
        #     for event in self._stubs["agent"].StreamEvents(request):
        #         if self._stop_event.is_set():
        #             break
        #             
        #         # Process event
        #         self._process_event(event)
        #         
        # except grpc.RpcError as e:
        #     logger.error(f"Event stream error: {e}")
        # finally:
        #     logger.info("Event monitoring stopped")
        pass
        
    def _process_event(self, event) -> None:
        """Process an event and dispatch to registered handlers."""
        # Will be implemented after protobuf generation
        # event_type = event.event_type
        # 
        # # Call all handlers registered for this event type
        # for handler in self._event_handlers.get(event_type, []):
        #     try:
        #         handler(event)
        #     except Exception as e:
        #         logger.error(f"Error in event handler: {e}")
        pass
        
    def on_event(self, event_type: str, handler: Callable) -> None:
        """
        Register an event handler.
        
        Args:
            event_type: Type of event to handle.
            handler: Callback function that takes an event parameter.
        """
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = []
        self._event_handlers[event_type].append(handler)
        
    def off_event(self, event_type: str, handler: Optional[Callable] = None) -> None:
        """
        Unregister an event handler.
        
        Args:
            event_type: Type of event.
            handler: Handler to remove. If None, removes all handlers for this type.
        """
        if event_type not in self._event_handlers:
            return
            
        if handler is None:
            self._event_handlers[event_type] = []
        else:
            self._event_handlers[event_type] = [
                h for h in self._event_handlers[event_type] if h != handler
            ]
