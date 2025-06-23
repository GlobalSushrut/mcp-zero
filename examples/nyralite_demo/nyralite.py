#!/usr/bin/env python3
"""
NyraLite: Wearable SOS + Health Monitor
Demonstrates MCP-ZERO mesh networking and consensus features for health monitoring.
"""
import os
import sys
import json
import time
from threading import Thread
import random  # For simulated sensor data
import queue  # For thread-safe communication

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP-ZERO imports
from pare_protocol.intent_weight_bias import IntentWeightBias
from pare_protocol.chain_protocol import PAREChainProtocol as PAREProtocol
from pare_protocol.intent_consensus import IntentAwareConsensus

class SensorData:
    """Simulates wearable sensor data"""
    
    def __init__(self, device_id):
        self.device_id = device_id
        self.baseline_temp = 98.6
        self.baseline_heart_rate = 75
        self.baseline_spo2 = 98
        self.last_fall_time = 0
        self.fall_detected = False
        
    def get_vitals(self):
        """Simulate reading vitals from sensors"""
        # Add minor fluctuations to baseline
        temp = round(self.baseline_temp + random.uniform(-0.5, 0.5), 1)
        heart_rate = int(self.baseline_heart_rate + random.uniform(-5, 5))
        spo2 = int(self.baseline_spo2 + random.uniform(-1, 1))
        
        # Get motion/position data (simulated)
        motion = random.choice(["walking", "standing", "sitting", "lying"])
        
        # Random chance of fall detection for demo
        if random.random() < 0.05:  # 5% chance
            self.fall_detected = True
            self.last_fall_time = time.time()
            motion = "fallen"
        elif time.time() - self.last_fall_time > 10:
            self.fall_detected = False
            
        return {
            "device_id": self.device_id,
            "timestamp": time.time(),
            "temperature": temp,
            "heart_rate": heart_rate,
            "spo2": spo2,
            "motion": motion,
            "fall_detected": self.fall_detected,
            "battery": random.randint(50, 100)
        }
        
    def simulate_emergency(self):
        """Simulate health emergency"""
        self.baseline_heart_rate = 120  # Elevated heart rate
        self.baseline_temp = 101.2      # Fever
        self.baseline_spo2 = 92         # Lower oxygen
        self.fall_detected = True
        self.last_fall_time = time.time()

class NyraLiteAgent:
    """NyraLite health monitoring agent using MCP-ZERO architecture"""
    
    def __init__(self, device_id, mesh_nodes=None):
        self.device_id = device_id
        self.sensor = SensorData(device_id)
        
        # Initialize MCP-ZERO components
        # Create a db path for this demo
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, f"nyralite_{device_id}.db")
        self.protocol = PAREProtocol(db_path=db_path, rpc_url="http://localhost:50051")
        self.agent_id = f"nyralite-{device_id}"
        self.intent_bias = IntentWeightBias(dimensions=(4, 4))  # Smaller grid for embedded
        
        # Create a queue for thread-safe data processing
        self.vitals_queue = queue.Queue()
        
        # Set up mesh network nodes
        self.mesh_nodes = mesh_nodes or []
        self.connected_nodes = []
        
        # Set up health thresholds
        self.thresholds = {
            "temp_high": 100.4,
            "temp_low": 97.0,
            "heart_rate_high": 100,
            "heart_rate_low": 50,
            "spo2_low": 95,
        }
        
        # Setup data storage with limited capacity (for edge device)
        self.vitals_history = []
        self.max_history = 100  # Store last 100 readings
        self.emergency_detected = False
        self.last_alert_time = 0
        
        # Setup consensus mechanism for peer nodes
        self.consensus = IntentAwareConsensus(intent_dimensions=(4, 4), learning_rate=0.05)
        
        # Track agent weights locally since IntentAwareConsensus doesn't have set_agent_weights
        self.agent_weights = {
            f"nyra-{device_id}": 1.0  # Self-weight
        }
        
    def connect_to_mesh(self):
        """Connect to other nodes in the mesh network"""
        print(f"🌐 {self.device_id} connecting to mesh network...")
        
        for node in self.mesh_nodes:
            # In real implementation, this would use actual network connections
            if node != self.device_id:
                print(f"  ├─ Connected to node: {node}")
                self.connected_nodes.append(node)
                # Register node in local weights dictionary
                self.agent_weights[f"nyra-{node}"] = 0.8  # Lower weight for other nodes
                
        print(f"  └─ Connected to {len(self.connected_nodes)} nodes in mesh")
        
    def start_monitoring(self):
        """Start health monitoring in background thread"""
        print(f"📊 {self.device_id} starting health monitoring...")
        self.running = True
        
        # Start sensor monitoring thread that handles everything
        # No need for a separate processing thread since we have a thread-safe approach
        self.monitoring_thread = Thread(target=self._monitoring_loop)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
        
    def stop_monitoring(self):
        """Stop monitoring"""
        print(f"Stopping {self.device_id} monitoring...")
        self.running = False
        
        # Wait for monitoring thread to end
        if hasattr(self, 'monitoring_thread'):
            self.monitoring_thread.join(timeout=1)
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        # Create a protocol instance specifically for this thread
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, f"nyralite_{self.device_id}_monitor.db")
        monitor_protocol = PAREProtocol(db_path=db_path, rpc_url="http://localhost:50051")
        
        while self.running:
            try:
                # Get sensor data
                vitals = self.sensor.get_vitals()
                
                # Store in history with limited capacity
                self.vitals_history.append(vitals)
                if len(self.vitals_history) > self.max_history:
                    self.vitals_history.pop(0)
                    
                # Process data directly in this thread with thread-local protocol
                self._process_vitals_thread_safe(monitor_protocol, vitals)
                
                # Sleep for a bit
                time.sleep(2)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(1)
            
    # The _process_queue method is no longer needed since we're using a thread-local protocol
            
    def _process_vitals_thread_safe(self, protocol, vitals):
        """Thread-safe version that accepts a protocol instance specific to the thread"""
        # Create training block for this vital processing
        trace_id = protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="vitals_processing",
            metadata={"timestamp": vitals['timestamp'], "device_id": self.device_id}
        )
        
        # Process vital signs using the thread-local protocol
        self._process_vitals_internal(protocol, vitals, trace_id)
        
    def _process_vitals(self, vitals):
        """Original method maintained for compatibility - delegates to thread-safe version"""
        # Create training block for this vital processing
        trace_id = self.protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="vitals_processing",
            metadata={"timestamp": vitals['timestamp'], "device_id": self.device_id}
        )
        
        # Process using the main protocol instance
        self._process_vitals_internal(self.protocol, vitals, trace_id)
        
    def _process_vitals_internal(self, protocol, vitals, trace_id):
        """Common implementation used by both thread-safe and original methods"""
        # The actual processing logic goes here
        
        # Check for anomalies
        anomalies = []
        
        if vitals["temperature"] > self.thresholds["temp_high"]:
            anomalies.append(f"High temperature: {vitals['temperature']}°F")
            
        if vitals["temperature"] < self.thresholds["temp_low"]:
            anomalies.append(f"Low temperature: {vitals['temperature']}°F")
            
        if vitals["heart_rate"] > self.thresholds["heart_rate_high"]:
            anomalies.append(f"Elevated heart rate: {vitals['heart_rate']} BPM")
            
        if vitals["heart_rate"] < self.thresholds["heart_rate_low"]:
            anomalies.append(f"Low heart rate: {vitals['heart_rate']} BPM")
            
        if vitals["spo2"] < self.thresholds["spo2_low"]:
            anomalies.append(f"Low blood oxygen: {vitals['spo2']}%")
            
        if vitals["fall_detected"]:
            anomalies.append("Fall detected")
            
        # Record data in memory trace - use the protocol passed in
        protocol.add_training_data(
            block_id=trace_id,
            data_content=json.dumps({
                "vitals": vitals,
                "anomalies": anomalies,
                "timestamp": vitals["timestamp"]
            }),
            data_type="vitals_data",
            metadata={"device_id": self.device_id}
        )
        
        # If anomalies detected, initiate consensus for alert
        if anomalies and not self.emergency_detected:
            self._initiate_alert_consensus(protocol, vitals, anomalies, trace_id)
        
    def _initiate_alert_consensus(self, protocol, vitals, anomalies, trace_id):
        """Use consensus to determine if alert should be triggered"""
        # Build alert proposal
        alert_level = self._calculate_alert_level(vitals, anomalies)
        
        # Prepare vote for consensus
        vote = {
            "agent_id": f"nyra-{self.device_id}",
            "proposal": f"alert-level-{alert_level}",
            "confidence": alert_level / 10.0,  # Convert to 0-1 scale
            "data": {
                "vitals": vitals,
                "anomalies": anomalies
            }
        }
        
        # Submit to consensus
        self.consensus.submit_vote(vote)
        
        # Check if we have enough votes for consensus
        if len(self.consensus.votes) >= max(1, len(self.connected_nodes) // 2):
            result = self.consensus.finalize_consensus()
            
            if result["consensus_reached"]:
                consensus_proposal = result["consensus_proposal"]
                print(f"⚠️ ALERT CONSENSUS: {consensus_proposal}")
                
                # Extract level from proposal name
                try:
                    level = int(consensus_proposal.split("-")[-1])
                    if level > 6:  # High alert threshold
                        self._trigger_emergency_protocol(vitals, anomalies)
                    else:
                        print(f"ℹ️ Monitoring alert level {level} (not emergency)")
                except Exception as e:
                    print(f"Error processing consensus: {e}")
                    pass
                
                # Record consensus in memory trace
                protocol.add_training_data(
                    block_id=trace_id,
                    data_content=json.dumps(result),
                    data_type="consensus_result",
                    metadata={"device_id": self.device_id}
                )
                
                # Reset consensus for next round
                self.consensus.reset()
                
    def _calculate_alert_level(self, vitals, anomalies):
        """Calculate alert level from 1-10 based on vitals"""
        base_level = 0
        
        # Temperature contribution
        temp_diff = abs(vitals["temperature"] - 98.6)
        base_level += min(3, temp_diff)  # Up to 3 points
        
        # Heart rate contribution 
        hr_diff = 0
        if vitals["heart_rate"] > self.thresholds["heart_rate_high"]:
            hr_diff = (vitals["heart_rate"] - self.thresholds["heart_rate_high"]) / 10
        elif vitals["heart_rate"] < self.thresholds["heart_rate_low"]:
            hr_diff = (self.thresholds["heart_rate_low"] - vitals["heart_rate"]) / 5
        base_level += min(3, hr_diff)  # Up to 3 points
        
        # Oxygen level
        if vitals["spo2"] < self.thresholds["spo2_low"]:
            base_level += min(2, (self.thresholds["spo2_low"] - vitals["spo2"]) * 0.5)
            
        # Fall detection is critical
        if vitals["fall_detected"]:
            base_level += 5  # Big increase
            
        # Ensure 1-10 range
        return max(1, min(10, round(base_level)))
        
    def _trigger_emergency_protocol(self, vitals, anomalies):
        """Trigger emergency response"""
        # Avoid repeated alerts
        if time.time() - self.last_alert_time < 30:  # 30 second cooldown
            return
            
        self.emergency_detected = True
        self.last_alert_time = time.time()
        
        print("\n🚨 EMERGENCY DETECTED 🚨")
        print("------------------------")
        print(f"Device: {self.device_id}")
        print(f"Time: {time.strftime('%H:%M:%S')}")
        print("Anomalies detected:")
        for anomaly in anomalies:
            print(f"  - {anomaly}")
        
        print("\nVital Signs:")
        print(f"  - Temperature: {vitals['temperature']}°F")
        print(f"  - Heart Rate: {vitals['heart_rate']} BPM")
        print(f"  - SpO2: {vitals['spo2']}%")
        print(f"  - Motion: {vitals['motion']}")
        
        print("\nInitiating SOS Protocol:")
        print("  1. Sending alert to connected devices")
        print("  2. Activating mesh network emergency broadcast")
        print("  3. Preparing medical data package for responders")
        
        # In a real implementation, this would communicate with other mesh nodes
        # and potentially external services if available
        
        # Reset after 10 seconds for demo purposes
        def reset_emergency():
            time.sleep(10)
            self.emergency_detected = False
            print("\n✅ Emergency response completed. Resuming normal monitoring.\n")
            
        Thread(target=reset_emergency).start()

def main():
    print("💓 NyraLite: Wearable Health Monitor with MCP-ZERO")
    print("==================================================")
    
    # Create a mesh of devices
    mesh_devices = ["wearable-01", "base-station", "family-phone"]
    
    # Create the NyraLite agent for wearable
    nyra = NyraLiteAgent("wearable-01", mesh_devices)
    nyra.connect_to_mesh()
    
    print("\nStarting health monitoring simulation...")
    print("Commands: 'status', 'emergency', 'exit'")
    
    nyra.start_monitoring()
    
    try:
        while True:
            cmd = input("\n> ").strip().lower()
            
            if cmd == "exit":
                break
            elif cmd == "status":
                if nyra.vitals_history:
                    vitals = nyra.vitals_history[-1]
                    print(f"\nCurrent Vital Signs:")
                    print(f"  Temperature: {vitals['temperature']}°F")
                    print(f"  Heart Rate: {vitals['heart_rate']} BPM") 
                    print(f"  SpO2: {vitals['spo2']}%")
                    print(f"  Motion: {vitals['motion']}")
                    print(f"  Battery: {vitals['battery']}%")
                else:
                    print("No vitals data collected yet")
            elif cmd == "emergency":
                print("Simulating health emergency...")
                nyra.sensor.simulate_emergency()
            else:
                print("Unknown command. Try 'status', 'emergency', or 'exit'")
    except KeyboardInterrupt:
        pass
        
    print("Shutting down NyraLite monitor...")
    nyra.stop_monitoring()
    print("Shutdown complete.")

if __name__ == "__main__":
    main()
