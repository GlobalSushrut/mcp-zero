"""
Resilient Integration Example for MCP Zero

This module demonstrates how to integrate our newly implemented resilient
components together to create a robust industry-grade system, following
the same resilience patterns as DBMemoryTree and Traffic Agent.
"""

import os
import time
import logging
from typing import Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

logger = logging.getLogger("mcp_zero.examples.resilient_integration")

# Import our resilient components
from src.api import telemetry_collector
from src.api import tracing
from src.api import metrics
from src.api import health_checker
from src.security import audit_logger
from src.security import rate_limiter
from src.kernel import config_manager


class ResilientAgent:
    """
    Example agent that demonstrates the integration of industry-grade
    resilient components in MCP Zero.
    
    This follows the same patterns used in DBMemoryTree and Traffic Agent:
    - Start in offline mode by default
    - Single connection attempt to external services
    - Graceful fallback to local processing if services are unavailable
    - No repeated connection attempts that could cause error cascades
    """
    
    def __init__(
        self,
        agent_id: str,
        services_host: Optional[str] = None,
        offline_dir: str = "/var/lib/mcp-zero/agent_data"
    ):
        """
        Initialize resilient agent with industry-grade observability and security.
        
        Args:
            agent_id: Unique agent identifier
            services_host: Host for centralized services (None for offline only)
            offline_dir: Base directory for offline data storage
        """
        self.agent_id = agent_id
        self.services_host = services_host
        self.offline_dir = offline_dir
        
        # Ensure base directories exist
        os.makedirs(offline_dir, exist_ok=True)
        
        # Configure service URLs if host is provided
        telemetry_url = f"http://{services_host}/telemetry" if services_host else None
        traces_url = f"http://{services_host}/traces" if services_host else None
        metrics_url = f"http://{services_host}/metrics" if services_host else None
        audit_url = f"http://{services_host}/audit" if services_host else None
        config_url = f"http://{services_host}/config" if services_host else None
        
        # Initialize components with offline-first approach
        logger.info(f"Initializing resilient agent {agent_id}")
        
        # 1. Config first (needed by other components)
        logger.info("Initializing configuration manager")
        self.config = config_manager.init(
            component_name=f"agent_{agent_id}",
            config_server=config_url,
            local_dir=f"{offline_dir}/config"
        )
        
        # 2. Telemetry (foundation for other observability)
        logger.info("Initializing telemetry collector")
        self.telemetry = telemetry_collector.initialize(
            component_name=f"agent_{agent_id}",
            server_url=telemetry_url,
            cache_dir=f"{offline_dir}/telemetry"
        )
        
        # 3. Metrics
        logger.info("Initializing metrics collector")
        self.metrics = metrics.init(
            component_name=f"agent_{agent_id}", 
            endpoint=metrics_url
        )
        
        # 4. Tracing
        logger.info("Initializing distributed tracing")
        self.tracer = tracing.init(
            service_name=f"agent_{agent_id}",
            collector_url=traces_url,
            offline_dir=f"{offline_dir}/traces"
        )
        
        # 5. Security audit logger
        logger.info("Initializing security audit logger")
        self.audit = audit_logger.init(
            service_name=f"agent_{agent_id}",
            audit_server=audit_url,
            offline_dir=f"{offline_dir}/audit"
        )
        
        # 6. Rate limiters
        logger.info("Initializing rate limiters")
        self.api_limiter = rate_limiter.create_limiter(
            name=f"agent_{agent_id}_api",
            requests_per_period=100,
            period_seconds=60
        )
        
        # 7. Health checker
        logger.info("Initializing health checker")
        self.health = health_checker.init(
            service_name=f"agent_{agent_id}",
            metrics_collector=self.metrics
        )
        
        # Register health checks
        self._register_health_checks()
        
        # Record successful initialization
        telemetry_collector.record(
            "agent.init",
            agent_id=agent_id,
            mode=self.telemetry.mode.value
        )
        
        # Create relevant metrics
        self.requests_counter = metrics.counter(
            "requests_total",
            "Total number of requests processed"
        )
        self.error_counter = metrics.counter(
            "errors_total",
            "Total number of errors encountered"
        )
        self.processing_time = metrics.gauge(
            "processing_time_seconds",
            "Time taken to process requests"
        )
        
        logger.info(f"Agent {agent_id} initialized with resilient components")
        
        # Log audit event for agent creation
        audit_logger.security_event(
            f"Agent {agent_id} initialized with resilient industry-grade components"
        )
    
    def _register_health_checks(self):
        """Register health checks for dependencies."""
        # Local database check
        health_checker.register_check(
            "local_storage",
            check_fn=self._check_local_storage,
            is_critical=True,
            requires_network=False
        )
        
        # Plugin system check
        health_checker.register_check(
            "plugin_system",
            check_fn=self._check_plugin_system,
            is_critical=True,
            requires_network=False
        )
        
        # Config check
        health_checker.register_check(
            "configuration",
            check_fn=self._check_configuration,
            is_critical=True,
            requires_network=False
        )
        
        # Remote service check (if in online mode)
        if self.services_host:
            health_checker.register_check(
                "services_connection",
                check_fn=self._check_remote_services,
                is_critical=False,
                requires_network=True
            )
    
    def _check_local_storage(self) -> bool:
        """Health check for local storage."""
        try:
            test_file = f"{self.offline_dir}/health_check.tmp"
            with open(test_file, 'w') as f:
                f.write("test")
            os.remove(test_file)
            return True
        except Exception:
            return False
    
    def _check_plugin_system(self) -> bool:
        """Health check for plugin system."""
        # Simplified - just check if the plugins directory exists
        plugins_dir = f"{self.offline_dir}/plugins"
        os.makedirs(plugins_dir, exist_ok=True)
        return os.path.exists(plugins_dir)
    
    def _check_configuration(self) -> bool:
        """Health check for configuration system."""
        try:
            # Try to get a configuration value
            self.config.get("health_check_key", "default")
            return True
        except Exception:
            return False
    
    def _check_remote_services(self) -> bool:
        """Health check for remote services."""
        if not self.services_host:
            return False
            
        try:
            import socket
            # Simple connectivity test
            socket.create_connection((self.services_host, 80), timeout=2)
            return True
        except Exception:
            return False
    
    def process_request(self, request_id: str, client_id: str, data: dict) -> dict:
        """
        Process a request with full observability and security.
        
        Args:
            request_id: Unique request identifier
            client_id: Client identifier for rate limiting
            data: Request data
            
        Returns:
            Response data
        """
        # 1. Rate limiting check
        if not self.api_limiter.allow_request(client_id):
            audit_logger.access_denied(
                user_id=client_id,
                resource_id=self.agent_id,
                message=f"Rate limit exceeded for request {request_id}"
            )
            return {"error": "Rate limit exceeded"}
        
        # 2. Start tracing and timing
        start_time = time.time()
        with tracing.start_span(f"process_request") as span:
            span.set_tag("request_id", request_id)
            span.set_tag("client_id", client_id)
            
            try:
                # 3. Record telemetry for this request
                telemetry_collector.record(
                    "request.received",
                    request_id=request_id,
                    client_id=client_id,
                    request_type=data.get("type", "unknown")
                )
                
                # 4. Update metrics
                self.requests_counter.inc()
                
                # 5. Log audit event for access
                audit_logger.data_accessed(
                    user_id=client_id,
                    resource_id=self.agent_id,
                    message=f"Processing request {request_id}",
                    metadata={"request_type": data.get("type", "unknown")}
                )
                
                # 6. Actual request processing (simplified for example)
                span.log("processing", {"stage": "started"})
                
                # Simulate processing
                time.sleep(0.1)
                response = {
                    "request_id": request_id,
                    "status": "success",
                    "result": f"Processed by agent {self.agent_id}",
                    "timestamp": time.time()
                }
                
                span.log("processing", {"stage": "completed"})
                
                # 7. Record successful completion
                telemetry_collector.record(
                    "request.completed",
                    request_id=request_id,
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True
                )
                
                return response
                
            except Exception as e:
                # 8. Error handling with full observability
                error_msg = str(e)
                logger.error(f"Error processing request {request_id}: {error_msg}")
                
                # Update span
                span.set_tag("error", True)
                span.set_tag("error.message", error_msg)
                
                # Update metrics
                self.error_counter.inc()
                
                # Record telemetry
                telemetry_collector.record(
                    "request.error",
                    request_id=request_id,
                    error=error_msg
                )
                
                # Audit log
                audit_logger.security_event(
                    f"Error processing request {request_id}: {error_msg}",
                    severity=audit_logger.AuditSeverity.ERROR,
                    user_id=client_id,
                    resource_id=self.agent_id
                )
                
                return {"error": "Internal processing error"}
                
            finally:
                # 9. Always update timing metric
                duration = time.time() - start_time
                self.processing_time.set(duration)


def main():
    """Example usage of resilient agent."""
    # Initialize agent in offline mode for demonstration
    agent = ResilientAgent(
        agent_id="demo_agent_123",
        services_host=None  # Offline mode
    )
    
    # Process some requests
    for i in range(5):
        response = agent.process_request(
            request_id=f"req_{i}",
            client_id="test_client",
            data={"type": "test_request", "value": i}
        )
        print(f"Request {i} response: {response}")
    
    # Get health status
    health = health_checker.get_status(force_check=True)
    print(f"Health status: {health['status']}")
    
    # Flush telemetry, metrics, traces and audit logs
    telemetry_collector.flush()
    metrics.export()
    tracing.flush()
    audit_logger.flush()


if __name__ == "__main__":
    main()
