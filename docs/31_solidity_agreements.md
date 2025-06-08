# Solidity Agreements

## Overview

MCP-ZERO processes Solidity agreements through middleware without requiring blockchain deployment. Ethical agreements are compulsory.

## Architecture

```
┌─────────────────────┐     ┌───────────────────────┐
│ MCP-ZERO Agreement  │     │ Optional Blockchain   │
│ Manager             │<----│ (Not Required)        │
└─────────┬───────────┘     └───────────────────────┘
          │
┌─────────▼───────────┐     ┌───────────────────────┐
│ Agreement Middleware│     │                       │
│ Server (RPC)        │<----│ Local Solidity VM     │
└─────────┬───────────┘     └───────────────────────┘
          │
┌─────────▼───────────┐
│ Ethical Governance  │
│ (Compulsory)        │
└───────────────────┬─┘
                    │
┌───────────────────▼─┐
│ Agreement Templates  │
└─────────────────────┘
```

## Smart Contract Format

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract MCPZeroAgreement {
    // Standard agreement properties
    string public consumer;
    string public provider;
    uint256 public maxCalls;
    uint256 public usedCalls;
    uint256 public validUntil;
    bool public active;
    
    // Ethical constraints (compulsory)
    bool public hasEthicalChecks;
    string[] public ethicalPolicies;
    
    // Events
    event CallRecorded(uint256 timestamp, string methodName);
    event EthicalViolation(string reason);
}
```

## Creating Agreements

```python
from mcp_zero.agreements import SolidityAgreement

# Create agreement via middleware
agreement = SolidityAgreement.create(
    consumer_id="agent123",
    provider_id="agent456",
    template="standard",
    terms={
        "max_calls": 100,
        "valid_days": 30
    },
    # Ethical constraints (compulsory)
    ethical_policies=["fair_use", "content_safety"]
)

print(f"Agreement created: {agreement.id}")
```

## Middleware Integration

```python
from mcp_zero.middleware import AgreementMiddleware

# Initialize middleware server
middleware = AgreementMiddleware()

# Register agreement verifier
middleware.register_verifier(
    verifier_type="ethical",
    verifier_function=verify_ethical_compliance
)

# Start middleware
middleware.start(port=8765)
```

## Verification Process

```python
# Agreement verification without blockchain
verification = SolidityAgreement.verify(
    agreement_id="agreement123",
    use_middleware=True  # Skip blockchain, use middleware
)

if verification.valid:
    print("Agreement valid")
    print(f"Ethical compliance: {verification.ethical_status}")
else:
    print(f"Invalid: {verification.reason}")
```

## Usage Recording

```python
# Record method call via middleware
SolidityAgreement.record_usage(
    agreement_id="agreement123",
    method_name="process_data",
    use_middleware=True
)
```

## Ethical Enforcement

```python
# Define ethical policy check
def content_safety_check(params):
    """Check content against safety standards"""
    content = params.get("content", "")
    return {
        "compliant": is_safe_content(content),
        "reason": "Content contains prohibited material" if not is_safe_content(content) else ""
    }

# Register compulsory policy
from mcp_zero.ethical import register_policy

register_policy(
    name="content_safety",
    check_function=content_safety_check,
    compulsory=True  # Must pass this check
)
```

## Alternative to Blockchain Payments

```python
# Internal credit system
from mcp_zero.billing import CreditSystem

# Setup credits
credits = CreditSystem()
credits.allocate("consumer123", 1000)

# Pay for agreement usage
credits.transfer(
    from_id="consumer123",
    to_id="provider456",
    amount=10,
    reference="agreement789:call:process_data"
)
```
