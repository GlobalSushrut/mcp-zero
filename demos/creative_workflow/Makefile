.PHONY: test run docker-build docker-run clean help

# Default target
.DEFAULT_GOAL := help

# Variables
PYTHON = python3
OUTPUT_DIR = ./output
DOCKER_IMAGE = mcp-creative-workflow
DOCKER_TAG = latest

help:  ## Show this help menu
	@echo "MCP-ZERO Creative Workflow Demo"
	@echo ""
	@echo "Usage: make [TARGET]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

run:  ## Run the creative workflow demo
	$(PYTHON) run_creative_demo.py

run-mock:  ## Run the demo in mock mode (without RPC server)
	$(PYTHON) run_creative_demo.py --mock

test:  ## Run the test suite
	$(PYTHON) -m pytest test_creative_workflow.py -v

test-ci:  ## Run tests for CI environment
	$(PYTHON) -m pytest test_creative_workflow.py -v --junitxml=test-results.xml

verify-resources:  ## Verify hardware constraints are met
	@echo "Verifying resource constraints (<27% CPU, <827MB RAM)..."
	$(PYTHON) -c "from setup import ResourceMonitor; monitor = ResourceMonitor(); usage = monitor.report_usage(); print(f'CPU: {usage[\"cpu_percent\"]}%, RAM: {usage[\"memory_mb\"]}MB'); assert usage['cpu_percent'] < 27 and usage['memory_mb'] < 827, 'Resource constraints violated!'"

docker-build:  ## Build the Docker image
	docker build -t $(DOCKER_IMAGE):$(DOCKER_TAG) .

docker-run:  ## Run the demo in Docker
	docker run --env MCP_RPC_URL=http://host.docker.internal:8082 -v "$(shell pwd)/$(OUTPUT_DIR):/app/output" $(DOCKER_IMAGE):$(DOCKER_TAG)

docker-compose-up:  ## Run with Docker Compose (includes MCP-ZERO server)
	docker-compose up

docker-compose-down:  ## Stop Docker Compose services
	docker-compose down

clean:  ## Remove output files and test artifacts
	rm -rf $(OUTPUT_DIR)/*.txt $(OUTPUT_DIR)/*.json
	rm -f test-results.xml
	rm -rf __pycache__ .pytest_cache

clean-all: clean  ## Remove all generated files including Docker images
	docker-compose down -v
	docker rmi $(DOCKER_IMAGE):$(DOCKER_TAG) || true
