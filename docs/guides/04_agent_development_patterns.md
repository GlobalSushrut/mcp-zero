# Agent Development Patterns

## Overview

Through our MCP-ZERO example development, we've discovered robust patterns for building intelligent agents that leverage the middleware's capabilities. These patterns ensure thread safety, error resilience, and proper integration with MCP-ZERO services.

## Core Agent Structure

### Base Agent Pattern

Our development revealed a common structure for MCP-ZERO agents:

```python
class BaseAgent:
    def __init__(self, agent_id, db_path, config=None):
        # Agent identity
        self.agent_id = agent_id
        self.db_path = db_path
        self.config = config or {}
        
        # Thread-local storage for protocol instances
        self._thread_local = threading.local()
        
        # Initialize protocol for main thread
        self._init_protocol()
        
        # Register with memory system
        self._register_agent()
        
    def _init_protocol(self):
        """Initialize protocol instance for current thread"""
        if not hasattr(self._thread_local, "protocol"):
            try:
                # Initialize the protocol - DB will start in offline mode by default
                self._thread_local.protocol = PAREChainProtocol(
                    db_path=self.db_path,
                    rpc_url="http://localhost:8081"
                )
                print(f"📊 Protocol instance initialized for thread {threading.current_thread().name}")
            except Exception as e:
                print(f"Error initializing protocol: {e}")
                # Ensure we have a protocol even if initialization fails
                self._thread_local.protocol = None
                
    def _register_agent(self):
        """Register agent with memory system"""
        if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
            try:
                self._thread_local.protocol.memory_tree.add_memory(
                    agent_id=self.agent_id,
                    content=f"Agent {self.agent_id} initialized",
                    node_type="agent_event",
                    metadata={"event_type": "initialization"}
                )
            except Exception as e:
                print(f"Note: Memory registration skipped - {e}")
```

### Agreement-Based Agents

Agents that operate under Solidity agreements follow this pattern:

```python
class SmartTaskAgent(BaseAgent):
    def __init__(self, agent_id, db_path, deploy_info_path):
        super().__init__(agent_id, db_path)
        
        # Agreement management
        self.deploy_info_path = deploy_info_path
        self.agreement = None
        
        # Task management
        self.tasks = []
        self.completed_tasks = []
        
        # Load agreement if available
        self.load_deployed_agreement()
        
    def load_deployed_agreement(self):
        """Load previously deployed Solidity agreement from JSON file"""
        try:
            # ... Agreement loading logic ...
            return True
        except Exception as e:
            print(f"❌ Error loading agreement: {e}")
            return False
            
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
            # ... Ethical violation handling ...
            return False
            
        # Check if we can execute (resources, limits)
        can_execute, reason = self.agreement.can_execute()
        if not can_execute:
            print(f"❌ Cannot execute task: {reason}")
            return False
            
        # Execute task (simulated)
        print(f"🔄 Executing task {task.task_id}: {task.description}")
        result = f"Analysis complete: Found {random.randint(10, 20)} patterns in data"
        print(f"✅ Task {task.task_id} completed: {result}")
        
        # Record in agreement
        success = self.agreement.record_task(
            task_id=task.task_id,
            description=task.description,
            resource_cost=random.randint(5, 15),
            result=result
        )
        
        if success:
            # ... Success handling ...
            return True
        else:
            print(f"❌ Failed to record task {task.task_id} in agreement")
            return False
```

## Thread Safety Patterns

### Thread-Local Protocol

MCP-ZERO agents must carefully manage SQLite connections:

```python
def _init_protocol(self):
    """Initialize protocol instance for current thread"""
    if not hasattr(self._thread_local, "protocol"):
        try:
            # Initialize the protocol with thread-local storage
            self._thread_local.protocol = PAREChainProtocol(
                db_path=self.db_path,
                rpc_url="http://localhost:8081"
            )
        except Exception as e:
            print(f"Error initializing protocol: {e}")
            self._thread_local.protocol = None
```

### Per-Thread Initialization

For multi-threaded agents, each thread requires protocol initialization:

```python
def process_in_thread(self, data):
    """Process data in a separate thread"""
    # Ensure protocol is initialized for this thread
    self._init_protocol()
    
    # Now process data with protocol instance
    result = self._process_data(data)
    return result
```

## Error Handling Patterns

### Graceful Fallbacks

Our examples demonstrated consistent error handling with fallbacks:

```python
def record_memory(self, content, node_type, metadata):
    """Record a memory with proper error handling"""
    if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
        try:
            self._thread_local.protocol.memory_tree.add_memory(
                agent_id=self.agent_id,
                content=content,
                node_type=node_type,
                metadata=metadata
            )
            return True
        except Exception as e:
            print(f"Note: Memory recording skipped - {e}")
            return False
    else:
        print("Note: Memory recording skipped - protocol not initialized")
        return False
```

### Service Unavailability

Agents handle service outages gracefully:

```python
def connect_to_service(self, service_url, timeout=5):
    """Connect to a service with proper error handling"""
    try:
        response = requests.get(f"{service_url}/ping", timeout=timeout)
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️ Service returned status code {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"⚠️ Could not connect to {service_url}")
        return False
    except requests.exceptions.Timeout:
        print(f"⚠️ Connection to {service_url} timed out")
        return False
    except Exception as e:
        print(f"⚠️ Unexpected error: {e}")
        return False
```

## Command-Line Interface Patterns

MCP-ZERO agents benefit from interactive interfaces:

```python
def run_interactive(self):
    """Run the agent in interactive mode"""
    print("\n🔍 Available Commands")
    print("==================")
    print("  task <description> - Add a new task")
    print("  execute - Execute the next task in queue")
    print("  status - Show agreement status")
    print("  history - Show task history")
    print("  help - Show this help message")
    print("  exit - Exit the demo")
    
    while True:
        try:
            command = input("\n> ").strip()
            
            if command.startswith("task "):
                # Add task logic
                description = command[5:]
                self.add_task(description)
                
            elif command == "execute":
                # Execute task logic
                self.execute_next_task()
                
            elif command == "status":
                # Show status logic
                self.show_status()
                
            elif command == "history":
                # Show history logic
                self.show_task_history()
                
            elif command == "help":
                # Show help logic
                self.show_help()
                
            elif command == "exit":
                print("👋 Goodbye!")
                break
                
            else:
                print("❓ Unknown command. Type 'help' for available commands.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
            
        except Exception as e:
            print(f"❌ Error: {e}")
```

## Real-World Applications

These agent development patterns enable numerous applications:

1. **Virtual Assistants** - Task management with ethical constraints
2. **Content Moderation Systems** - Policy enforcement and review
3. **Medical Treatment Assistants** - Protocol-compliant healthcare support
4. **Financial Compliance Agents** - Regulatory guideline enforcement
5. **Educational Tutors** - Personalized learning with usage limits
6. **Customer Service Agents** - Policy-bounded customer interactions
7. **Research Assistants** - Information gathering with ethical guidelines
8. **Legal Document Processors** - Compliant document handling
9. **Scheduling Assistants** - Resource allocation with constraints
10. **Security Monitoring Agents** - Policy-based threat assessment

## Best Practices

1. **Always use thread-local storage** for thread safety
2. **Check for null protocol instances** before use
3. **Implement graceful error handling** for all service calls
4. **Record significant agent events** in memory system
5. **Use consistent command patterns** for interfaces
6. **Validate all inputs** before processing
7. **Handle interruptions gracefully** in interactive modes
8. **Provide detailed status information** to users
9. **Implement proper resource cleanup** on shutdown
10. **Include comprehensive help information** for users
