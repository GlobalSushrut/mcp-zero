#!/usr/bin/env python3
"""
Design Agent: Voice-interactive design assistant using MCP-ZERO
Demonstrates tool orchestration and intent tracing capabilities.
"""
import os
import sys
import time
import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# MCP-ZERO imports
from pare_protocol.chain_protocol import PAREChainProtocol as PAREProtocol
from pare_protocol.intent_weight_bias import IntentWeightBias

# Simple data structures
@dataclass
class DesignElement:
    """Represents a design element (text, shape, image)"""
    element_id: str
    element_type: str
    x: int = 0
    y: int = 0
    width: int = 100
    height: int = 50
    color: str = "#000000"
    text: str = ""
    font: str = "Arial"
    font_size: int = 14
    opacity: float = 1.0
    rotation: int = 0
    layer: int = 0

@dataclass
class DesignCanvas:
    """Represents the design canvas"""
    width: int = 800
    height: int = 600
    background_color: str = "#FFFFFF"
    elements: List[DesignElement] = field(default_factory=list)

class DesignAgent:
    """Design agent using MCP-ZERO architecture"""
    
    def __init__(self):
        # Initialize MCP-ZERO components
        # Create a db path for this demo
        db_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "temp_db")
        os.makedirs(db_dir, exist_ok=True)
        db_path = os.path.join(db_dir, "design_agent.db")
        self.protocol = PAREProtocol(db_path=db_path, rpc_url="http://localhost:50051")
        self.agent_id = "design-agent"
        self.intent_bias = IntentWeightBias(dimensions=(4, 4))
        self.canvas = DesignCanvas()
        self.next_element_id = 1
        self.history = []
        
    def process_command(self, command: str) -> Dict[str, Any]:
        """Process a design command and update the canvas"""
        # Create training block for this design command
        trace_id = self.protocol.create_training_block(
            agent_id=self.agent_id,
            block_type="design_command",
            metadata={"timestamp": time.time()}
        )
        
        # Record command in memory trace
        self.protocol.add_training_data(
            block_id=trace_id,
            data_content=json.dumps({"command": command}),
            data_type="command_input",
            metadata={"agent_id": self.agent_id}
        )
        
        # Add to history
        self.history.append({"command": command, "timestamp": time.time()})
        
        # Parse command and execute appropriate function
        response = {"success": False, "message": "Command not recognized"}
        
        # Text commands
        if "add text" in command.lower():
            text = command.lower().replace("add text", "").strip()
            if not text:
                text = "Sample Text"
            element = self._add_text(text)
            response = {
                "success": True,
                "message": f"Added text element: '{text}'",
                "element": asdict(element)
            }
            
        # Shape commands
        elif "add rectangle" in command.lower() or "add box" in command.lower():
            element = self._add_shape("rectangle")
            response = {
                "success": True, 
                "message": "Added rectangle to canvas",
                "element": asdict(element)
            }
            
        elif "add circle" in command.lower():
            element = self._add_shape("circle")
            response = {
                "success": True,
                "message": "Added circle to canvas",
                "element": asdict(element)
            }
            
        # Color commands
        elif "color" in command.lower() or "set color" in command.lower():
            color = self._extract_color(command)
            if color:
                if self.canvas.elements:
                    element = self.canvas.elements[-1]
                    element.color = color
                    response = {
                        "success": True,
                        "message": f"Set color to {color}",
                        "element": asdict(element)
                    }
                else:
                    response = {"success": False, "message": "No elements to color"}
            else:
                response = {"success": False, "message": "No color specified"}
                
        # Position commands
        elif "align" in command.lower():
            if "left" in command.lower():
                self._align_elements("left")
                response = {"success": True, "message": "Aligned elements to left"}
            elif "right" in command.lower():
                self._align_elements("right")
                response = {"success": True, "message": "Aligned elements to right"}
            elif "center" in command.lower():
                self._align_elements("center")
                response = {"success": True, "message": "Aligned elements to center"}
                
        # Background commands
        elif "background" in command.lower():
            color = self._extract_color(command)
            if color:
                self.canvas.background_color = color
                response = {"success": True, "message": f"Set background to {color}"}
                
        # Export commands
        elif "export" in command.lower():
            response = {"success": True, "message": "Design exported (simulated)"}
            
        # Status command
        elif "status" in command.lower() or "elements" in command.lower():
            response = {
                "success": True,
                "message": f"Canvas has {len(self.canvas.elements)} elements",
                "canvas": asdict(self.canvas)
            }
            
        # Record result in memory trace
        self.protocol.add_llm_call(
            block_id=trace_id,
            prompt=command,
            result=json.dumps(response),
            metadata={"agent_id": self.agent_id, "model": "design-agent-v1"}
        )
        
        return response
    
    def _add_text(self, text: str) -> DesignElement:
        """Add a text element to the canvas"""
        element = DesignElement(
            element_id=f"e{self.next_element_id}",
            element_type="text",
            text=text,
            x=self.canvas.width // 4,
            y=self.canvas.height // 4
        )
        self.canvas.elements.append(element)
        self.next_element_id += 1
        return element
    
    def _add_shape(self, shape_type: str) -> DesignElement:
        """Add a shape element to the canvas"""
        element = DesignElement(
            element_id=f"e{self.next_element_id}",
            element_type=shape_type,
            x=self.canvas.width // 4,
            y=self.canvas.height // 4
        )
        self.canvas.elements.append(element)
        self.next_element_id += 1
        return element
    
    def _extract_color(self, command: str) -> Optional[str]:
        """Extract color from command"""
        colors = {
            "red": "#FF0000",
            "blue": "#0000FF",
            "green": "#00FF00",
            "yellow": "#FFFF00",
            "black": "#000000",
            "white": "#FFFFFF",
            "purple": "#800080",
            "orange": "#FFA500",
            "gray": "#808080"
        }
        
        for color_name, color_hex in colors.items():
            if color_name in command.lower():
                return color_hex
        return None
    
    def _align_elements(self, alignment: str):
        """Align elements on the canvas"""
        if not self.canvas.elements:
            return
            
        for element in self.canvas.elements:
            if alignment == "left":
                element.x = 10
            elif alignment == "right":
                element.x = self.canvas.width - element.width - 10
            elif alignment == "center":
                element.x = (self.canvas.width - element.width) // 2

    def render_ascii(self) -> str:
        """Render a simple ASCII representation of the canvas"""
        width = 60
        height = 20
        
        # Create an empty canvas
        canvas = [[" " for _ in range(width)] for _ in range(height)]
        
        # Draw each element (basic representation)
        for element in self.canvas.elements:
            # Scale coordinates to ascii dimensions
            x = int(element.x * width / self.canvas.width)
            y = int(element.y * height / self.canvas.height)
            w = max(1, int(element.width * width / self.canvas.width))
            h = max(1, int(element.height * height / self.canvas.height))
            
            # Keep within bounds
            x = min(x, width - 1)
            y = min(y, height - 1)
            
            # Choose symbol based on element type
            symbol = "?"
            if element.element_type == "text":
                symbol = "T"
            elif element.element_type == "rectangle":
                symbol = "█"
            elif element.element_type == "circle":
                symbol = "●"
                
            # Draw the element
            for dy in range(min(h, height - y)):
                for dx in range(min(w, width - x)):
                    if 0 <= y+dy < height and 0 <= x+dx < width:
                        canvas[y+dy][x+dx] = symbol
        
        # Convert to string
        result = "+" + "-" * width + "+\n"
        for row in canvas:
            result += "|" + "".join(row) + "|\n"
        result += "+" + "-" * width + "+"
        
        return result

def main():
    print("🎨 Design Agent: Voice-to-Design Tool with MCP-ZERO")
    print("==================================================")
    
    agent = DesignAgent()
    
    print("Ready for design commands!")
    print("Try commands like:")
    print("  - 'Add text Hello World'")
    print("  - 'Add rectangle'") 
    print("  - 'Set color to blue'")
    print("  - 'Align center'")
    print("  - 'Export'")
    
    while True:
        command = input("\n🎙️ Say design command: ")
        
        if command.lower() == "exit":
            print("Exiting design tool.")
            break
            
        result = agent.process_command(command)
        print(f"🤖 {result['message']}")
        
        # Show current canvas state
        if len(agent.canvas.elements) > 0:
            print("\nCurrent Canvas:")
            print(agent.render_ascii())
            print(f"Elements: {len(agent.canvas.elements)}")

if __name__ == "__main__":
    main()
