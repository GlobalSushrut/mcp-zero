#!/usr/bin/env python3
"""
Smart Task Agent - Guided by Solidity Agreement
==============================================

This agent performs various tasks while being governed by a Solidity agreement
that enforces resource limits, ethical constraints, and access controls.

The Solidity agreement is deployed to the MCP-ZERO middleware server,
not a blockchain, but still provides the same governance capabilities.
"""

import os
import sys
import json
import time
import asyncio
import random
import argparse
import threading
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import MCP-ZERO components
from memory_trace.db.memory_tree import DBMemoryTree
from pare_protocol.chain_protocol import PAREChainProtocol

class AgreementMiddleware:
    """Handles deployment and interaction with Solidity agreements via middleware"""
    
    def __init__(self, middleware_url="http://localhost:50051"):
        self.middleware_url = middleware_url
        self.agreement_id = None
        self.contracts_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "contracts")
        
    def deploy_agreement(self, agent_id, max_tasks=100, max_resource_usage=1000, 
                         duration_days=30, ethical_policies=None):
        """Deploy a Solidity agreement to middleware server"""
        if ethical_policies is None:
            ethical_policies = ["content_safety", "fair_use", "data_privacy"]
            
        print(f"🔄 Deploying agreement for agent {agent_id}")
        
        # In a real implementation, this would use RPC to deploy the contract
        # For this demo, we'll simulate the deployment process
        
        # Read the contract source
        contract_path = os.path.join(self.contracts_dir, "TaskAgreement.sol")
        try:
            with open(contract_path, "r") as f:
                contract_source = f.read()
                print(f"📄 Loaded contract from {contract_path}")
        except FileNotFoundError:
            print(f"❌ Contract file not found at {contract_path}")
            return None
            
        # Generate a simulated agreement ID
        self.agreement_id = f"task-{agent_id}-{int(time.time())}"
        
        # Store agreement details (in a real system this would be in the middleware)
        self.agreement_details = {
            "id": self.agreement_id,
            "agent_id": agent_id,
            "max_tasks": max_tasks,
            "completed_tasks": 0,
            "max_resource_usage": max_resource_usage,
            "used_resources": 0,
            "expiration_time": int((datetime.now() + timedelta(days=duration_days)).timestamp()),
            "ethical_policies": ethical_policies,
            "task_history": []
        }
        
        print(f"✅ Agreement deployed with ID: {self.agreement_id}")
        return self.agreement_id
        
    def check_can_execute_task(self, resources_needed):
        """Check if a task can be executed based on agreement constraints"""
        if not self.agreement_id:
            print("❌ No agreement deployed")
            return False
            
        # Check if agreement is active
        now = int(time.time())
        if now >= self.agreement_details["expiration_time"]:
            print("❌ Agreement has expired")
            return False
            
        # Check task limit
        if self.agreement_details["completed_tasks"] >= self.agreement_details["max_tasks"]:
            print("❌ Task limit reached")
            return False
            
        # Check resource limit
        if self.agreement_details["used_resources"] + resources_needed > self.agreement_details["max_resource_usage"]:
            print("❌ Resource limit would be exceeded")
            return False
            
        return True
        
    def check_ethical_compliance(self, policy, content):
        """Check if an operation complies with ethical policies"""
        if not self.agreement_id:
            print("❌ No agreement deployed")
            return False, "No agreement deployed"
            
        # Check if policy is enabled
        if policy not in self.agreement_details["ethical_policies"]:
            return False, f"Policy {policy} not enabled"
            
        # In a real implementation, this would contain complex ethical evaluation
        # For this demo, we'll simulate basic checks
        
        if policy == "content_safety":
            # Check for unsafe content (simplified)
            unsafe_terms = ["hack", "exploit", "bypass", "illegal"]
            for term in unsafe_terms:
                if term in content.lower():
                    return False, f"Content contains unsafe term: {term}"
                    
        elif policy == "fair_use":
            # Check fair resource usage (simplified)
            if len(content) > 1000:  # arbitrary limit for demo
                return False, "Content length exceeds fair use policy"
                
        elif policy == "data_privacy":
            # Check for potential PII (simplified)
            pii_patterns = ["password:", "ssn:", "credit card:"]
            for pattern in pii_patterns:
                if pattern in content.lower():
                    return False, f"Content may contain PII: {pattern}"
        
        return True, "Content is compliant"
        
    def record_task(self, task_id, task_type, resources_used, result):
        """Record a completed task in the agreement"""
        if not self.agreement_id:
            print("❌ No agreement deployed")
            return False
            
        # Check if we can execute this task
        if not self.check_can_execute_task(resources_used):
            return False
            
        # Record the task
        task_record = {
            "task_id": task_id,
            "timestamp": int(time.time()),
            "task_type": task_type,
            "resources_used": resources_used,
            "completed": True,
            "result": result
        }
        
        # Update agreement state
        self.agreement_details["task_history"].append(task_record)
        self.agreement_details["completed_tasks"] += 1
        self.agreement_details["used_resources"] += resources_used
        
        print(f"✅ Task {task_id} recorded in agreement {self.agreement_id}")
        return True
        
    def get_agreement_stats(self):
        """Get current agreement statistics"""
        if not self.agreement_id:
            return None
            
        now = int(time.time())
        remaining_tasks = self.agreement_details["max_tasks"] - self.agreement_details["completed_tasks"]
        remaining_resources = self.agreement_details["max_resource_usage"] - self.agreement_details["used_resources"]
        
        if now >= self.agreement_details["expiration_time"]:
            remaining_time = 0
        else:
            remaining_time = self.agreement_details["expiration_time"] - now
            
        return {
            "tasks_remaining": remaining_tasks,
            "resources_remaining": remaining_resources,
            "time_remaining_seconds": remaining_time
        }

class Task:
    """Represents a task that the agent can perform"""
    
    def __init__(self, task_id, task_type, description, resource_estimate):
        self.task_id = task_id
        self.task_type = task_type  # analysis, processing, generation, etc.
        self.description = description
        self.resource_estimate = resource_estimate
        self.completed = False
        self.result = None
        
    def execute(self):
        """Execute the task (simulated)"""
        print(f"🔄 Executing task {self.task_id}: {self.description}")
        
        # Simulate task execution
        time.sleep(1)  # Simulated processing time
        
        # Simulate different task types
        if self.task_type == "analysis":
            self.result = f"Analysis complete: Found {random.randint(3, 15)} patterns in data"
        elif self.task_type == "processing":
            self.result = f"Processing complete: Transformed {random.randint(10, 100)} data points"
        elif self.task_type == "generation":
            self.result = f"Generation complete: Created {random.randint(1, 5)} new outputs"
        else:
            self.result = "Task completed successfully"
            
        self.completed = True
        print(f"✅ Task {self.task_id} completed: {self.result}")
        return self.result

class SmartTaskAgent:
    """Agent that executes tasks governed by a Solidity agreement"""
    
    def __init__(self, agent_id, middleware_url="http://localhost:50051"):
        self.agent_id = agent_id
        
        # Create db directory for this demo
        self.db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_db")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, f"{agent_id}.db")
        
        # Initialize thread-local storage for protocol instances
        self._thread_local = threading.local()
        
        # Initialize protocol in main thread
        self._init_protocol()
        
        # Initialize agreement middleware
        self.agreement = AgreementMiddleware(middleware_url)
        
        # Task queue and history
        self.tasks = []
        self.completed_tasks = []
        
        print(f"🤖 Smart Task Agent '{agent_id}' initialized")
        
    def _init_protocol(self):
        """Initialize protocol instance for current thread"""
        if not hasattr(self._thread_local, "protocol"):
            try:
                # Initialize the protocol - DB will start in offline mode by default
                # This aligns with the memory_tree fix to prevent connection errors
                self._thread_local.protocol = PAREChainProtocol(
                    db_path=self.db_path,
                    rpc_url="http://localhost:8081"  # Default RPC URL, but DB will be in offline mode
                )
                print(f"📊 Protocol instance initialized for thread {threading.current_thread().name}")
            except Exception as e:
                print(f"Error initializing protocol: {e}")
                # Ensure we have a protocol even if initialization fails
                self._thread_local.protocol = None
            
    def load_deployed_agreement(self):
        """Load previously deployed Solidity agreement from JSON file"""
        # Path to the deployment info file
        deploy_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 
            "deployed_agreement.json"
        )
        
        try:
            with open(deploy_file, "r") as f:
                deploy_info = json.load(f)
                
            # Check if this is for our agent
            if deploy_info.get("agent_id") != self.agent_id:
                print(f"⚠️ Warning: Loaded agreement is for agent {deploy_info.get('agent_id')}, not {self.agent_id}")
                print("⚠️ Will use the agreement anyway for demo purposes")
                
            # Set the agreement ID and details
            self.agreement.agreement_id = deploy_info.get("agreement_id")
            self.agreement.agreement_details = {
                "id": deploy_info.get("agreement_id"),
                "agent_id": deploy_info.get("agent_id"),
                "max_tasks": deploy_info.get("max_tasks", 50),
                "completed_tasks": 0,
                "max_resource_usage": deploy_info.get("max_resource_usage", 500),
                "used_resources": 0,
                "expiration_time": deploy_info.get("expiration_time"),
                "ethical_policies": deploy_info.get("ethical_policies", []),
                "task_history": []
            }
            
            print(f"🔐 Agent is now governed by agreement: {self.agreement.agreement_id}")
            # Record this event in memory trace using memory_tree.add_memory
            if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
                try:
                    self._thread_local.protocol.memory_tree.add_memory(
                        agent_id=self.agent_id,
                        content=f"Loaded agreement {self.agreement.agreement_id} with {deploy_info.get('max_tasks')} tasks, {deploy_info.get('max_resource_usage')} resource units",
                        node_type="agreement_event",
                        metadata={"event_type": "agreement_loaded"}
                    )
                except Exception as e:
                    print(f"Note: Memory recording skipped - {e}")
            else:
                print("Note: Memory recording skipped - protocol not initialized")
            return True
        except FileNotFoundError:
            print("❌ No deployed agreement found. Please run deploy_agreement.py first.")
            return False
        except json.JSONDecodeError:
            print("❌ Invalid agreement deployment file format")
            return False
            
    def add_task(self, description, task_type="processing", resource_estimate=10):
        """Add a new task to the queue"""
        task_id = f"task-{len(self.tasks)+1}-{int(time.time())}"
        task = Task(task_id, task_type, description, resource_estimate)
        self.tasks.append(task)
        print(f"➕ Added task {task_id} to queue: {description}")
        return task_id
        
    def execute_next_task(self):
        """Execute the next task in the queue, if allowed by the agreement"""
        if not self.tasks:
            print("❌ No tasks in queue")
            return False
            
        # Get next task
        task = self.tasks.pop(0)
        
        # Check ethical compliance
        compliance, reason = self.agreement.check_ethical_compliance(
            "content_safety", task.description
        )
        
        if not compliance:
            print(f"❌ Task '{task.task_id}' violates ethical policy: {reason}")
            # Record violation in memory trace
            if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
                try:
                    self._thread_local.protocol.memory_tree.add_memory(
                        agent_id=self.agent_id,
                        content=f"Task {task.task_id} failed ethical check: {reason}",
                        node_type="ethical_event",
                        metadata={"event_type": "ethical_violation", "task_id": task.task_id}
                    )
                except Exception as e:
                    print(f"Note: Memory recording skipped - {e}")
            return False
            
        # Check if we can execute (resources, limits)
        if not self.agreement.check_can_execute_task(task.resource_estimate):
            print(f"❌ Agreement constraints prevent execution of task {task.task_id}")
            return False
            
        # Execute the task
        result = task.execute()
        
        # Record the task in the agreement
        success = self.agreement.record_task(
            task_id=task.task_id,
            task_type=task.task_type,
            resources_used=task.resource_estimate,
            result=result
        )
        
        if success:
            # Add to completed tasks
            self.completed_tasks.append(task)
            
            # Record in memory trace using memory_tree.add_memory
            if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
                try:
                    self._thread_local.protocol.memory_tree.add_memory(
                        agent_id=self.agent_id,
                        content=f"Completed task {task.task_id}: {task.description}",
                        node_type="task_event",
                        metadata={"event_type": "task_completion", "task_id": task.task_id}
                    )
                except Exception as e:
                    print(f"Note: Memory recording skipped - {e}")
            else:
                print("Note: Memory recording skipped - protocol not initialized")
            return True
        else:
            print(f"❌ Failed to record task {task.task_id} in agreement")
            return False
            
    def show_agreement_status(self):
        """Show current agreement statistics"""
        stats = self.agreement.get_agreement_stats()
        if not stats:
            print("❌ No active agreement")
            return
            
        print("\n📊 Agreement Status")
        print("==================")
        print(f"Tasks remaining: {stats['tasks_remaining']}")
        print(f"Resources remaining: {stats['resources_remaining']}")
        
        # Convert seconds to days/hours/minutes
        remaining_seconds = stats['time_remaining_seconds']
        days = remaining_seconds // 86400
        hours = (remaining_seconds % 86400) // 3600
        minutes = (remaining_seconds % 3600) // 60
        
        print(f"Time remaining: {days} days, {hours} hours, {minutes} minutes")
        print(f"Completed tasks: {len(self.completed_tasks)}")
        
    def display_help(self):
        """Display available commands"""
        print("\n🔍 Available Commands")
        print("==================")
        print("  task <description> - Add a new task")
        print("  execute - Execute the next task in queue")
        print("  status - Show agreement status")
        print("  history - Show task history")
        print("  help - Show this help message")
        print("  exit - Exit the demo")

def main():
    """Main entry point for the Smart Task Agent demo"""
    parser = argparse.ArgumentParser(description="Smart Task Agent Demo")
    parser.add_argument("--agent-id", default="smart-agent-1749539350", 
                      help="ID for the agent (use the ID from deployed_agreement.json)")
    parser.add_argument("--middleware", default="http://localhost:50051",
                      help="URL for middleware server")
    
    args = parser.parse_args()
    
    print("🤖 Smart Task Agent Demo")
    print("======================")
    print("Agent governed by Solidity agreement on MCP-ZERO middleware")
    
    # Create the agent
    agent = SmartTaskAgent(args.agent_id, args.middleware)
    
    # Load previously deployed agreement
    if not agent.load_deployed_agreement():
        print("\n⚠️ Failed to load agreement. Please run deploy_agreement.py first.")
        return
    
    # Add some initial tasks
    agent.add_task("Analyze customer sentiment data", "analysis", 15)
    agent.add_task("Process monthly transaction records", "processing", 25)
    agent.add_task("Generate quarterly report", "generation", 30)
    
    # Command loop
    agent.display_help()
    try:
        while True:
            cmd = input("\n> ").strip()
            
            if cmd.startswith("task "):
                description = cmd[5:].strip()
                if description:
                    agent.add_task(description)
                else:
                    print("❌ Please provide a task description")
                    
            elif cmd == "execute":
                agent.execute_next_task()
                
            elif cmd == "status":
                agent.show_agreement_status()
                
            elif cmd == "history":
                if agent.completed_tasks:
                    print("\n📜 Task History")
                    print("=============")
                    for i, task in enumerate(agent.completed_tasks, 1):
                        print(f"{i}. {task.task_id}: {task.description}")
                        print(f"   Result: {task.result}")
                else:
                    print("No completed tasks yet")
                    
            elif cmd == "help":
                agent.display_help()
                
            elif cmd == "exit":
                break
                
            else:
                print("❌ Unknown command. Type 'help' for available commands")
                
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        
    print("Smart Task Agent demo finished")

if __name__ == "__main__":
    main()
