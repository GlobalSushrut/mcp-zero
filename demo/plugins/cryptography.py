#!/usr/bin/env python3
"""
Cryptography Plugin for MCP-ZERO

This plugin provides cryptographic capabilities for secure data handling.
It demonstrates the security-focused features of MCP-ZERO and how
specialized security features can be encapsulated in plugins.
"""

import os
import json
import time
import hashlib
import base64
import secrets
import logging
from typing import Dict, Any, Union, Optional, Tuple
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import hashes, hmac
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger("mcp_zero.plugins.cryptography")

class CryptographyPlugin:
    """Cryptography plugin implementation for MCP-ZERO."""
    
    def __init__(self, plugin_id: str, agent_id: str):
        """Initialize the cryptography plugin.
        
        Args:
            plugin_id: Unique identifier for this plugin instance
            agent_id: ID of the agent this plugin is attached to
        """
        self.plugin_id = plugin_id
        self.agent_id = agent_id
        self.initialized_at = time.time()
        self.execution_count = 0
        
        # Create plugin-specific signing key for integrity
        self.signing_key = secrets.token_bytes(32)
        
        logger.info(f"Cryptography Plugin initialized for agent {agent_id}")
    
    def get_info(self) -> Dict[str, Any]:
        """Return information about this plugin."""
        return {
            "id": self.plugin_id,
            "name": "Cryptography Plugin",
            "description": "Provides cryptographic operations for secure data handling",
            "version": "1.0.0",
            "agent_id": self.agent_id,
            "initialized_at": self.initialized_at,
            "execution_count": self.execution_count,
            "capabilities": [
                "hash", "encrypt", "decrypt", "sign", "verify", "generate_key"
            ]
        }
    
    def execute(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a cryptographic operation.
        
        Args:
            intent: The cryptographic operation to perform
            parameters: Parameters for the operation
            
        Returns:
            Result of the cryptographic operation
        """
        self.execution_count += 1
        
        # Extract operation from intent or parameters
        operation = intent
        if intent == "crypto":
            operation = parameters.get("operation", "")
        
        # Execute the operation
        handlers = {
            "hash": self._hash_data,
            "encrypt": self._encrypt_data,
            "decrypt": self._decrypt_data,
            "sign": self._sign_data,
            "verify": self._verify_signature,
            "generate_key": self._generate_key
        }
        
        handler = handlers.get(operation)
        if not handler:
            logger.error(f"Unknown cryptographic operation: {operation}")
            return {
                "success": False,
                "error": f"Unknown cryptographic operation: {operation}",
                "trace_id": f"crypto-trace-{int(time.time())}"
            }
            
        try:
            # Create cryptographic trace for ZK audit
            trace_id = f"crypto-{int(time.time())}-{hash(str(parameters)) % 10000}"
            
            # Execute cryptographic operation
            result = handler(parameters)
            
            # Successful cryptographic operation
            response = {
                "success": True,
                "operation": operation,
                "trace_id": trace_id,
                "agent_id": self.agent_id,
                "plugin_id": self.plugin_id,
                "timestamp": time.time()
            }
            response.update(result)
            return response
            
        except Exception as e:
            logger.error(f"Error executing cryptographic operation {operation}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "trace_id": f"crypto-trace-{int(time.time())}"
            }
    
    def _hash_data(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Hash data using various algorithms."""
        data = parameters.get("data", "")
        algorithm = parameters.get("algorithm", "sha256").lower()
        
        if not data:
            raise ValueError("No data provided for hashing")
            
        # Convert string data to bytes
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Hash with the specified algorithm
        if algorithm == "sha256":
            hash_obj = hashlib.sha256(data_bytes)
        elif algorithm == "sha512":
            hash_obj = hashlib.sha512(data_bytes)
        elif algorithm == "blake3":
            # Using SHA3 as BLAKE3 might not be available in standard lib
            hash_obj = hashlib.sha3_256(data_bytes)
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
            
        # Return the hash digest in hexadecimal
        return {
            "hash": hash_obj.hexdigest(),
            "algorithm": algorithm
        }
    
    def _encrypt_data(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Encrypt data using AES-GCM."""
        data = parameters.get("data", "")
        key = parameters.get("key", None)
        
        if not data:
            raise ValueError("No data provided for encryption")
            
        # Convert data to bytes
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Generate a key if not provided
        if key is None:
            # Generate a random 256-bit key
            key = secrets.token_bytes(32)
            key_b64 = base64.b64encode(key).decode('utf-8')
        else:
            # Decode provided key from base64
            try:
                key = base64.b64decode(key)
                key_b64 = parameters.get("key")
            except:
                raise ValueError("Invalid encryption key format")
        
        # Generate a random 96-bit IV
        iv = secrets.token_bytes(12)
        
        # Create an encryptor
        cipher = Cipher(algorithms.AES(key), modes.GCM(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        
        # Encrypt the data
        ciphertext = encryptor.update(data_bytes) + encryptor.finalize()
        
        # Get the tag
        tag = encryptor.tag
        
        # Encode results in base64
        iv_b64 = base64.b64encode(iv).decode('utf-8')
        ciphertext_b64 = base64.b64encode(ciphertext).decode('utf-8')
        tag_b64 = base64.b64encode(tag).decode('utf-8')
        
        return {
            "ciphertext": ciphertext_b64,
            "iv": iv_b64,
            "tag": tag_b64,
            "key": key_b64,
            "algorithm": "AES-GCM"
        }
    
    def _decrypt_data(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Decrypt data using AES-GCM."""
        ciphertext = parameters.get("ciphertext", "")
        iv = parameters.get("iv", "")
        tag = parameters.get("tag", "")
        key = parameters.get("key", "")
        
        if not all([ciphertext, iv, tag, key]):
            raise ValueError("Missing required parameters for decryption")
            
        try:
            # Decode from base64
            ciphertext_bytes = base64.b64decode(ciphertext)
            iv_bytes = base64.b64decode(iv)
            tag_bytes = base64.b64decode(tag)
            key_bytes = base64.b64decode(key)
            
            # Create a decryptor
            cipher = Cipher(algorithms.AES(key_bytes), modes.GCM(iv_bytes, tag_bytes), backend=default_backend())
            decryptor = cipher.decryptor()
            
            # Decrypt the data
            plaintext = decryptor.update(ciphertext_bytes) + decryptor.finalize()
            
            # Try to decode as UTF-8 if possible
            try:
                plaintext_str = plaintext.decode('utf-8')
            except UnicodeDecodeError:
                plaintext_str = base64.b64encode(plaintext).decode('utf-8')
                
            return {
                "plaintext": plaintext_str
            }
        except Exception as e:
            raise ValueError(f"Decryption failed: {str(e)}")
    
    def _sign_data(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Sign data using HMAC."""
        data = parameters.get("data", "")
        key = parameters.get("key", None)
        
        if not data:
            raise ValueError("No data provided for signing")
            
        # Convert data to bytes
        data_bytes = data.encode('utf-8') if isinstance(data, str) else data
        
        # Use plugin signing key if no key provided
        if key is None:
            key_bytes = self.signing_key
            key_b64 = base64.b64encode(key_bytes).decode('utf-8')
        else:
            try:
                key_bytes = base64.b64decode(key)
                key_b64 = parameters.get("key")
            except:
                raise ValueError("Invalid signing key format")
        
        # Create HMAC
        h = hmac.HMAC(key_bytes, hashes.SHA256(), backend=default_backend())
        h.update(data_bytes)
        signature = h.finalize()
        
        # Encode signature in base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        
        return {
            "signature": signature_b64,
            "key": key_b64
        }
    
    def _verify_signature(self, parameters: Dict[str, Any]) -> Dict[str, bool]:
        """Verify a signature using HMAC."""
        data = parameters.get("data", "")
        signature = parameters.get("signature", "")
        key = parameters.get("key", "")
        
        if not all([data, signature, key]):
            raise ValueError("Missing required parameters for signature verification")
            
        try:
            # Decode from base64
            data_bytes = data.encode('utf-8') if isinstance(data, str) else data
            signature_bytes = base64.b64decode(signature)
            key_bytes = base64.b64decode(key)
            
            # Create HMAC
            h = hmac.HMAC(key_bytes, hashes.SHA256(), backend=default_backend())
            h.update(data_bytes)
            
            # Verify the signature
            h.verify(signature_bytes)
            
            return {
                "verified": True
            }
        except Exception as e:
            return {
                "verified": False,
                "error": str(e)
            }
    
    def _generate_key(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Generate a cryptographic key."""
        key_type = parameters.get("type", "symmetric").lower()
        bits = int(parameters.get("bits", "256"))
        
        if key_type == "symmetric":
            if bits not in [128, 192, 256]:
                raise ValueError("Symmetric key bits must be 128, 192, or 256")
                
            # Generate random key
            key = secrets.token_bytes(bits // 8)
            key_b64 = base64.b64encode(key).decode('utf-8')
            
            return {
                "key": key_b64,
                "type": key_type,
                "bits": bits
            }
        else:
            # For demo, we only implement symmetric keys
            raise ValueError(f"Unsupported key type: {key_type}")
    
    def cleanup(self) -> None:
        """Cleanup resources used by this plugin."""
        logger.info(f"Cleaning up Cryptography Plugin for agent {self.agent_id}")
        # Securely clear sensitive data
        self.signing_key = None
