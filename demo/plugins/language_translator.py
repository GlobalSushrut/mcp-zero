#!/usr/bin/env python3
"""
Language Translator Plugin for MCP-ZERO

This plugin provides translation capabilities for the IntelliAgent demo,
demonstrating how specialized functionality can be encapsulated in
modular plugins and how plugins can communicate with each other.
"""

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("mcp_zero.plugins.translator")

# Dictionary of language codes to language names
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "ja": "Japanese",
    "ru": "Russian",
    "ar": "Arabic",
    "hi": "Hindi",
    "pt": "Portuguese"
}

class LanguageTranslatorPlugin:
    """Language translator plugin implementation for MCP-ZERO."""
    
    def __init__(self, plugin_id: str, agent_id: str):
        """Initialize the language translator plugin.
        
        Args:
            plugin_id: Unique identifier for this plugin instance
            agent_id: ID of the agent this plugin is attached to
        """
        self.plugin_id = plugin_id
        self.agent_id = agent_id
        self.initialized_at = time.time()
        self.execution_count = 0
        self.translation_history = []
        logger.info(f"Language Translator Plugin initialized for agent {agent_id}")
    
    def get_info(self) -> Dict[str, Any]:
        """Return information about this plugin."""
        return {
            "id": self.plugin_id,
            "name": "Language Translator Plugin",
            "description": "Translates text between different languages",
            "version": "1.0.0",
            "agent_id": self.agent_id,
            "initialized_at": self.initialized_at,
            "execution_count": self.execution_count,
            "supported_languages": list(LANGUAGES.keys())
        }
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Return dictionary of supported language codes and names."""
        return LANGUAGES
    
    def execute(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the translation operation.
        
        Args:
            intent: The intent to execute (should be "translate")
            parameters: Parameters for the translation
            
        Returns:
            Result of the translation
        """
        self.execution_count += 1
        
        # Extract operation from intent or parameters
        operation = intent
        if intent != "translate":
            operation = parameters.get("operation", "")
            if operation != "translate":
                logger.error(f"Unknown operation: {operation}")
                return {
                    "success": False,
                    "error": "This plugin only supports the 'translate' operation",
                    "trace_id": f"trans-trace-{int(time.time())}"
                }
        
        # Get translation parameters
        text = parameters.get("text", "")
        source_lang = parameters.get("source_language", "auto").lower()
        target_lang = parameters.get("target_language", "en").lower()
        
        if not text:
            return {
                "success": False,
                "error": "No text provided for translation",
                "trace_id": f"trans-trace-{int(time.time())}"
            }
            
        # Validate languages
        if source_lang != "auto" and source_lang not in LANGUAGES:
            return {
                "success": False,
                "error": f"Unsupported source language: {source_lang}",
                "supported_languages": list(LANGUAGES.keys()),
                "trace_id": f"trans-trace-{int(time.time())}"
            }
            
        if target_lang not in LANGUAGES:
            return {
                "success": False,
                "error": f"Unsupported target language: {target_lang}",
                "supported_languages": list(LANGUAGES.keys()),
                "trace_id": f"trans-trace-{int(time.time())}"
            }
            
        # Track this translation in history (limited to last 20)
        history_entry = {
            "source_language": source_lang,
            "target_language": target_lang,
            "text_length": len(text),
            "timestamp": time.time()
        }
        self.translation_history.append(history_entry)
        if len(self.translation_history) > 20:
            self.translation_history = self.translation_history[-20:]
            
        try:
            # Create cryptographic trace for ZK audit
            trace_id = f"trans-{int(time.time())}-{hash(text) % 10000}"
            
            # For the demo, we simulate translation by adding a prefix
            if source_lang == "auto":
                detected_lang = "en"  # Simulate language detection
            else:
                detected_lang = source_lang
                
            translated_text = self._simulate_translation(text, detected_lang, target_lang)
            
            # Successful translation
            return {
                "success": True,
                "original_text": text,
                "translated_text": translated_text,
                "source_language": detected_lang,
                "source_language_name": LANGUAGES.get(detected_lang, "Unknown"),
                "target_language": target_lang,
                "target_language_name": LANGUAGES.get(target_lang, "Unknown"),
                "trace_id": trace_id,
                "agent_id": self.agent_id,
                "plugin_id": self.plugin_id,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Error executing translation: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "trace_id": f"trans-trace-{int(time.time())}"
            }
    
    def _simulate_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """Simulate translation from source to target language."""
        # In a real-world scenario, this would call a machine translation service
        # For the demo, we'll just prefix the text with language information
        source_name = LANGUAGES.get(source_lang, "Unknown")
        target_name = LANGUAGES.get(target_lang, "Unknown")
        
        if source_lang == target_lang:
            return text
            
        return f"[Translated from {source_name} to {target_name}]: {text}"
    
    def cleanup(self) -> None:
        """Cleanup resources used by this plugin."""
        logger.info(f"Cleaning up Language Translator Plugin for agent {self.agent_id}")
        # Release any resources, close connections, etc.
