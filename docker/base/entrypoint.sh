#!/bin/bash
# MCP Zero container entrypoint script
# Implements offline-first resilience pattern

set -e

# Configure offline-first behavior
if [[ "${MCP_OFFLINE_FIRST}" == "true" ]]; then
  echo "Starting in offline-first mode - will attempt connection once only"
  export MCP_CONNECTION_ATTEMPTS=1
  export MCP_START_OFFLINE=true
fi

# Check for remote services but don't fail if they're unavailable
if [[ -n "${MCP_SERVICE_CHECK_URL}" ]]; then
  echo "Testing connection to remote services..."
  if curl --silent --fail --max-time 2 "${MCP_SERVICE_CHECK_URL}" > /dev/null 2>&1; then
    echo "Remote services are available"
    export MCP_REMOTE_AVAILABLE=true
  else
    echo "Remote services unavailable - using local processing mode"
    export MCP_REMOTE_AVAILABLE=false
  fi
else
  echo "No service check URL configured - assuming offline mode"
  export MCP_REMOTE_AVAILABLE=false
fi

# Execute the passed command
exec "$@"
