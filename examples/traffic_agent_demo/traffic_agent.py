#!/usr/bin/env python3
"""
Smart Traffic Agent (Edge Street Cop) using MCP-ZERO Acceleration Server
"""
import os
import sys
import json
import time
import random
import requests
import threading
from dataclasses import dataclass
from typing import Dict, List, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP-ZERO imports
from pare_protocol.chain_protocol import PAREChainProtocol as PAREProtocol

# Simulated data structures
@dataclass
class Vehicle:
    id: str
    vehicle_type: str  # car, truck, motorcycle, bus
    speed: float       # mph
    location: tuple    # x, y coordinates
    direction: str     # N, S, E, W
    anomaly: bool = False

@dataclass
class TrafficEvent:
    event_id: str
    timestamp: float
    event_type: str
    confidence: float
    vehicle_ids: List[str]
    details: Dict[str, Any]

class TrafficAgent:
    """Edge traffic monitoring agent with acceleration server offloading"""
    
    def __init__(self, intersection_id, use_acceleration=True):
        self.intersection_id = intersection_id
        self.use_acceleration = use_acceleration
        
        # Initialize MCP-ZERO protocol paths
        # Create a db path for this demo
        self.db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(self.db_dir, exist_ok=True)
        self.db_path = os.path.join(self.db_dir, f"traffic_{intersection_id}.db")
        self.rpc_url = "http://localhost:50051"
        
        # Create thread-local storage for protocol instances
        self._thread_local = threading.local()
        
        # Initialize protocol in main thread
        self._init_protocol()
        
        self.agent_id = f"traffic-{intersection_id}"
        
        # Acceleration server settings
        self.acceleration_url = "http://localhost:50055"
        
        # Simulation settings
        self.speed_limit = 35.0  # mph
        self.vehicles = {}
        self.events = []
        self.running = False
        
        # Traffic patterns
        self.traffic_patterns = {
            "morning_rush": {"density": 0.8, "avg_speed": 25.0},
            "midday": {"density": 0.4, "avg_speed": 30.0},
            "evening_rush": {"density": 0.9, "avg_speed": 22.0},
            "night": {"density": 0.2, "avg_speed": 38.0}
        }
        
        self.current_pattern = "midday"
        print(f"Traffic agent initialized at intersection {intersection_id}")
        
    def start_monitoring(self):
        """Start traffic monitoring simulation"""
        self.running = True
        
        while self.running:
            # Generate simulated traffic data
            self._update_simulation()
            
            # Process traffic data
            events = self._process_traffic_data()
            
            # Display status
            if events:
                for event in events:
                    print(f"⚠️ {event.event_type}: {event.details.get('description', '')}")
                    print(f"   Confidence: {event.confidence:.2f}, Vehicles: {len(event.vehicle_ids)}")
            else:
                vehicles = len(self.vehicles)
                pattern = self.current_pattern.replace("_", " ").title()
                print(f"🔍 Monitoring {vehicles} vehicles - {pattern} traffic pattern")
                
            # Sleep to simulate real-time monitoring
            time.sleep(2)
    
    def _update_simulation(self):
        """Update simulated traffic data"""
        pattern = self.traffic_patterns[self.current_pattern]
        
        # Add new vehicles
        if random.random() < pattern["density"] * 0.2:
            vehicle_id = f"v{int(time.time() * 1000) % 10000}"
            vehicle_type = random.choice(["car", "car", "car", "truck", "motorcycle", "bus"])
            direction = random.choice(["N", "S", "E", "W"])
            
            # Randomize speed based on pattern with some violations
            base_speed = pattern["avg_speed"]
            speed = max(5, min(65, random.gauss(base_speed, 8)))
            
            self.vehicles[vehicle_id] = Vehicle(
                id=vehicle_id,
                vehicle_type=vehicle_type,
                speed=speed,
                location=(random.randint(0, 100), random.randint(0, 100)),
                direction=direction,
                anomaly=random.random() < 0.05  # 5% chance of anomaly
            )
        
        # Remove some vehicles (out of view)
        for vehicle_id in list(self.vehicles.keys()):
            if random.random() < 0.15:  # 15% chance to leave view
                del self.vehicles[vehicle_id]
            else:
                # Update existing vehicles
                v = self.vehicles[vehicle_id]
                
                # Randomize speed changes
                v.speed += random.uniform(-3, 3)
                v.speed = max(0, min(70, v.speed))
                
                # Update anomaly flag (simulate erratic behavior)
                if random.random() < 0.01:  # 1% chance to become anomalous
                    v.anomaly = True
                
                # Update location based on direction
                x, y = v.location
                if v.direction == "N":
                    y = (y - v.speed/10) % 100
                elif v.direction == "S":
                    y = (y + v.speed/10) % 100
                elif v.direction == "E":
                    x = (x + v.speed/10) % 100
                elif v.direction == "W":
                    x = (x - v.speed/10) % 100
                v.location = (x, y)
    
    def _init_protocol(self):
        """Initialize protocol instance for current thread"""
        if not hasattr(self._thread_local, 'protocol'):
            self._thread_local.protocol = PAREProtocol(
                db_path=self.db_path,
                rpc_url=self.rpc_url
            )
    
    def _process_traffic_data(self):
        """Process traffic data to detect events"""
        # Ensure protocol is initialized for this thread
        self._init_protocol()
        
        trace_id = self._thread_local.protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="traffic_analysis",
            metadata={"timestamp": time.time(), "intersection_id": self.intersection_id}
        )
        
        events = []
        
        # Use acceleration server for video processing if enabled
        if self.use_acceleration:
            events.extend(self._offload_video_processing())
        
        # Local processing for speed violations
        speed_violations = [v for v in self.vehicles.values() if v.speed > self.speed_limit * 1.15]
        if speed_violations:
            # Create speeding event
            event = TrafficEvent(
                event_id=f"speed-{int(time.time())}",
                timestamp=time.time(),
                event_type="SPEED_VIOLATION",
                confidence=0.92,
                vehicle_ids=[v.id for v in speed_violations],
                details={
                    "description": f"Speeding vehicles detected ({len(speed_violations)})",
                    "max_speed": max(v.speed for v in speed_violations),
                    "speed_limit": self.speed_limit
                }
            )
            events.append(event)
            
            # Record in memory trace
            self._thread_local.protocol.add_training_data(
                block_id=trace_id,
                data_content=json.dumps({
                    "event_type": "SPEED_VIOLATION",
                    "vehicles": len(speed_violations),
                    "timestamp": time.time(),
                    "max_speed": max(v.speed for v in speed_violations)
                }),
                data_type="traffic_event",
                metadata={"agent_id": self.agent_id}
            )
        
        # Local processing for anomalous vehicles
        anomalous = [v for v in self.vehicles.values() if v.anomaly]
        if anomalous:
            # Create anomaly event
            event = TrafficEvent(
                event_id=f"anom-{int(time.time())}",
                timestamp=time.time(),
                event_type="ANOMALOUS_BEHAVIOR",
                confidence=0.85,
                vehicle_ids=[v.id for v in anomalous],
                details={
                    "description": f"Anomalous vehicle behavior detected ({len(anomalous)})",
                    "types": [v.vehicle_type for v in anomalous]
                }
            )
            events.append(event)
            
            # Record in memory trace
            self._thread_local.protocol.add_training_data(
                block_id=trace_id,
                data_content=json.dumps({
                    "event_type": "ANOMALOUS_BEHAVIOR",
                    "vehicles": len(anomalous),
                    "timestamp": time.time()
                }),
                data_type="traffic_event",
                metadata={"agent_id": self.agent_id}
            )
        
        # Update event history
        self.events.extend(events)
        if len(self.events) > 100:
            self.events = self.events[-100:]
            
        # No need to close the training block - it's automatically managed
        
        return events
    
    def _offload_video_processing(self):
        """Offload video processing to acceleration server"""
        events = []
        
        # Only attempt offloading if we have vehicles to process
        if not hasattr(self, '_acceleration_offline') and len(self.vehicles) > 0:
            # Prepare data for offloading
            traffic_data = {
                "agent_id": self.agent_id,
                "timestamp": time.time(),
                "vehicles": []
            }
            
            # Convert vehicle data to JSON-serializable format
            for vehicle_id, vehicle in self.vehicles.items():
                traffic_data["vehicles"].append({
                    "id": vehicle.id,
                    "type": vehicle.vehicle_type,
                    "speed": vehicle.speed,
                    "location": list(vehicle.location),
                    "direction": vehicle.direction
                })
            
            # Try to send to acceleration server
            try:
                print(f"📤 Connecting to acceleration server at {self.acceleration_url}/acceleration/offload")
                print(f"📤 Sending data for {len(traffic_data['vehicles'])} vehicles")
                
                # Prepare request parameters and data
                url = f"{self.acceleration_url}/acceleration/offload"
                params = {
                    "agent_id": self.agent_id,
                    "task_type": "video_processing"
                }
                headers = {"Content-Type": "application/json"}
                
                # Debug prints
                print(f"💿 Full URL: {url}?agent_id={self.agent_id}&task_type=video_processing")
                print(f"💾 Request data: {traffic_data}")
                
                # Make the request with extended timeout
                response = requests.post(
                    url=url,
                    params=params,
                    headers=headers,
                    json=traffic_data,
                    timeout=5  # Increased timeout for more reliable connections
                )
                
                if response.status_code == 200:
                    # Process successful response
                    result = response.json()
                    print(f"✅ Acceleration server processed {result.get('vehicle_count', 0)} vehicles")
                    
                    # Convert detections to events
                    for detection in result.get("detections", []):
                        # In real implementation, we would create proper events
                        # Here we'll simulate an immediate response with events
                        events.extend(self._generate_simulated_events())
                    return events
                else:
                    print(f"❌ Acceleration server returned error: {response.status_code}")
                    self._acceleration_offline = True
                    print("   Switching to local processing only")
            except requests.exceptions.ConnectionError as e:
                print(f"⚠️ CONNECTION ERROR: Failed to connect to acceleration server: {e}")
                print(f"⚠️ Server URL: {self.acceleration_url}")
                print("⚠️ Switching to offline mode for future processing")
                self._acceleration_offline = True
            except requests.exceptions.Timeout as e:
                print(f"⚠️ TIMEOUT ERROR: Acceleration server connection timed out: {e}")
                print("⚠️ Switching to offline mode for future processing")
                self._acceleration_offline = True
            except Exception as e:
                print(f"⚠️ UNEXPECTED ERROR: Problem with acceleration server: {e}")
                print(f"⚠️ Error type: {type(e).__name__}")
                print("⚠️ Switching to offline mode for future processing")
                self._acceleration_offline = True
        
        # If we get here, we're using local processing
        # Generate simulated events locally
        if hasattr(self, '_acceleration_offline') and len(self.vehicles) > 0:
            events.extend(self._generate_simulated_events())
        
        return events

    def _generate_simulated_events(self):
        """Generate simulated events for demo purposes"""
        events = []
        
        # Randomly generate accident events
        if self.vehicles and random.random() < 0.1:  # 10% chance of accident event
            vehicle_ids = random.sample(list(self.vehicles.keys()), 
                                      min(2, len(self.vehicles)))
            
            event = TrafficEvent(
                event_id=f"acc-{int(time.time())}",
                timestamp=time.time(),
                event_type="ACCIDENT_DETECTED",
                confidence=0.96,
                vehicle_ids=vehicle_ids,
                details={
                    "description": "Vehicle collision detected",
                    "severity": random.choice(["minor", "moderate", "major"]),
                    "location": "intersection center"
                }
            )
            events.append(event)
        
        # Randomly generate emergency vehicle events
        if random.random() < 0.05:  # 5% chance
            event = TrafficEvent(
                event_id=f"emrg-{int(time.time())}",
                timestamp=time.time(),
                event_type="EMERGENCY_VEHICLE",
                confidence=0.98,
                vehicle_ids=[],
                details={
                    "description": "Emergency vehicle approaching",
                    "vehicle_type": random.choice(["ambulance", "police", "fire"]),
                    "direction": random.choice(["N", "S", "E", "W"])
                }
            )
            events.append(event)
        
        return events
    
    def change_traffic_pattern(self, pattern):
        """Change the current traffic pattern for simulation"""
        if pattern in self.traffic_patterns:
            self.current_pattern = pattern
            print(f"Traffic pattern changed to: {pattern}")
        else:
            print(f"Unknown traffic pattern: {pattern}")
    
    def stop(self):
        """Stop the traffic monitoring"""
        self.running = False

def main():
    print("🚦 Smart Traffic Agent (Edge Street Cop)")
    print("========================================")
    print("Uses MCP-ZERO with Acceleration Server for video processing")
    
    # Create traffic agent
    agent = TrafficAgent("main-and-5th")
    
    try:
        # Start in a separate thread
        from threading import Thread
        monitoring_thread = Thread(target=agent.start_monitoring)
        monitoring_thread.daemon = True
        monitoring_thread.start()
        
        # Command interface
        print("\nCommands:")
        print("  'pattern [morning_rush|midday|evening_rush|night]' - Change traffic pattern")
        print("  'exit' - Exit the demo")
        
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "exit":
                break
                
            elif cmd.startswith("pattern "):
                pattern = cmd.split(" ")[1]
                agent.change_traffic_pattern(pattern)
                
            else:
                print("Unknown command")
                
    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        agent.stop()
        print("Traffic agent stopped")

if __name__ == "__main__":
    main()
