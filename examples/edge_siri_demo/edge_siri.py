#!/usr/bin/env python3
"""
Edge Siri: Fully offline voice assistant using MCP-ZERO
Demonstrates intent parsing, memory trace, and local execution without cloud.
"""
import os
import sys
import json
import time
from threading import Thread

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP-ZERO imports
from pare_protocol.intent_weight_bias import IntentWeightBias
from pare_protocol.chain_protocol import PAREChainProtocol as PAREProtocol
from pare_protocol.intent_consensus import IntentAwareConsensus

# Mock speech recognition (would use a real library in production)
class SpeechRecognition:
    def listen(self):
        # In a real implementation, this would use a microphone
        user_input = input("🎤 Say something (or type 'exit' to quit): ")
        return user_input

# Mock device control (would use actual IoT libraries in production)
class SmartHomeControl:
    def __init__(self):
        self.devices = {
            "living_room_light": {"state": "off", "type": "light"},
            "kitchen_light": {"state": "off", "type": "light"},
            "thermostat": {"state": 70, "type": "temperature"},
            "music_player": {"state": "off", "track": None, "type": "media"}
        }
        
    def execute_command(self, device_name, command, value=None):
        if device_name not in self.devices:
            return f"Device {device_name} not found"
            
        device = self.devices[device_name]
        
        if command == "turn_on" and device["type"] in ["light", "media"]:
            device["state"] = "on"
            return f"{device_name} turned on"
            
        elif command == "turn_off" and device["type"] in ["light", "media"]:
            device["state"] = "off"
            return f"{device_name} turned off"
            
        elif command == "set_temp" and device["type"] == "temperature":
            device["state"] = value
            return f"Thermostat set to {value}°F"
            
        elif command == "play" and device["type"] == "media":
            device["state"] = "playing"
            device["track"] = value
            return f"Playing {value}"
            
        return "Command not recognized"

# Edge Siri Agent using MCP-ZERO
class EdgeSiriAgent:
    def __init__(self):
        # Initialize MCP-ZERO components
        self.intent_bias = IntentWeightBias(dimensions=(8, 8))
        # Create a db path for this demo
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "edge_siri.db")
        self.protocol = PAREProtocol(db_path=db_path, rpc_url="http://localhost:50051")
        self.agent_id = "edge-siri-agent"
        
        # Setup consensus mechanism - for multi-device coordination
        self.consensus = IntentAwareConsensus(intent_dimensions=(8, 8), learning_rate=0.05)
        
        # Initialize home control
        self.home = SmartHomeControl()
        
        # Define intent patterns for command recognition
        self.intent_patterns = {
            "light_control": ["turn on", "turn off", "lights", "light"],
            "temperature_control": ["temperature", "thermostat", "degrees", "cooler", "warmer"],
            "media_control": ["play", "music", "song", "stop", "volume"],
            "status_request": ["status", "state", "how is", "what is"],
            "general_help": ["help", "what can you do", "commands"]
        }
        
        # Load local news (would be periodically updated from local cache)
        self.local_news = [
            "Local temperature today will be 72°F with partly cloudy conditions",
            "Community garden event happening this weekend at Central Park",
            "Road construction on Main Street expected to cause delays"
        ]
        
    def process_command(self, text):
        # Create training block for this command
        process_id = self.protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="command_processing",
            metadata={"command": text, "timestamp": time.time()}
        )
        
        # Determine intent using MCP-ZERO intent learning
        intent = self.determine_intent(text.lower())
        
        # Record intent in training block
        self.protocol.add_training_data(
            block_id=process_id,
            data_content=json.dumps({"text": text, "classified_intent": intent}),
            data_type="intent_classification",
            metadata={"confidence": 0.85}
        )
        
        # Process based on intent
        if intent == "light_control":
            response = self._handle_light_command(text.lower())
        elif intent == "temperature_control":
            response = self._handle_temperature_command(text.lower())
        elif intent == "media_control":
            response = self._handle_media_command(text.lower())
        elif intent == "status_request":
            response = self._handle_status_request(text.lower())
        elif intent == "local_news":
            response = self._get_local_news()
        else:
            response = "I'm not sure how to help with that. Try asking about lights, temperature, or music."
            
        # Record result in memory trace
        self.protocol.add_llm_call(
            block_id=process_id,
            prompt=text,
            result=response,
            metadata={"model": "local-intent-model-v1"}
        )
        
        # No need to explicitly close the memory trace
        
        return response
    
    def determine_intent(self, text):
        # Simple keyword-based intent matching
        # In a full implementation, this would use the intent_bias model with learning
        max_score = 0
        detected_intent = "unknown"
        
        for intent, keywords in self.intent_patterns.items():
            score = sum(1 for keyword in keywords if keyword in text)
            if score > max_score:
                max_score = score
                detected_intent = intent
                
        if "news" in text:
            return "local_news"
            
        return detected_intent
    
    def _handle_light_command(self, text):
        if "living room" in text or "livingroom" in text:
            device = "living_room_light"
        elif "kitchen" in text:
            device = "kitchen_light"
        else:
            return "Which light do you want to control? Try 'living room' or 'kitchen'"
            
        if "on" in text or "turn on" in text:
            return self.home.execute_command(device, "turn_on")
        elif "off" in text or "turn off" in text:
            return self.home.execute_command(device, "turn_off")
            
        return "Do you want to turn the light on or off?"
    
    def _handle_temperature_command(self, text):
        # Extract temperature value if present
        import re
        temp_match = re.search(r'(\d+)\s*degrees', text)
        
        if temp_match:
            temp = int(temp_match.group(1))
            return self.home.execute_command("thermostat", "set_temp", temp)
        elif "warmer" in text:
            current = self.home.devices["thermostat"]["state"]
            return self.home.execute_command("thermostat", "set_temp", current + 2)
        elif "cooler" in text:
            current = self.home.devices["thermostat"]["state"]
            return self.home.execute_command("thermostat", "set_temp", current - 2)
            
        return f"Current temperature is set to {self.home.devices['thermostat']['state']}°F"
    
    def _handle_media_command(self, text):
        if "play" in text:
            # Extract song name if present
            song = text.split("play")[1].strip() if "play" in text else "default music"
            return self.home.execute_command("music_player", "play", song)
        elif "stop" in text or "off" in text:
            return self.home.execute_command("music_player", "turn_off")
            
        return "Music player is currently " + self.home.devices["music_player"]["state"]
    
    def _handle_status_request(self, text):
        statuses = []
        for device_name, device in self.home.devices.items():
            if device["type"] == "temperature":
                statuses.append(f"{device_name} is set to {device['state']}°F")
            elif device["type"] == "media" and device["state"] == "playing":
                statuses.append(f"{device_name} is playing {device['track']}")
            else:
                statuses.append(f"{device_name} is {device['state']}")
                
        return "Current status:\n" + "\n".join(statuses)
    
    def _get_local_news(self):
        return "Here's your local news:\n" + "\n".join(self.local_news)

def main():
    print("🏠 Edge Siri: Offline Voice Assistant Using MCP-ZERO")
    print("====================================================")
    
    agent = EdgeSiriAgent()
    speech = SpeechRecognition()
    
    print("🎙️  Edge Siri is ready! No cloud servers, no network needed.")
    print("Try commands like:")
    print("  - 'Turn on the living room light'")
    print("  - 'Set temperature to 72 degrees'")
    print("  - 'Play some relaxing music'")
    print("  - 'What's the local news?'")
    print("  - 'What's the status of my home?'")
    
    while True:
        command = speech.listen()
        
        if command.lower() == 'exit':
            print("Shutting down Edge Siri. Goodbye!")
            break
            
        response = agent.process_command(command)
        print(f"🤖 {response}")

if __name__ == "__main__":
    main()
