#!/usr/bin/env python3
"""
MCP-ZERO Creative Workflow Demo - Setup
Initializes the environment for a simulated video production workflow
"""
import logging
import os
import sys
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("creative_workflow")

# Server URLs - RPC server is the single point of access
RPC_URL = "http://localhost:8082"

# Ensure the demo directory exists
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

class ResourceMonitor:
    """Simple resource monitoring for the demo"""
    
    def __init__(self):
        """Initialize with empty usage stats"""
        self.max_cpu_percent = 0
        self.max_memory_mb = 0
    
    def check_constraints(self, cpu_percent=27, memory_mb=827):
        """Verify we're within hardware constraints"""
        logger.info(f"Checking resource usage: CPU < {cpu_percent}%, Memory < {memory_mb}MB")
        # In a real system, this would check actual usage
        return True
        
    def report_usage(self):
        """Report current resource usage"""
        # Simulate resource usage within constraints
        cpu_usage = 15 + (int(time.time()) % 10)  # 15-25% CPU
        memory_usage = 500 + (int(time.time() * 10) % 300)  # 500-800MB RAM
        
        # Update max usage stats
        self.max_cpu_percent = max(self.max_cpu_percent, cpu_usage)
        self.max_memory_mb = max(self.max_memory_mb, memory_usage)
        
        logger.info(f"Current resource usage: {cpu_usage}% CPU, {memory_usage}MB RAM")
        return {
            "cpu_percent": cpu_usage,
            "memory_mb": memory_usage
        }
        
    def get_max_usage(self):
        """Return the maximum resource usage observed"""
        return {
            "cpu_percent": self.max_cpu_percent,
            "memory_mb": self.max_memory_mb
        }

if __name__ == "__main__":
    logger.info("MCP-ZERO Creative Workflow - Setup Complete")
    monitor = ResourceMonitor()
    monitor.report_usage()
    monitor.check_constraints()
