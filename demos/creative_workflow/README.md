# MCP-ZERO Creative Workflow Demo

![Build Status](https://github.com/mcp-zero/mcp-zero/workflows/MCP-ZERO%20Creative%20Workflow%20Demo/badge.svg)
![Hardware Constraints](https://img.shields.io/badge/CPU-%3C27%25-green)
![Hardware Constraints](https://img.shields.io/badge/RAM-%3C827MB-green)

This demo showcases MCP-ZERO's ability to orchestrate a complex creative workflow for video production through multiple specialized agents, all governed by a Solidity-inspired agreement.

## Overview

The demo simulates an Adobe Creative Suite-like video production workflow using multiple MCP-ZERO agents:

1. **ScriptAgent** - Writes narrative scripts using LLM capabilities
2. **VisualAgent** - Creates visual scenes based on script descriptions
3. **AudioAgent** - Generates soundtrack and audio elements
4. **EditorAgent** - Composites all elements into a final video

All agents operate under a formal agreement that enforces:
- Resource constraints (CPU < 27%, RAM < 827MB)
- Content policies (no explicit violence, hate speech)
- Quality standards (resolution, framerate)

## Components

- **setup.py** - Resource monitoring and environment initialization
- **creative_agents.py** - Agent class definitions with MCP-ZERO RPC integration
- **creative_agreement.py** - Solidity-inspired agreement for creative collaboration
- **workflow_simulation.py** - Core workflow orchestration
- **scene_generation.py** - Visual scene creation with resource monitoring
- **audio_generation.py** - Audio generation with mood analysis
- **video_editor.py** - Timeline creation and rendering
- **run_creative_demo.py** - Main entry point for the demo

## Running the Demo

### Prerequisites:
- MCP-ZERO RPC server running (default: `http://localhost:8082`)
- Python 3.8+ with required dependencies

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### Local Development

```bash
# From the demos/creative_workflow directory
python run_creative_demo.py

# With custom parameters
python run_creative_demo.py --project-name "Climate Solutions" --description "A documentary about climate change solutions"

# Run without RPC server (mock mode)
python run_creative_demo.py --mock
```

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up

# Run just the demo against an existing MCP server
docker build -t mcp-creative-workflow .
docker run --env MCP_RPC_URL=http://host.docker.internal:8082 -v "$(pwd)/output:/app/output" mcp-creative-workflow
```

## Demo Output

The demo will create:
1. A script file (`project-{id}_script.txt`)
2. Scene metadata files for each visual scene
3. Audio soundtrack metadata
4. Video timeline and rendering metadata
5. Final project metadata (`project_{id}_metadata.json`)

All outputs are generated in the `output/` directory.

## Resource Monitoring

The demo maintains strict adherence to MCP-ZERO hardware constraints:
- CPU usage stays below 27% of a single core
- RAM usage stays below 827MB

Resource usage is tracked throughout the workflow and verified against the agreement for each action.

## Agreement Verification

Each agent action (script generation, visual creation, etc.) is verified against the creative agreement before execution. The verification enforces:
1. Resource limitations
2. Content policies
3. Quality standards

The system uses cryptographic hashing for ZK-traceable auditing of all operations.

## CI/CD Integration

This demo includes GitHub Actions workflow configuration for continuous integration:

- Automatic testing on push/PR to main branch
- Resource constraint verification
- Ethical governance compliance checks
- Docker image building and publishing

The CI checks ensure that all contributions maintain strict adherence to MCP-ZERO's hardware constraints (<27% CPU, <827MB RAM) and ethical governance requirements.

## Extending the Demo

To extend this demo:
1. Add more specialized agents 
2. Enhance the agreement with additional constraints
3. Connect to real LLMs for content generation
4. Implement actual rendering capabilities
5. Add specialized plugins for industry-specific creative workflows

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Ensure your contributions maintain the resource constraints and pass all CI checks.
