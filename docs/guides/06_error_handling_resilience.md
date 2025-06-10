# Error Handling and Resilience

## Overview

Our development work with MCP-ZERO revealed critical patterns for error handling and system resilience. These insights help build robust agents that maintain functionality even when underlying services are unavailable.

## Key Improvements

### Offline Mode by Default

One of the most important improvements we made to the MCP-ZERO demos was modifying the `DBMemoryTree` to start in offline mode by default:

```python
class DBMemoryTree:
    def __init__(self, db_path, rpc_url=None):
        self.db_path = db_path
        self.rpc_url = rpc_url
        
        # Start in offline mode by default - prevents repeated connection errors
        self.offline_mode = True
        
        # Initialize database
        self._init_db()
        
        logging.info("Starting in offline mode - memory traces will be local only")
```

This change prevents repeated connection errors to the MCP-ZERO RPC server, resulting in cleaner execution and better user experience.

### One-Time Connection Attempts

Another critical improvement was modifying the Traffic Agent's video processing offload function to only attempt connecting to the acceleration server once:

```python
def _offload_video_processing(self, vehicles):
    """Attempt to offload video processing to acceleration server"""
    if self.offline_mode:
        # Already in offline mode, use local processing
        return self._simulate_local_events(vehicles)
    
    # ... connection logic ...
    
    try:
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
            return response.json().get("events", [])
        else:
            # Permanently switch to offline mode after first failure
            print(f"⚠️ Acceleration server returned status code {response.status_code}")
            self.offline_mode = True
            return self._simulate_local_events(vehicles)
            
    except requests.exceptions.ConnectionError:
        # Permanently switch to offline mode after first failure
        print("⚠️ Failed to connect to acceleration server - switching to offline mode")
        self.offline_mode = True
        return self._simulate_local_events(vehicles)
```

This permanent switch to local processing after a single failure prevents repetitive connection attempts and error messages.

## Comprehensive Error Handling Patterns

### Protocol Initialization

Robust protocol initialization with error handling:

```python
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
```

### Memory Operations

Memory operations with null checks and exception handling:

```python
def record_memory(self, content, metadata=None):
    """Record memory with comprehensive error handling"""
    if hasattr(self._thread_local, "protocol") and self._thread_local.protocol is not None:
        try:
            self._thread_local.protocol.memory_tree.add_memory(
                agent_id=self.agent_id,
                content=content,
                node_type="agent_event",
                metadata=metadata or {}
            )
            return True
        except Exception as e:
            print(f"Note: Memory recording skipped - {e}")
            return False
    else:
        print("Note: Memory recording skipped - protocol not initialized")
        return False
```

### Service Connections

Service connections with timeouts and comprehensive error handling:

```python
def connect_service(self, service_url, timeout=5.0):
    """Connect to service with robust error handling"""
    try:
        response = requests.get(
            f"{service_url}/status", 
            timeout=timeout
        )
        
        if response.status_code == 200:
            return True, None
        else:
            error_msg = f"Service returned status code {response.status_code}"
            return False, error_msg
            
    except requests.exceptions.ConnectionError as e:
        return False, f"Connection error: {str(e)}"
        
    except requests.exceptions.Timeout:
        return False, f"Connection timed out after {timeout}s"
        
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"
```

## Fallback Strategies

### Local Processing Fallback

The Traffic Agent implements proper fallback to local processing:

```python
def process_video_frame(self, frame_data):
    """Process video frame with fallback strategy"""
    if not self.offline_mode:
        try:
            # Try acceleration server first
            return self._offload_video_processing(frame_data)
        except Exception:
            # Any error switches to offline mode permanently
            self.offline_mode = True
            
    # Use local processing as fallback
    return self._process_locally(frame_data)
```

### Cached Results

Implementing result caching for resilience:

```python
def get_results(self, query, force_refresh=False):
    """Get results with caching for resilience"""
    cache_key = hash(query)
    
    # Check if we have cached results
    if not force_refresh and cache_key in self.result_cache:
        return self.result_cache[cache_key]
        
    try:
        # Try to get fresh results
        results = self._fetch_results(query)
        # Cache the results
        self.result_cache[cache_key] = results
        return results
    except Exception as e:
        print(f"Error fetching results: {e}")
        # Return cached results if available, otherwise empty results
        return self.result_cache.get(cache_key, [])
```

### Degraded Functionality

Graceful degradation of functionality:

```python
def execute_task(self, task):
    """Execute task with graceful degradation"""
    # Try full featured execution
    if not self.reduced_functionality_mode:
        try:
            return self._execute_full_featured(task)
        except Exception as e:
            print(f"Switching to reduced functionality mode: {e}")
            self.reduced_functionality_mode = True
            
    # Fall back to basic execution
    return self._execute_basic(task)
```

## Real-World Applications

These error handling and resilience patterns enable numerous applications:

1. **Critical Medical Systems** - Maintain essential functionality during outages
2. **Emergency Response Systems** - Ensure operation in degraded network conditions
3. **Rural Information Systems** - Function with intermittent connectivity
4. **Autonomous Vehicle Guidance** - Continue safe operation when cloud services fail
5. **Smart Grid Controllers** - Maintain core power distribution during outages
6. **Banking Transaction Systems** - Process essential transactions during failures
7. **Air Traffic Control Assistants** - Provide fallback guidance during system failures
8. **Disaster Management Tools** - Continue coordinating responses with limited connectivity
9. **Military Field Communication** - Maintain essential messaging in contested environments
10. **Space Exploration Systems** - Function with high-latency or interrupted communications

## Best Practices

1. **Start in offline mode by default** - Prevents connection errors on startup
2. **Switch to offline mode permanently after first failure** - Prevents repeated errors
3. **Always implement local fallbacks** - Ensure continued operation without services
4. **Use appropriate timeouts** - Prevent hanging on slow connections
5. **Check protocol availability before use** - Handle null or unavailable protocols
6. **Wrap all external calls in try-except** - Comprehensive error handling
7. **Log errors but continue operation** - Maintain service with degraded functionality
8. **Cache results when possible** - Provide stale data over no data
9. **Implement graceful degradation** - Prioritize core functionality
10. **Use thread-local storage properly** - Prevent thread safety issues
