#!/usr/bin/env python3
"""
MCP-ZERO v7 Master Test Automation Script
----------------------------------------

This script executes the comprehensive production-grade test suite for the entire 
MCP-ZERO infrastructure. It orchestrates testing across all components and measures
resource utilization to ensure compliance with hardware constraints (<27% CPU, <827MB RAM).

Usage:
    python3 run_all_tests.py [--component <component>] [--phase <phase>] [--verbose]
    
    --component: Specify a single component to test (kernel, sdk, rpc, trace, storage, plugin, solidity)
    --phase: Specify a test phase (unit, integration, system, performance, security, durability)
    --verbose: Enable detailed logging
"""

import os
import sys
import time
import argparse
import subprocess
import json
import psutil
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("mcp_zero_tests.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

# Test configuration
TEST_COMPONENTS = {
    "kernel": {
        "path": "kernel/tests",
        "command": "cargo test --release",
        "description": "Rust/C++ Kernel Tests",
        "new_script": "tests/test_kernel.py"
    },
    "sdk": {
        "path": "sdk/python/tests",
        "command": "python3 -m pytest",
        "description": "Python SDK Tests",
        "new_script": "tests/test_sdk.py"
    },
    "rpc": {
        "path": "src/rpc-layer",
        "command": "go test -v ./...",
        "description": "Go RPC Layer Tests",
        "new_script": "tests/test_rpc_layer.py"
    },
    "trace": {
        "path": "trace/tests",
        "command": "./run_trace_tests.sh",
        "description": "Poseidon+ZKSync Trace Engine Tests",
        "new_script": "tests/test_trace_engine.py"
    },
    "storage": {
        "path": "storage/tests",
        "command": "python3 -m pytest",
        "description": "MongoDB + HeapBT Storage Tests",
        "new_script": "tests/test_storage.py"
    },
    "plugin": {
        "path": "plugin/tests",
        "command": "./test_wasm_integration.sh",
        "description": "WASM Plugin ABI Tests",
        "new_script": "tests/test_plugin_abi.py"
    },
    "solidity": {
        "path": "tests",
        "command": "python3 test_solidity_verification.py",
        "description": "Solidity Agreement Middleware Tests",
        "new_script": "tests/test_solidity_verification.py"
    }
}

TEST_PHASES = {
    "unit": "Unit tests for individual components",
    "integration": "Integration tests between components",
    "system": "End-to-end system tests",
    "performance": "Performance and resource utilization tests",
    "security": "Security and cryptographic integrity tests",
    "durability": "Data persistence and recovery tests"
}

class ResourceMonitor:
    """Monitor and record system resource utilization during tests"""
    
    def __init__(self, interval=1.0):
        self.interval = interval
        self.running = False
        self.measurements = []
        self.start_time = None
        self.end_time = None
        
    def start(self):
        """Start monitoring resources"""
        self.measurements = []
        self.running = True
        self.start_time = datetime.now()
        
        # Start monitoring in a separate thread
        def monitor():
            while self.running:
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                memory_used_mb = memory.used / (1024 * 1024)  # Convert to MB
                
                self.measurements.append({
                    "timestamp": time.time(),
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_used_mb
                })
                
                time.sleep(self.interval)
        
        self.monitor_thread = ThreadPoolExecutor(max_workers=1)
        self.monitor_thread.submit(monitor)
        
    def stop(self):
        """Stop monitoring resources"""
        self.running = False
        self.end_time = datetime.now()
        
    def get_report(self):
        """Generate resource utilization report"""
        if not self.measurements:
            return {"error": "No measurements collected"}
            
        cpu_values = [m["cpu_percent"] for m in self.measurements]
        memory_values = [m["memory_mb"] for m in self.measurements]
        
        duration = (self.end_time - self.start_time).total_seconds()
        
        report = {
            "duration_seconds": duration,
            "cpu": {
                "avg": sum(cpu_values) / len(cpu_values) if cpu_values else 0,
                "max": max(cpu_values) if cpu_values else 0,
                "within_limit": all(v <= 27.0 for v in cpu_values)
            },
            "memory_mb": {
                "avg": sum(memory_values) / len(memory_values) if memory_values else 0,
                "max": max(memory_values) if memory_values else 0, 
                "within_limit": all(v <= 827.0 for v in memory_values)
            }
        }
        
        return report


class TestRunner:
    """Execute tests and collect results"""
    
    def __init__(self, base_dir, verbose=False):
        self.base_dir = base_dir
        self.verbose = verbose
        self.resource_monitor = ResourceMonitor()
        self.results = {}
        
    def run_component_test(self, component, phase=None, legacy=False):
        """Run tests for a specific component"""
        if component not in TEST_COMPONENTS:
            logging.error(f"Unknown component: {component}")
            return False
            
        comp_config = TEST_COMPONENTS[component]
        
        # Check if we should use the new unified test scripts
        if not legacy and "new_script" in comp_config and os.path.exists(os.path.join(self.base_dir, comp_config["new_script"])):
            script_path = os.path.join(self.base_dir, comp_config["new_script"])
            logging.info(f"Running new {comp_config['description']} script: {script_path}")
            
            # Make script executable if needed
            if not os.access(script_path, os.X_OK):
                os.chmod(script_path, 0o755)
                
            command = f"python3 {script_path}"
            if phase:
                command += f" --phase {phase}"
                
            comp_dir = os.path.dirname(script_path)
        else:
            # Use legacy test command
            comp_dir = os.path.join(self.base_dir, comp_config["path"])
            
            if not os.path.exists(comp_dir):
                logging.warning(f"Component directory not found: {comp_dir}")
                return False
                
            command = comp_config["command"]
            if phase:
                # Append phase-specific arguments if applicable
                if component == "rpc" and phase == "performance":
                    command += " -tags=performance"
                elif component == "sdk" and phase == "integration":
                    command += " -m integration"
        
        logging.info(f"Running {comp_config['description']}...")
        
        # Start resource monitoring
        self.resource_monitor.start()
        
        # Run the test command
        start_time = time.time()
        process = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=comp_dir
        )
        
        stdout, stderr = process.communicate()
        stdout = stdout.decode('utf-8', errors='replace')
        stderr = stderr.decode('utf-8', errors='replace')
        
        end_time = time.time()
        exit_code = process.returncode
        
        # Stop resource monitoring
        self.resource_monitor.stop()
        resource_report = self.resource_monitor.get_report()
        
        # Store results
        self.results[component] = {
            "success": exit_code == 0,
            "duration": end_time - start_time,
            "exit_code": exit_code,
            "resources": resource_report
        }
        
        if self.verbose:
            logging.info(stdout)
            if stderr:
                logging.error(stderr)
                
        result_str = "PASSED" if exit_code == 0 else "FAILED"
        logging.info(f"{comp_config['description']}: {result_str} (Duration: {end_time - start_time:.2f}s)")
        
        # Resource compliance check
        cpu_compliant = resource_report["cpu"]["within_limit"]
        mem_compliant = resource_report["memory_mb"]["within_limit"]
        
        if not cpu_compliant:
            logging.warning(f"CPU usage exceeded 27% limit! Max: {resource_report['cpu']['max']:.1f}%")
        
        if not mem_compliant:
            logging.warning(f"Memory usage exceeded 827MB limit! Max: {resource_report['memory_mb']['max']:.1f}MB")
            
        return exit_code == 0
    
    def run_all_tests(self, phase=None):
        """Run tests for all components"""
        overall_success = True
        
        for component in TEST_COMPONENTS:
            # Use new test scripts by default
            success = self.run_component_test(component, phase, legacy=False)
            overall_success = overall_success and success
            
        return overall_success
    
    def generate_report(self):
        """Generate a comprehensive test report"""
        success_count = sum(1 for r in self.results.values() if r["success"])
        total_count = len(self.results)
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "overall_success": success_count == total_count,
            "success_rate": f"{success_count}/{total_count}",
            "component_results": self.results,
        }
        
        # Check hardware constraints
        cpu_maxes = [r["resources"]["cpu"]["max"] for r in self.results.values()]
        mem_maxes = [r["resources"]["memory_mb"]["max"] for r in self.results.values()]
        
        report["hardware_constraints"] = {
            "cpu_within_limit": all(cpu <= 27.0 for cpu in cpu_maxes),
            "memory_within_limit": all(mem <= 827.0 for mem in mem_maxes),
            "max_cpu_percent": max(cpu_maxes) if cpu_maxes else 0,
            "max_memory_mb": max(mem_maxes) if mem_maxes else 0
        }
        
        return report


def main():
    parser = argparse.ArgumentParser(description="MCP-ZERO v7 Test Automation")
    parser.add_argument("--component", help="Component to test", choices=TEST_COMPONENTS.keys())
    parser.add_argument("--phase", help="Test phase", choices=TEST_PHASES.keys())
    parser.add_argument("--verbose", help="Enable verbose logging", action="store_true")
    parser.add_argument("--legacy", help="Use legacy test scripts", action="store_true")
    args = parser.parse_args()
    
    # Get the base directory
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Set up the test runner
    runner = TestRunner(base_dir, args.verbose)
    
    # Print test plan info
    logging.info("MCP-ZERO v7 Production-Grade Test Automation")
    logging.info("===========================================")
    logging.info(f"Base directory: {base_dir}")
    logging.info(f"Testing hardware constraints: <27% CPU, <827MB RAM")
    
    try:
        if args.component:
            # Run tests for a specific component
            success = runner.run_component_test(args.component, args.phase, args.legacy)
        else:
            # Run all tests
            success = runner.run_all_tests(args.phase)
            
        # Generate and save the report
        report = runner.generate_report()
        report_file = os.path.join(base_dir, "tests", "test_report.json")
        
        with open(report_file, "w") as f:
            json.dump(report, f, indent=2)
            
        logging.info(f"Test report saved to {report_file}")
        
        # Output summary
        logging.info("\nTest Summary:")
        logging.info(f"- Overall success: {'Yes' if report['overall_success'] else 'No'}")
        logging.info(f"- Components tested: {report['success_rate']}")
        logging.info(f"- CPU constraint met: {'Yes' if report['hardware_constraints']['cpu_within_limit'] else 'No'}")
        logging.info(f"- Memory constraint met: {'Yes' if report['hardware_constraints']['memory_within_limit'] else 'No'}")
        
        # Set exit code based on success
        sys.exit(0 if success else 1)
        
    except Exception as e:
        logging.error(f"Error during test execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
