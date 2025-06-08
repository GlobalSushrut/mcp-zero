#!/usr/bin/env python3
"""
Calculator Plugin for MCP-ZERO

This plugin provides computational capabilities for the IntelliAgent demo.
It demonstrates how specialized functionality can be encapsulated in
modular plugins that extend agent capabilities.
"""

import os
import json
import time
import math
import logging
from typing import Dict, Any, Union, Optional

logger = logging.getLogger("mcp_zero.plugins.calculator")

class CalculatorPlugin:
    """Calculator plugin implementation for MCP-ZERO."""
    
    def __init__(self, plugin_id: str, agent_id: str):
        """Initialize the calculator plugin.
        
        Args:
            plugin_id: Unique identifier for this plugin instance
            agent_id: ID of the agent this plugin is attached to
        """
        self.plugin_id = plugin_id
        self.agent_id = agent_id
        self.initialized_at = time.time()
        self.execution_count = 0
        self.operation_history = []
        logger.info(f"Calculator Plugin initialized for agent {agent_id}")
    
    def get_info(self) -> Dict[str, Any]:
        """Return information about this plugin."""
        return {
            "id": self.plugin_id,
            "name": "Calculator Plugin",
            "description": "Performs mathematical operations and computations",
            "version": "1.0.0",
            "agent_id": self.agent_id,
            "initialized_at": self.initialized_at,
            "execution_count": self.execution_count,
            "capabilities": [
                "add", "subtract", "multiply", "divide", 
                "power", "sqrt", "log", "factorial"
            ]
        }
    
    def execute(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an intent with the given parameters.
        
        The calculator plugin supports various mathematical operations.
        
        Args:
            intent: The intent to execute (operation type)
            parameters: Parameters for the calculation
            
        Returns:
            Result of the calculation
        """
        self.execution_count += 1
        
        # Extract operation type from intent or parameters
        operation = intent
        if intent == "compute" or intent == "calculate":
            operation = parameters.get("operation", "")
        
        # Track this operation in history (limited to last 20)
        history_entry = {
            "operation": operation,
            "parameters": parameters,
            "timestamp": time.time()
        }
        self.operation_history.append(history_entry)
        if len(self.operation_history) > 20:
            self.operation_history = self.operation_history[-20:]
        
        # Execute the operation
        handlers = {
            "add": self._add,
            "subtract": self._subtract,
            "multiply": self._multiply,
            "divide": self._divide,
            "power": self._power,
            "sqrt": self._sqrt,
            "log": self._log,
            "factorial": self._factorial
        }
        
        handler = handlers.get(operation)
        if not handler:
            logger.error(f"Unknown operation: {operation}")
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
                "trace_id": f"calc-trace-{int(time.time())}"
            }
            
        try:
            # Create cryptographic trace for ZK audit
            trace_id = f"calc-{int(time.time())}-{hash(str(parameters)) % 10000}"
            
            # Execute calculation
            result = handler(parameters)
            
            # Successful calculation
            response = {
                "success": True,
                "operation": operation,
                "result": result,
                "trace_id": trace_id,
                "agent_id": self.agent_id,
                "plugin_id": self.plugin_id,
                "timestamp": time.time()
            }
            
            # Add input parameters for completeness
            response.update({k: v for k, v in parameters.items() if k not in response})
            return response
            
        except Exception as e:
            logger.error(f"Error executing operation {operation}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "trace_id": f"calc-trace-{int(time.time())}"
            }
    
    def _extract_numeric_params(self, parameters: Dict[str, Any]) -> Dict[str, float]:
        """Extract and convert numeric parameters."""
        result = {}
        for key, value in parameters.items():
            if key in ["a", "b", "x", "n", "base"]:
                try:
                    result[key] = float(value)
                except (ValueError, TypeError):
                    raise ValueError(f"Invalid numeric value for {key}: {value}")
        return result
    
    def _add(self, parameters: Dict[str, Any]) -> str:
        """Add two numbers."""
        params = self._extract_numeric_params(parameters)
        a = params.get("a", 0)
        b = params.get("b", 0)
        return str(a + b)
    
    def _subtract(self, parameters: Dict[str, Any]) -> str:
        """Subtract two numbers."""
        params = self._extract_numeric_params(parameters)
        a = params.get("a", 0)
        b = params.get("b", 0)
        return str(a - b)
    
    def _multiply(self, parameters: Dict[str, Any]) -> str:
        """Multiply two numbers."""
        params = self._extract_numeric_params(parameters)
        a = params.get("a", 0)
        b = params.get("b", 0)
        return str(a * b)
    
    def _divide(self, parameters: Dict[str, Any]) -> str:
        """Divide two numbers."""
        params = self._extract_numeric_params(parameters)
        a = params.get("a", 0)
        b = params.get("b", 0)
        if b == 0:
            raise ValueError("Division by zero")
        return str(a / b)
    
    def _power(self, parameters: Dict[str, Any]) -> str:
        """Calculate x raised to power n."""
        params = self._extract_numeric_params(parameters)
        x = params.get("x", 0)
        n = params.get("n", 0)
        return str(math.pow(x, n))
    
    def _sqrt(self, parameters: Dict[str, Any]) -> str:
        """Calculate square root of x."""
        params = self._extract_numeric_params(parameters)
        x = params.get("x", 0)
        if x < 0:
            raise ValueError("Cannot calculate square root of negative number")
        return str(math.sqrt(x))
    
    def _log(self, parameters: Dict[str, Any]) -> str:
        """Calculate logarithm of x with given base."""
        params = self._extract_numeric_params(parameters)
        x = params.get("x", 0)
        base = params.get("base", math.e)
        if x <= 0:
            raise ValueError("Cannot calculate logarithm of non-positive number")
        if base <= 0 or base == 1:
            raise ValueError("Invalid logarithm base")
        return str(math.log(x, base))
    
    def _factorial(self, parameters: Dict[str, Any]) -> str:
        """Calculate factorial of n."""
        params = self._extract_numeric_params(parameters)
        n = params.get("n", 0)
        if n < 0:
            raise ValueError("Cannot calculate factorial of negative number")
        if n > 170:
            raise ValueError("Input too large for factorial calculation")
        n_int = int(n)
        if n != n_int:
            raise ValueError("Cannot calculate factorial of non-integer")
        return str(math.factorial(n_int))
    
    def cleanup(self) -> None:
        """Cleanup resources used by this plugin."""
        logger.info(f"Cleaning up Calculator Plugin for agent {self.agent_id}")
        # Release any resources
