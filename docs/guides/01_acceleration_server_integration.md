# Acceleration Server Integration

## Overview

The acceleration server is a key component of MCP-ZERO that offloads compute-intensive tasks from agents. During our development, we learned that proper integration requires careful error handling and connection management.

## Key Features

1. **Task Offloading Protocol**
   - HTTP-based API on port 50055
   - JSON request/response format for structured data
   - Query parameters for agent identification and task type
   - Standardized endpoint structure: `/acceleration/offload`

2. **Robust Error Handling**
   - Connection timeouts require appropriate handling
   - Network failures should trigger graceful fallback
   - Response validation prevents processing malformed data
   - Detailed logging for diagnostic purposes

3. **Fallback Mechanisms**
   - Agents should detect server unavailability
   - Switch to local processing mode when server is unreachable
   - Cache processing capabilities locally when possible
   - Maintain consistent output format regardless of processing mode

4. **Performance Optimization**
   - Batching of similar tasks reduces connection overhead
   - Compression for large data transfers
   - Keep-alive connections for multiple sequential requests
   - Stream processing for real-time data

## Implementation Example

Our Traffic Agent implementation demonstrated these principles:

```python
def _offload_video_processing(self, vehicles):
    """Attempt to offload video processing to acceleration server"""
    if self.offline_mode:
        # Already in offline mode, use local processing
        return self._simulate_local_events(vehicles)
        
    # Prepare request data - convert any tuples to lists for JSON serialization
    request_data = {
        "agent_id": self.agent_id,
        "timestamp": time.time(),
        "vehicles": [{
            "id": v.id,
            "type": v.type,
            "speed": v.speed,
            "location": list(v.location),  # Convert tuple to list for JSON
            "direction": v.direction
        } for v in vehicles]
    }
    
    try:
        # Construct URL with query parameters
        url = f"{self.acceleration_url}?agent_id={self.agent_id}&task_type=video_processing"
        print(f"📤 Connecting to acceleration server at {self.acceleration_url}")
        print(f"📤 Sending data for {len(vehicles)} vehicles")
        print(f"💿 Full URL: {url}")
        print(f"💾 Request data: {request_data}")
        
        # Send HTTP request with timeout
        response = requests.post(
            url, 
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=5.0  # 5 second timeout
        )
        
        # Check if request was successful
        if response.status_code == 200:
            # Process successful response
            print(f"✅ Acceleration server processed {len(vehicles)} vehicles")
            return response.json().get("events", [])
        else:
            print(f"⚠️ Acceleration server returned status code {response.status_code}")
            self.offline_mode = True
            return self._simulate_local_events(vehicles)
            
    except requests.exceptions.ConnectionError:
        print("⚠️ Failed to connect to acceleration server - switching to offline mode")
        self.offline_mode = True
        return self._simulate_local_events(vehicles)
        
    except requests.exceptions.Timeout:
        print("⚠️ Acceleration server request timed out - switching to offline mode")
        self.offline_mode = True
        return self._simulate_local_events(vehicles)
        
    except Exception as e:
        print(f"⚠️ Unexpected error when connecting to acceleration server: {e}")
        self.offline_mode = True
        return self._simulate_local_events(vehicles)
```

## Real-World Applications

This acceleration server integration pattern enables a wide range of applications:

1. **Video Surveillance Systems** - Offload video analysis to dedicated hardware
2. **Autonomous Vehicles** - Process sensor data with hardware acceleration
3. **Real-time Image Recognition** - Accelerate computer vision tasks
4. **Natural Language Processing** - Offload complex NLP tasks to specialized hardware
5. **Scientific Data Analysis** - Process large datasets efficiently
6. **Neural Network Inference** - Accelerate ML model execution
7. **Audio Processing** - Real-time speech recognition and processing
8. **Cryptographic Operations** - Secure, accelerated encryption/decryption
9. **Volumetric Rendering** - Accelerated 3D visualization
10. **Physics Simulations** - Complex environment simulations

## Best Practices

1. **Always validate server responses** - Never assume the response format
2. **Implement automatic retry logic** - For transient failures
3. **Include detailed request logging** - Capture full URLs and payload data
4. **Use appropriate timeouts** - Prevent application hangs
5. **Design for graceful degradation** - Ensure agents function with reduced capabilities
6. **Add debugging endpoints** - Include `/debug/ping` for connectivity testing
7. **Monitor server health** - Detect and respond to server failures
8. **Log client-side metrics** - Track success rates and response times
9. **Use compressed payloads** - For large data transfers
10. **Implement request throttling** - Prevent server overload
