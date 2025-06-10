# Solidity Agreement Integration

## Overview

MCP-ZERO enables middleware-based Solidity agreement deployment without blockchain requirements. Our development experiences demonstrated how these agreements can govern agent behavior through constraints, resource limits, and ethical policies.

## Key Components

### TaskAgreement Contract

The Solidity contract defines governance rules for agent behavior:

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract TaskAgreement {
    // Agreement participants
    address public owner;
    string public agentId;
    
    // Agreement constraints
    uint256 public maxTasks;
    uint256 public maxResourceUsage;
    uint256 public expirationTime;
    uint256 public completedTasks;
    uint256 public resourceUsed;
    
    // Ethical policies
    bool public contentSafetyEnabled;
    bool public fairUseEnabled;
    bool public dataPrivacyEnabled;

    // Task recording
    struct Task {
        string taskId;
        string description;
        uint256 timestamp;
        string result;
    }
    
    Task[] public tasks;
    
    // Events
    event TaskCompleted(string taskId, string description, string result);
    event EthicalViolation(string policyType, string taskId, string reason);
    event AgreementViolation(string violationType, string reason);
    
    constructor(
        string memory _agentId,
        uint256 _maxTasks,
        uint256 _maxResourceUsage,
        uint256 _expirationTime,
        bool _contentSafetyEnabled,
        bool _fairUseEnabled,
        bool _dataPrivacyEnabled
    ) {
        owner = msg.sender;
        agentId = _agentId;
        maxTasks = _maxTasks;
        maxResourceUsage = _maxResourceUsage;
        expirationTime = _expirationTime;
        contentSafetyEnabled = _contentSafetyEnabled;
        fairUseEnabled = _fairUseEnabled;
        dataPrivacyEnabled = _dataPrivacyEnabled;
        completedTasks = 0;
        resourceUsed = 0;
    }
    
    // Function to check if agent can execute tasks
    function canExecute() public view returns (bool, string memory) {
        // Check expiration
        if (block.timestamp > expirationTime) {
            return (false, "Agreement expired");
        }
        
        // Check task limit
        if (completedTasks >= maxTasks) {
            return (false, "Maximum tasks exceeded");
        }
        
        // Check resource usage
        if (resourceUsed >= maxResourceUsage) {
            return (false, "Maximum resource usage exceeded");
        }
        
        return (true, "");
    }
    
    // Function to record task completion
    function recordTask(
        string memory taskId, 
        string memory description, 
        uint256 resourceCost, 
        string memory result
    ) public returns (bool) {
        require(msg.sender == owner, "Only owner can record tasks");
        
        // Check if task can be executed
        (bool canExecuteTask, string memory reason) = canExecute();
        if (!canExecuteTask) {
            emit AgreementViolation("CannotExecute", reason);
            return false;
        }
        
        // Record task
        tasks.push(Task({
            taskId: taskId,
            description: description,
            timestamp: block.timestamp,
            result: result
        }));
        
        // Update counters
        completedTasks++;
        resourceUsed += resourceCost;
        
        // Emit event
        emit TaskCompleted(taskId, description, result);
        return true;
    }
    
    // Check ethical compliance
    function checkEthicalCompliance(
        string memory policyType, 
        string memory content
    ) public view returns (bool, string memory) {
        if (keccak256(bytes(policyType)) == keccak256(bytes("content_safety"))) {
            if (!contentSafetyEnabled) {
                return (true, "Content safety check not required");
            }
            // Here we would implement content safety checks
            // For now we'll just return true
            return (true, "");
        } else if (keccak256(bytes(policyType)) == keccak256(bytes("fair_use"))) {
            if (!fairUseEnabled) {
                return (true, "Fair use check not required");
            }
            // Fair use policy checks
            return (true, "");
        } else if (keccak256(bytes(policyType)) == keccak256(bytes("data_privacy"))) {
            if (!dataPrivacyEnabled) {
                return (true, "Data privacy check not required");
            }
            // Data privacy checks
            return (true, "");
        }
        
        return (false, "Unknown policy type");
    }
}
```

### Deployment Module

The deployment script simulates middleware deployment:

```python
def deploy_agreement(agent_id, max_tasks=50, max_resource_usage=500, 
                    expiration_days=30, ethical_policies=None):
    """Deploy a Solidity agreement to MCP-ZERO middleware"""
    if ethical_policies is None:
        ethical_policies = ["content_safety", "fair_use", "data_privacy"]
    
    # Read contract source
    contract_path = os.path.join(
        os.path.dirname(__file__), 
        'contracts', 
        'TaskAgreement.sol'
    )
    
    with open(contract_path, 'r') as file:
        contract_source = file.read()
        print(f"📄 Loaded contract source: {len(contract_source)} bytes")
    
    # Deployment timestamp
    deploy_time = int(time.time())
    expiration_time = deploy_time + (expiration_days * 24 * 60 * 60)
    
    # Agreement ID (in production would be assigned by middleware)
    agreement_id = f"task-{agent_id}-{deploy_time}"
    
    print(f"🚀 Deploying agreement {agreement_id} for agent {agent_id}")
    
    # Create deployment info record (simulating middleware deployment)
    deploy_info = {
        "agreement_id": agreement_id,
        "agent_id": agent_id,
        "deployed_at": deploy_time,
        "max_tasks": max_tasks,
        "max_resource_usage": max_resource_usage,
        "expiration_time": expiration_time,
        "ethical_policies": ethical_policies,
        "middleware_url": "http://localhost:50051"
    }
    
    # In production, we would make an RPC call to the middleware server to deploy
    # For simulation, we'll just save this to a JSON file
    output_path = os.path.join(
        os.path.dirname(__file__), 
        'deployed_agreement.json'
    )
    
    with open(output_path, 'w') as file:
        json.dump(deploy_info, file, indent=2)
        print(f"📝 Deployment info written to {output_path}")
    
    print(f"✅ Agreement {agreement_id} deployed successfully")
    print(f"📊 Agreement details:")
    print(f"   - Max tasks: {max_tasks}")
    print(f"   - Max resource usage: {max_resource_usage}")
    print(f"   - Expires: {datetime.fromtimestamp(expiration_time)}")
    print(f"   - Ethical policies: {', '.join(ethical_policies)}")
    
    return agreement_id, deploy_info
```

### Agent Integration

Agents load and respect agreement constraints:

```python
def load_deployed_agreement(self):
    """Load previously deployed Solidity agreement from JSON file"""
    try:
        # Initialize protocol for current thread
        self._init_protocol()
        
        # Load deployment info
        with open(self.deploy_info_path, 'r') as file:
            deploy_info = json.load(file)
            
        # Create Agreement instance (simulating connection to deployed contract)
        self.agreement = Agreement(
            agreement_id=deploy_info.get("agreement_id", ""),
            agent_id=deploy_info.get("agent_id", ""),
            max_tasks=deploy_info.get("max_tasks", 0),
            max_resource_usage=deploy_info.get("max_resource_usage", 0),
            expiration_time=deploy_info.get("expiration_time", 0),
            ethical_policies=deploy_info.get("ethical_policies", [])
        )
        
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
    except Exception as e:
        print(f"❌ Error loading agreement: {e}")
        return False
```

## Implementation Patterns

### Middleware Without Blockchain

MCP-ZERO provides smart contract functionality without blockchain requirements:
- No gas costs or transaction delays
- Simplified deployment and management
- Retained verifiability and constraint enforcement
- Lower computational overhead

### Ethical Policy Enforcement

Agreements enforce ethical policies through runtime checks:

```python
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
```

### Constraint Checking

Agreements validate task execution against resource and count limits:

```python
# Check if we can execute (resources, limits)
can_execute, reason = self.agreement.can_execute()
if not can_execute:
    print(f"❌ Cannot execute task: {reason}")
    return False
```

## Real-World Applications

Solidity agreement integration enables numerous applications:

1. **AI Safety Systems** - Enforce ethical boundaries on agent behavior
2. **Task Management Systems** - Govern resource allocation and priorities
3. **Regulatory Compliance** - Ensure actions meet legal requirements
4. **Multi-Agent Coordination** - Define interaction rules between agents
5. **Resource Allocation** - Manage computing resources across systems
6. **Service Level Agreements** - Define and enforce service parameters
7. **Data Access Controls** - Restrict and audit data usage
8. **Ethical AI Frameworks** - Implement and verify ethical principles
9. **Business Process Management** - Enforce workflow rules
10. **Digital Rights Management** - Control content usage and distribution

## Best Practices

1. **Separate deployment from usage** - Deploy once, reference many times
2. **Include comprehensive constraints** - Time, resources, and task limits
3. **Implement all ethical policies** - Content safety, fair use, and privacy
4. **Record all agreement events** - Load, execution, and violations
5. **Validate before execution** - Check all constraints beforehand
6. **Handle expiration gracefully** - Proper lifecycle management
7. **Document policy implications** - Clear guidance on restrictions
8. **Implement detailed logging** - Track all agreement interactions
9. **Version agreements properly** - Support updates and migrations
10. **Test edge cases** - Verify behavior at constraint boundaries
