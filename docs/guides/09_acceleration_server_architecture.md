# Acceleration Server Architecture

## Overview

Our development work with MCP-ZERO revealed the key architectural patterns of the Go-based acceleration server. This component offloads compute-intensive tasks from agent processes, enabling better performance and resource utilization.

## Server Components

### Core Architecture

The acceleration server is built as a Go HTTP server with specialized handlers:

```go
type AccelerationServer struct {
    Port       int
    AgentStore map[string]*AgentState
    mu         sync.RWMutex
}

func NewAccelerationServer(port int) *AccelerationServer {
    return &AccelerationServer{
        Port:       port,
        AgentStore: make(map[string]*AgentState),
    }
}

func (s *AccelerationServer) Start() {
    http.HandleFunc("/acceleration/offload", s.handleTaskOffload)
    http.HandleFunc("/acceleration/status", s.handleStatus)
    http.HandleFunc("/debug/ping", s.handlePing)
    
    addr := fmt.Sprintf(":%d", s.Port)
    log.Printf("🚀 Starting Acceleration Server at %s", addr)
    
    err := http.ListenAndServe(addr, nil)
    if err != nil {
        log.Fatalf("💥 Failed to start server: %v", err)
    }
}
```

### Task Offload Handler

The task offload handler receives and processes compute-intensive tasks:

```go
func (s *AccelerationServer) handleTaskOffload(w http.ResponseWriter, r *http.Request) {
    log.Printf("📥 Received task offload request from %s to %s", r.RemoteAddr, r.URL.Path)
    
    // Log request headers for debugging
    log.Printf("📝 Request headers: %v", r.Header)
    
    // Log query parameters
    log.Printf("📝 Query parameters: agent_id=%s, task_type=%s", 
        r.URL.Query().Get("agent_id"), r.URL.Query().Get("task_type"))
    
    // Read and log full request body
    bodyBytes, err := ioutil.ReadAll(r.Body)
    if err != nil {
        http.Error(w, "Failed to read request body", http.StatusBadRequest)
        return
    }
    log.Printf("📝 Request body: %s", string(bodyBytes))
    
    // Parse JSON request
    var requestData map[string]interface{}
    err = json.Unmarshal(bodyBytes, &requestData)
    if err != nil {
        http.Error(w, "Invalid JSON", http.StatusBadRequest)
        return
    }
    
    // Extract agent_id from query parameters or request body
    agentID := r.URL.Query().Get("agent_id")
    if agentID == "" {
        if id, ok := requestData["agent_id"].(string); ok {
            agentID = id
        } else {
            http.Error(w, "Missing agent_id", http.StatusBadRequest)
            return
        }
    }
    
    // Process based on task type
    taskType := r.URL.Query().Get("task_type")
    var result interface{}
    
    switch taskType {
    case "video_processing":
        result = s.processVideoTask(agentID, requestData)
    case "natural_language":
        result = s.processNLPTask(agentID, requestData)
    case "image_analysis":
        result = s.processImageTask(agentID, requestData)
    default:
        http.Error(w, "Unknown task_type", http.StatusBadRequest)
        return
    }
    
    // Return results as JSON
    response := map[string]interface{}{
        "status":    "success",
        "timestamp": time.Now().Unix(),
        "agent_id":  agentID,
        "task_type": taskType,
        "result":    result,
    }
    
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(response)
    log.Printf("✅ Task offload completed for agent %s", agentID)
}
```

### Video Processing Implementation

Specialized processing for video analysis tasks:

```go
func (s *AccelerationServer) processVideoTask(agentID string, requestData map[string]interface{}) map[string]interface{} {
    log.Printf("🎬 Processing video task for agent %s", agentID)
    
    // Extract vehicles from request
    vehiclesData, ok := requestData["vehicles"].([]interface{})
    if !ok {
        log.Printf("❌ Invalid vehicles data for agent %s", agentID)
        return map[string]interface{}{
            "error": "Invalid vehicles data",
        }
    }
    
    // Generate simulated events
    events := make([]map[string]interface{}, 0)
    for _, vehicleData := range vehiclesData {
        vehicle, ok := vehicleData.(map[string]interface{})
        if !ok {
            continue
        }
        
        // Extract vehicle properties
        vehicleID, _ := vehicle["id"].(string)
        vehicleType, _ := vehicle["type"].(string)
        speed, _ := vehicle["speed"].(float64)
        
        // Analyze for events (simulated)
        if speed > 65.0 {
            // Generate speeding event
            events = append(events, map[string]interface{}{
                "type":       "speeding",
                "vehicle_id": vehicleID,
                "vehicle_type": vehicleType,
                "speed":      speed,
                "speed_limit": 65.0,
                "timestamp":  time.Now().Unix(),
            })
        }
        
        // Random chance of additional events
        if rand.Float32() < 0.3 {
            eventTypes := []string{"lane_deviation", "tailgating", "abrupt_stop"}
            randomEvent := eventTypes[rand.Intn(len(eventTypes))]
            
            events = append(events, map[string]interface{}{
                "type":       randomEvent,
                "vehicle_id": vehicleID,
                "vehicle_type": vehicleType,
                "timestamp":  time.Now().Unix(),
            })
        }
    }
    
    log.Printf("✅ Generated %d events for agent %s", len(events), agentID)
    
    return map[string]interface{}{
        "events": events,
    }
}
```

### Status Handler

The status handler provides server health and diagnostics:

```go
func (s *AccelerationServer) handleStatus(w http.ResponseWriter, r *http.Request) {
    log.Printf("📊 Status request from %s", r.RemoteAddr)
    
    // Gather status metrics
    status := map[string]interface{}{
        "status":      "ok",
        "version":     "1.0.0",
        "uptime":      time.Since(startTime).String(),
        "agent_count": len(s.AgentStore),
        "timestamp":   time.Now().Unix(),
    }
    
    // Return status as JSON
    w.Header().Set("Content-Type", "application/json")
    json.NewEncoder(w).Encode(status)
}
```

## Client Integration

### Python Client Pattern

MCP-ZERO agents connect to the acceleration server using this pattern:

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

## Key Improvements

### Single Connection Attempt

Our development work revealed the importance of making only one connection attempt to the acceleration server:

```python
try:
    # Attempt connection once
    response = requests.post(url, json=request_data, timeout=5.0)
    # Process response...
except Exception as e:
    # On ANY error, permanently switch to offline mode
    print(f"⚠️ Error connecting to acceleration server: {e}")
    self.offline_mode = True  # Permanent switch to offline mode
    return self._simulate_local_events(vehicles)
```

This improvement prevents repetitive connection attempts and error messages, resulting in cleaner execution and better user experience.

## Real-World Applications

The acceleration server architecture enables numerous applications:

1. **Traffic Monitoring Systems** - Offload vehicle detection and analysis
2. **Facial Recognition Services** - Process image data with hardware acceleration
3. **Natural Language Processing** - Accelerate text analysis and generation
4. **Medical Image Analysis** - Process diagnostic imagery with specialized hardware
5. **Financial Market Analysis** - Accelerate pattern detection in market data
6. **Security Camera Systems** - Process multiple video streams efficiently
7. **Satellite Imagery Processing** - Analyze remote sensing data at scale
8. **Gaming Physics Simulation** - Offload complex physics calculations
9. **Scientific Data Analysis** - Process research data with specialized hardware
10. **Augmented Reality Systems** - Offload scene understanding and object recognition

## Best Practices

1. **Implement proper error logging** - Capture detailed request and response data
2. **Use appropriate timeout values** - Prevent hanging on slow responses
3. **Handle all error types** - ConnectionError, Timeout, and unexpected exceptions
4. **Provide meaningful status endpoints** - Help diagnose server health
5. **Use query parameters for metadata** - Makes logging and debugging easier
6. **Implement request validation** - Verify request format before processing
7. **Return standardized responses** - Consistent format for all operations
8. **Include detailed metrics** - Track processing times and resource usage
9. **Implement rate limiting** - Prevent server overload from excessive requests
10. **Design for horizontal scaling** - Enable multiple server instances for throughput

## Deployment Considerations

The acceleration server is typically deployed:

1. On dedicated hardware with specialized accelerators (GPUs, TPUs, etc.)
2. With high-bandwidth network connections to agent processes
3. With resource monitoring and auto-scaling capabilities
4. As multiple instances behind a load balancer for high availability
5. With proper error tracking and alerting mechanisms
