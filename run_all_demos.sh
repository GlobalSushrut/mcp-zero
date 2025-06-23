#!/bin/bash
# Run all MCP-ZERO demos in sequence
# These demo files showcase the MCP-ZERO capabilities

DEMOS_DIR="/home/umesh/Videos/mcp_zero/examples"
PYTHONPATH="/home/umesh/Videos/mcp_zero:$PYTHONPATH"
export PYTHONPATH

echo "===== MCP-ZERO Demos Runner ====="
echo "This script will run all 5 demo applications in sequence."
echo ""

run_demo() {
  DEMO_NAME=$1
  SCRIPT_PATH=$2
  
  echo ""
  echo "================================================="
  echo "🚀 Running Demo: $DEMO_NAME"
  echo "================================================="
  echo "Press Ctrl+C to exit the current demo and continue to the next one."
  echo ""
  
  # Run the demo with a timeout
  python3 "$SCRIPT_PATH"
  
  echo ""
  echo "✅ Demo '$DEMO_NAME' completed or interrupted."
  echo "Press Enter to continue to the next demo..."
  read
}

# Demo 1: Edge Siri
run_demo "Edge Siri - Offline AI Assistant" "$DEMOS_DIR/edge_siri_demo/edge_siri.py"

# Demo 2: NyraLite Health Monitor
run_demo "NyraLite - Wearable SOS Health Monitor" "$DEMOS_DIR/nyralite_demo/nyralite.py"

# Demo 3: Design Agent
run_demo "Design Agent - Voice-Interactive Design Assistant" "$DEMOS_DIR/design_agent_demo/design_agent.py"

# Demo 4: Traffic Agent with Acceleration Server
run_demo "Traffic Agent - Edge Street Cop" "$DEMOS_DIR/traffic_agent_demo/traffic_agent.py"

# Demo 5: Dev Agent
run_demo "Dev Agent - Voice-Interactive Code Assistant" "$DEMOS_DIR/dev_agent_demo/dev_agent.py"

echo ""
echo "All demos completed. Thank you for exploring MCP-ZERO capabilities!"
