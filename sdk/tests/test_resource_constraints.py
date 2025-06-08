#!/usr/bin/env python3
"""
MCP-ZERO SDK: Resource Constraints Tests

This module tests that the SDK adheres to MCP-ZERO's strict hardware constraints:
- CPU: <27% on a single core
- Memory: <827MB

These tests include load testing and simulated agent operations to ensure
resource efficiency even under stress conditions.
"""

import os
import sys
import unittest
import time
import threading
import gc
from typing import List

# Add the SDK to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_zero import Agent, ResourceMonitor
from mcp_zero.exceptions import ResourceLimitError

# Try to import psutil (optional dependency)
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class ResourceConstraintsTest(unittest.TestCase):
    """Test case for verifying SDK resource constraints"""

    @classmethod
    def setUpClass(cls):
        """Set up for all tests"""
        # Skip tests if psutil is not available
        if not HAS_PSUTIL:
            raise unittest.SkipTest("psutil not available, skipping resource constraint tests")
        
        # Create a resource monitor
        cls.monitor = ResourceMonitor()
        cls.monitor.start_monitoring()
        
        # Set environment variables
        os.environ["MCP_TESTING_MODE"] = "1"
        os.environ["MCP_LOW_CPU_MODE"] = "1"
        
        # Perform GC to start with clean state
        gc.collect()
        time.sleep(0.5)  # Allow for cleanup

    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests"""
        # Stop monitoring
        cls.monitor.stop_monitoring()
        
        # Clean up environment variables
        if "MCP_TESTING_MODE" in os.environ:
            del os.environ["MCP_TESTING_MODE"]
        if "MCP_LOW_CPU_MODE" in os.environ:
            del os.environ["MCP_LOW_CPU_MODE"]

    def setUp(self):
        """Set up before each test"""
        # Perform GC before each test
        gc.collect()
        time.sleep(0.5)  # Allow for cleanup

    def test_idle_cpu_usage(self):
        """Test CPU usage when idle"""
        # Wait for any initialization to complete
        time.sleep(1.0)
        
        # Get initial CPU usage
        initial_cpu = self.monitor.get_cpu_percent()
        
        # Allow 5 seconds of idle time
        time.sleep(5.0)
        
        # Get final CPU usage
        final_cpu = self.monitor.get_cpu_percent()
        
        # Calculate average (simple approximation)
        avg_cpu = (initial_cpu + final_cpu) / 2
        
        # Check constraint
        self.assertLess(avg_cpu, 27.0, f"Idle CPU usage too high: {avg_cpu:.1f}%")
        print(f"Idle CPU usage: {avg_cpu:.1f}% (limit: 27.0%)")

    def test_idle_memory_usage(self):
        """Test memory usage when idle"""
        # Wait for any initialization to complete
        time.sleep(1.0)
        
        # Get memory usage
        memory_mb = self.monitor.get_memory_mb()
        
        # Check constraint
        self.assertLess(memory_mb, 827.0, f"Idle memory usage too high: {memory_mb:.1f}MB")
        print(f"Idle memory usage: {memory_mb:.1f}MB (limit: 827.0MB)")

    def test_agent_creation_resource_usage(self):
        """Test resource usage during agent creation"""
        # Get initial metrics
        initial_cpu = self.monitor.get_cpu_percent()
        initial_memory = self.monitor.get_memory_mb()
        
        # Create a test agent
        start_time = time.time()
        agent = Agent.spawn(name="test-resource-agent")
        elapsed = time.time() - start_time
        
        # Get metrics after creation
        post_cpu = self.monitor.get_cpu_percent()
        post_memory = self.monitor.get_memory_mb()
        
        # Calculate changes
        cpu_change = post_cpu - initial_cpu
        memory_change = post_memory - initial_memory
        
        # Check constraints
        self.assertLess(post_cpu, 27.0, f"CPU usage too high during agent creation: {post_cpu:.1f}%")
        self.assertLess(post_memory, 827.0, f"Memory usage too high during agent creation: {post_memory:.1f}MB")
        print(f"Agent creation: CPU {cpu_change:+.1f}%, Memory {memory_change:+.1f}MB, Time {elapsed:.3f}s")
        
    def test_concurrent_operations(self):
        """Test resource usage during concurrent operations"""
        # Create agents
        agents = [Agent.spawn(name=f"concurrent-agent-{i}") for i in range(3)]
        
        # Define operation to run in parallel
        def run_operations(agent, count):
            for i in range(count):
                try:
                    # Simulate a simple operation
                    agent.execute("test_operation", {"value": i})
                    time.sleep(0.1)  # Small delay to prevent CPU spikes
                except ResourceLimitError:
                    # Expected when resource constraints are enforced
                    time.sleep(0.5)
        
        # Start threads for concurrent operations
        threads = []
        for agent in agents:
            thread = threading.Thread(target=run_operations, args=(agent, 5))
            thread.daemon = True
            threads.append(thread)
        
        # Get initial metrics
        initial_cpu = self.monitor.get_cpu_percent()
        initial_memory = self.monitor.get_memory_mb()
        
        # Start all threads
        start_time = time.time()
        for thread in threads:
            thread.start()
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=30.0)
        
        elapsed = time.time() - start_time
        
        # Get final metrics
        peak_cpu = max(self.monitor._cpu_samples) if self.monitor._cpu_samples else 0
        peak_memory = max(self.monitor._memory_samples) if self.monitor._memory_samples else 0
        
        # Check constraints
        self.assertLess(peak_cpu, 27.0, f"Peak CPU usage too high during concurrent operations: {peak_cpu:.1f}%")
        self.assertLess(peak_memory, 827.0, f"Peak memory usage too high during concurrent operations: {peak_memory:.1f}MB")
        
        print(f"Concurrent operations: Peak CPU {peak_cpu:.1f}%, Peak Memory {peak_memory:.1f}MB, Time {elapsed:.3f}s")
    
    def test_resource_constraints_enforced(self):
        """Test that resource constraints are actually enforced"""
        # Create an agent
        agent = Agent.spawn(name="constraint-test-agent")
        
        # Override CPU budget to a low value to force throttling
        with agent.resource_monitor._lock:
            agent.resource_monitor._cpu_budget = 0.1
        
        # Try to execute an operation - should be throttled or fail
        start_time = time.time()
        
        throttled = False
        try:
            for i in range(5):
                # This should eventually trigger throttling or resource limits
                agent.execute("test_operation", {"cpu_intensive": True})
                time.sleep(0.1)
        except ResourceLimitError:
            throttled = True
        
        elapsed = time.time() - start_time
        
        # Check that throttling occurred
        self.assertTrue(throttled, "Resource constraints were not enforced")
        print(f"Resource constraint enforcement test passed in {elapsed:.3f}s")
    
    def test_memory_leak_detection(self):
        """Test that there are no memory leaks during normal operation"""
        # Create an agent
        agent = Agent.spawn(name="memory-leak-test-agent")
        
        # Get initial memory
        initial_memory = self.monitor.get_memory_mb()
        
        # Run multiple operations in a loop
        iteration_memories = []
        for i in range(10):
            # Execute some operations
            for j in range(5):
                try:
                    agent.execute("test_operation", {"value": j})
                except Exception:
                    pass
            
            # Explicitly trigger garbage collection
            gc.collect()
            time.sleep(0.5)  # Allow for cleanup
            
            # Measure memory
            current_memory = self.monitor.get_memory_mb()
            iteration_memories.append(current_memory)
            
            print(f"Iteration {i+1} memory: {current_memory:.1f}MB")
        
        # Calculate memory growth rate
        if len(iteration_memories) >= 5:
            early_avg = sum(iteration_memories[:3]) / 3
            late_avg = sum(iteration_memories[-3:]) / 3
            growth_per_iteration = (late_avg - early_avg) / (len(iteration_memories) - 3)
            
            # Check for significant memory growth
            max_acceptable_growth = 0.5  # MB per iteration
            self.assertLess(
                growth_per_iteration, 
                max_acceptable_growth, 
                f"Potential memory leak detected: {growth_per_iteration:.2f}MB growth per iteration"
            )
            
            print(f"Memory growth rate: {growth_per_iteration:.2f}MB per iteration (acceptable: <{max_acceptable_growth}MB)")


if __name__ == "__main__":
    unittest.main()
