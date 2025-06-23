// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/**
 * @title TaskAgreement
 * @dev Contract that governs agent tasks and resource allocation
 */
contract TaskAgreement {
    // Agreement participants
    address public owner;
    string public agentId;
    
    // Task constraints
    uint256 public maxTasks;
    uint256 public completedTasks;
    uint256 public maxResourceUsage;  // CPU/memory units
    uint256 public usedResources;
    uint256 public expirationTime;
    
    // Ethical policies
    string[] public ethicalPolicies;
    mapping(string => bool) private policyEnabled;
    
    // Task outcomes
    struct TaskResult {
        uint256 timestamp;
        string taskType;
        uint256 resourcesUsed;
        bool completed;
        string result;
    }
    
    // Task history
    TaskResult[] public taskHistory;
    
    // Events
    event TaskCompleted(string taskId, uint256 timestamp, uint256 resourcesUsed);
    event AgreementViolation(string reason, uint256 timestamp);
    event EthicalCheck(string policy, bool passed, uint256 timestamp);
    
    constructor(
        string memory _agentId,
        uint256 _maxTasks,
        uint256 _maxResourceUsage,
        uint256 _duration,
        string[] memory _ethicalPolicies
    ) {
        owner = msg.sender;
        agentId = _agentId;
        maxTasks = _maxTasks;
        maxResourceUsage = _maxResourceUsage;
        expirationTime = block.timestamp + _duration;
        
        // Set ethical policies
        for (uint i = 0; i < _ethicalPolicies.length; i++) {
            ethicalPolicies.push(_ethicalPolicies[i]);
            policyEnabled[_ethicalPolicies[i]] = true;
        }
    }
    
    // Check if the agreement is active
    function isActive() public view returns (bool) {
        return block.timestamp < expirationTime;
    }
    
    // Check if a task can be executed
    function canExecuteTask(uint256 resourcesNeeded) public view returns (bool) {
        return isActive() && 
               completedTasks < maxTasks && 
               usedResources + resourcesNeeded <= maxResourceUsage;
    }
    
    // Record a completed task
    function recordTask(
        string memory taskId,
        string memory taskType,
        uint256 resourcesUsed,
        string memory result
    ) public returns (bool) {
        require(isActive(), "Agreement has expired");
        require(completedTasks < maxTasks, "Task limit reached");
        require(usedResources + resourcesUsed <= maxResourceUsage, "Resource limit exceeded");
        
        // Record the task
        taskHistory.push(TaskResult({
            timestamp: block.timestamp,
            taskType: taskType,
            resourcesUsed: resourcesUsed,
            completed: true,
            result: result
        }));
        
        // Update counters
        completedTasks += 1;
        usedResources += resourcesUsed;
        
        // Emit event
        emit TaskCompleted(taskId, block.timestamp, resourcesUsed);
        
        return true;
    }
    
    // Check ethical compliance
    function checkEthicalCompliance(
        string memory policy,
        string memory content
    ) public returns (bool) {
        // In a real implementation, this would contain complex logic
        // Here we just check if the policy exists and simulate a check
        
        bool policyExists = policyEnabled[policy];
        bool passed = policyExists && bytes(content).length > 0;
        
        emit EthicalCheck(policy, passed, block.timestamp);
        
        return passed;
    }
    
    // Get agreement stats
    function getStats() public view returns (
        uint256 remaining,
        uint256 resourcesRemaining,
        uint256 timeRemaining
    ) {
        remaining = maxTasks - completedTasks;
        resourcesRemaining = maxResourceUsage - usedResources;
        
        if (block.timestamp >= expirationTime) {
            timeRemaining = 0;
        } else {
            timeRemaining = expirationTime - block.timestamp;
        }
        
        return (remaining, resourcesRemaining, timeRemaining);
    }
}
