# MCP Zero Application Examples

This directory contains example implementations for various applications that can be built using the MCP Zero platform. Each example demonstrates how to implement the offline-first resilience pattern that is central to MCP Zero's architecture.

## Offline-First Resilience Pattern

All examples follow this critical pattern:

1. **Start Offline by Default**: Every component begins in offline mode
2. **Single Connection Attempt**: Components try to connect to remote services exactly once
3. **Permanent Fallback**: On connection failure, components permanently switch to offline mode
4. **Local Processing**: Full functionality is maintained using local resources when offline
5. **Progressive Enhancement**: Features are enhanced when remote services are available

## Available Examples

### Development Tools & Environments

- [Code Editor with Offline-First Intelligence](./development_tools/code_editor.py) - Demonstrates a code editor with offline-capable analysis and completion

### AI Agent Platforms

- [Autonomous Agent with Offline-First Resilience](./ai_agents/autonomous_agent.py) - Shows how to build AI agents that function independently offline

### Knowledge Management Systems

- [Personal Knowledge Base](./knowledge_management/personal_knowledge_base.py) - Example of a knowledge management system with local search and indexing

### Healthcare Applications

- [Medical Reference System](./healthcare/medical_reference.py) - Critical medical reference system that functions in disconnected environments

## Implementation Guidelines

When implementing any application with MCP Zero, follow these key practices:

1. **Initialize in Offline Mode**: Always start in offline mode by default
   ```python
   self.mode = "OFFLINE"  # Start offline by default
   ```

2. **Single Connection Attempt**: Only try to connect once, with a short timeout
   ```python
   def try_connect_once(self):
       try:
           connected = self.connection_manager.connect(timeout_seconds=2)
           if connected:
               self.mode = "ONLINE"
       except Exception:
           # No retry - remain in offline mode
           pass
   ```

3. **Permanent Fallback**: If online operations fail, permanently switch to offline mode
   ```python
   try:
       result = self.online_component.process(data)
   except Exception:
       self.mode = "OFFLINE"  # Permanent fallback
       result = self.offline_component.process(data)
   ```

4. **Always Maintain Local Functionality**: Ensure core features work offline
   ```python
   # Local component is always initialized
   self.local_processor = LocalProcessor()
   
   # Only initialize online component if needed
   if api_key:
       self.online_processor = OnlineProcessor(api_key)
   ```

5. **Progressive Enhancement**: Add advanced features when online without breaking core functionality
   ```python
   def process(self, data):
       # Basic processing always works
       result = self.local_processor.process(data)
       
       # Enhanced processing if online
       if self.mode == "ONLINE":
           try:
               enhanced = self.online_processor.enhance(result)
               result.update(enhanced)  # Enhance but don't replace
           except Exception:
               self.mode = "OFFLINE"
               # Original result is still valid
       
       return result
   ```

## License Compliance

All examples in this directory are provided under the MCP Zero Proprietary License. Use of these examples must comply with the terms specified in the main LICENSE.md file.
