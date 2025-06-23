# MCP-ZERO Agent Development Guide

## Core Principles

MCP-ZERO provides a foundation for building sustainable, ethical AI agents with the following core principles:

1. **Immutable Core Design**: Hardware constraints (<27% CPU, <827MB RAM) ensuring 100+ year sustainability
2. **Plugin-Based Extensibility**: All new capabilities added via plugins without modifying core
3. **Cryptographic Integrity**: All agent actions and memory are cryptographically verifiable
4. **Ethical Governance**: Built-in ethical constraints and auditing capabilities
5. **Resource Efficiency**: Optimized for minimal resource consumption

## Agent Lifecycle

```
┌─────────────────┐    ┌───────────────┐    ┌───────────────┐    ┌────────────┐
│ agent.spawn()   │ → │ agent.attach() │ → │ agent.execute()│ → │agent.snapshot()│
└─────────────────┘    └───────────────┘    └───────────────┘    └────────────┘
        ↑                                                              │
        └──────────────────────────────────────────────────────────────┘
                              agent.recover()
```

### Creating an Agent

```python
from mcp_zero import Agent

# Create a new agent
agent = Agent.spawn(
    agent_name="assistant_agent",
    capabilities=["reasoning", "memory"],
    constraints={"ethical": True, "resource": "standard"}
)
```

### Attaching Plugins

```python
# Attach plugins to extend capabilities
agent.attach_plugin("creative_workflow")
agent.attach_plugin("pare_training", config={
    "learning_rate": 0.1, 
    "geometry": "hyperbolic"
})
```

### Executing Tasks

```python
# Execute a task
result = agent.execute(
    task_description="Create a summary of the provided text",
    inputs={"text": long_document},
    trace=True  # Enable ZK-tracing
)
```

### Snapshots and Recovery

```python
# Create a snapshot
snapshot_id = agent.snapshot()

# Recover agent state from snapshot
recovered_agent = Agent.recover(snapshot_id)
```

## Resource Monitoring

All agents automatically monitor resource usage:

```python
# Get current resource usage
stats = agent.get_resource_usage()
print(f"CPU: {stats['cpu_percent']}%, RAM: {stats['memory_mb']}MB")

# Set resource warnings
agent.set_resource_warning(cpu_threshold=20, memory_threshold=700)
```

## Memory Integration

Agents use the built-in memory tree for persistent, verifiable memory:

```python
# Add memory
memory_id = agent.add_memory(
    content="Important information to remember",
    memory_type="learning",
    metadata={"source": "user_interaction"}
)

# Retrieve memory
memory = agent.get_memory(memory_id)

# Verify memory chain integrity
is_valid = agent.verify_memory_chain(memory_id)
```

## PARE Protocol Integration

Advanced agent training with the PARE protocol:

```python
from mcp_zero import Agent
from pare_protocol import PAREChainProtocol

# Initialize protocol
protocol = PAREChainProtocol()

# Create training block for agent
agent = Agent.spawn("learner_agent")
block_id = protocol.create_training_block(
    agent_id=agent.id,
    training_type="perception"
)

# Record agent learnings
protocol.add_training_data(block_id, 
                          agent.get_latest_learnings(), 
                          "observation")
```

## Testing Agents

MCP-ZERO provides comprehensive testing tools:

```python
from mcp_zero.testing import AgentTester

# Create test harness
tester = AgentTester(agent)

# Test agent capabilities
results = tester.run_test_suite("standard_reasoning")
print(f"Agent passed {results['passed_count']} out of {results['total']} tests")

# Resource constraint testing
resource_compliance = tester.verify_resource_constraints()
```

## Best Practices

1. **Always monitor resource usage** to ensure compliance with MCP-ZERO constraints
2. **Use plugins for extending functionality** rather than modifying core code
3. **Enable tracing** for all production agent operations to ensure auditability
4. **Implement regular snapshots** for fault tolerance and recovery
5. **Use the PARE protocol** for advanced agent training scenarios
6. **Test against resource constraints** before deployment

## Common Pitfalls

1. Exceeding resource constraints, particularly during complex operations
2. Neglecting to verify memory chain integrity regularly
3. Implementing capabilities in core code instead of plugins
4. Disabling trace functionality in production
5. Not properly handling plugin lifecycle (attach/detach)

By following these guidelines, developers can build robust, efficient, and ethical AI agents on the MCP-ZERO platform that maintain the core principles of sustainability and verifiability.
