# Agreement Templates

## Overview

MCP-ZERO uses agreements to define resource usage terms between consumers and providers.

## Template Structure

```json
{
  "template_id": "standard_compute",
  "version": "1.0",
  "parameters": {
    "duration_days": {"type": "integer", "default": 30},
    "requests_per_day": {"type": "integer", "default": 1000},
    "compute_units": {"type": "integer", "default": 5000}
  },
  "pricing": {
    "base_price": {"type": "decimal", "default": 10.0},
    "overage_rate": {"type": "decimal", "default": 0.001}
  },
  "conditions": [
    {"type": "usage_limit", "metric": "requests", "limit": "${requests_per_day}"},
    {"type": "time_limit", "days": "${duration_days}"}
  ]
}
```

## Standard Templates

- **basic_agent**: Simple agent resources
- **compute_intensive**: High-CPU operations
- **storage_focused**: Large data storage
- **network_optimized**: High bandwidth operations

## Usage Example

```python
from mcp_zero.sdk import Agreement

# Create agreement from template
agreement = Agreement.create_from_template(
    template_id="standard_compute",
    consumer_id="user123",
    provider_id="provider456",
    parameters={
        "duration_days": 60,
        "requests_per_day": 5000,
        "compute_units": 10000
    }
)

# Sign agreement
agreement.sign(consumer_key="consumer_signing_key")

# Validate for operation
valid = agreement.validate_for_operation("process_data")
```

## Validation Process

1. Check agreement signatures
2. Verify not expired
3. Confirm sufficient resources
4. Validate for specific operation
5. Record usage against limits

## Billing Integration

```python
# Record usage
agreement.record_usage("requests", 1)
agreement.record_usage("compute_units", 25)

# Check usage status
status = agreement.get_usage_status()
if status.is_over_limit():
    # Handle overage billing
    agreement.bill_overage()
```

## Custom Templates

Create custom templates with specific constraints:

```python
from mcp_zero.sdk import AgreementTemplate

template = AgreementTemplate(
    template_id="ai_training",
    parameters={
        "gpu_hours": {"type": "integer", "default": 100},
        "model_size_gb": {"type": "integer", "default": 10}
    },
    pricing={
        "base_price": {"type": "decimal", "default": 500.0},
        "overage_rate": {"type": "decimal", "default": 5.0}
    }
)

template.save()
```
