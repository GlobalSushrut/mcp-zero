# MCP-ZERO Build System
# Edge AI Operating System

.PHONY: all build-kernel build-gateway test lint clean help release install start stop

# Default target
all: build-kernel build-gateway

# Build Rust kernel
build-kernel:
	@echo "Building Rust kernel..."
	cd src/kernel && cargo build --release
	@echo "Kernel built: src/kernel/target/release/mcp-kernel"

# Build Go gateway
build-gateway:
	@echo "Building Go gateway..."
	cd src/gateway && go build -ldflags="-s -w" -o gateway .
	@echo "Gateway built: src/gateway/gateway"

# Run all tests
test: test-kernel test-gateway test-python
	@echo "All tests passed."

test-kernel:
	@echo "Testing Rust kernel..."
	cd src/kernel && cargo test

test-gateway:
	@echo "Testing Go gateway..."
	cd src/gateway && go test ./...

test-python:
	@echo "Testing Python cognitive..."
	cd core && python -m pytest ../tests/ -v

# Lint all code
lint: lint-kernel lint-gateway lint-python
	@echo "All lints passed."

lint-kernel:
	cd src/kernel && cargo clippy -- -D warnings

lint-gateway:
	cd src/gateway && go vet ./...

lint-python:
	cd core && python -m flake8 umeshian_construct/ --max-line-length=120

# Clean build artifacts
clean:
	cd src/kernel && cargo clean
	rm -f src/gateway/gateway
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean."

# Show binary sizes
sizes:
	@echo "=== Binary Sizes ==="
	@ls -lh src/kernel/target/release/mcp-kernel 2>/dev/null || echo "Kernel not built"
	@ls -lh src/gateway/gateway 2>/dev/null || echo "Gateway not built"

# Release build (stripped binaries)
release: build-kernel
	@echo "Building stripped Go gateway..."
	cd src/gateway && go build -ldflags="-s -w" -o gateway .
	@echo "=== Release Binaries ==="
	@ls -lh src/kernel/target/release/mcp-kernel
	@ls -lh src/gateway/gateway
	@echo "Release ready."

# Install to system (requires root)
install: release
	sudo bash scripts/install.sh

# Start the system (dev mode)
start:
	bash scripts/start.sh

# Stop the system
stop:
	@echo "Stopping MCP-ZERO..."
	@pkill -f mcp-kernel 2>/dev/null || true
	@pkill -f "gateway.*mcp" 2>/dev/null || true
	@rm -f /tmp/mcp-kernel.sock
	@echo "Stopped."

# Show help
help:
	@echo "MCP-ZERO Build Targets:"
	@echo "  make all            - Build kernel + gateway"
	@echo "  make build-kernel   - Build Rust kernel"
	@echo "  make build-gateway  - Build Go gateway"
	@echo "  make release        - Build stripped release binaries"
	@echo "  make test           - Run all tests"
	@echo "  make lint           - Lint all code"
	@echo "  make clean          - Remove build artifacts"
	@echo "  make sizes          - Show binary sizes"
	@echo "  make start          - Start system (dev mode)"
	@echo "  make stop           - Stop system"
	@echo "  make install        - Install to /opt/mcpzero (requires root)"
