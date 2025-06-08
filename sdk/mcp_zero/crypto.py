"""
MCP-ZERO SDK: Cryptography Module

This module provides cryptographic functions for ensuring the integrity
and security of MCP-ZERO operations, including signing, verification,
and encryption services.
"""

import os
import json
import time
import base64
import logging
import hashlib
from typing import Dict, Any, Union, Optional
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.backends import default_backend
from cryptography.exceptions import InvalidSignature

from .exceptions import CryptographicError

# Configure logging
logger = logging.getLogger("mcp_zero")

# Constants
KEY_DIR = os.path.expanduser("~/.mcp_zero/keys")
AGENT_KEYS_DIR = os.path.join(KEY_DIR, "agents")
DEFAULT_KEY_SIZE = 2048


def ensure_key_dirs() -> None:
    """Ensure key directories exist"""
    os.makedirs(KEY_DIR, exist_ok=True)
    os.makedirs(AGENT_KEYS_DIR, exist_ok=True)


def generate_key_pair(agent_id: Optional[str] = None) -> tuple:
    """
    Generate a new RSA key pair.
    
    Args:
        agent_id: Optional agent ID to associate with the keys
        
    Returns:
        Tuple of (private_key, public_key) objects
    """
    try:
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=DEFAULT_KEY_SIZE,
            backend=default_backend()
        )
        
        # Derive public key
        public_key = private_key.public_key()
        
        # If agent_id provided, save keys to disk
        if agent_id:
            ensure_key_dirs()
            agent_key_dir = os.path.join(AGENT_KEYS_DIR, agent_id)
            os.makedirs(agent_key_dir, exist_ok=True)
            
            # Save private key
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            with open(os.path.join(agent_key_dir, "private.pem"), "wb") as f:
                f.write(private_pem)
            
            # Save public key
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            with open(os.path.join(agent_key_dir, "public.pem"), "wb") as f:
                f.write(public_pem)
            
            logger.debug(f"Generated and saved key pair for agent {agent_id}")
        
        return private_key, public_key
    
    except Exception as e:
        logger.error(f"Failed to generate key pair: {str(e)}")
        raise CryptographicError(f"Failed to generate key pair: {str(e)}") from e


def load_agent_keys(agent_id: str) -> Optional[tuple]:
    """
    Load existing keys for an agent.
    
    Args:
        agent_id: Agent ID to load keys for
        
    Returns:
        Tuple of (private_key, public_key) objects or None if not found
    """
    agent_key_dir = os.path.join(AGENT_KEYS_DIR, agent_id)
    private_key_path = os.path.join(agent_key_dir, "private.pem")
    public_key_path = os.path.join(agent_key_dir, "public.pem")
    
    if not (os.path.exists(private_key_path) and os.path.exists(public_key_path)):
        return None
    
    try:
        # Load private key
        with open(private_key_path, "rb") as f:
            private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        # Load public key
        with open(public_key_path, "rb") as f:
            public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        
        return private_key, public_key
    
    except Exception as e:
        logger.error(f"Failed to load keys for agent {agent_id}: {str(e)}")
        return None


def sign_operation(operation_type: str, payload: Dict[str, Any]) -> str:
    """
    Sign an operation with the agent's private key.
    
    Args:
        operation_type: Type of operation being signed
        payload: The payload to sign
        
    Returns:
        Base64-encoded signature
    """
    try:
        # Get agent_id from payload
        agent_id = payload.get("agent_id") or payload.get("id")
        if not agent_id:
            raise CryptographicError("No agent_id found in payload")
        
        # Load or generate keys
        keys = load_agent_keys(agent_id)
        if not keys:
            keys = generate_key_pair(agent_id)
        
        private_key, _ = keys
        
        # Create signature payload
        signature_payload = {
            "operation": operation_type,
            "timestamp": time.time(),
            "data": payload
        }
        
        # Serialize and hash the payload
        serialized = json.dumps(signature_payload, sort_keys=True).encode('utf-8')
        digest = hashlib.sha256(serialized).digest()
        
        # Create signature
        signature = private_key.sign(
            digest,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Encode the signature
        encoded_signature = base64.b64encode(signature).decode('utf-8')
        
        return encoded_signature
    
    except Exception as e:
        logger.error(f"Failed to sign operation: {str(e)}")
        raise CryptographicError(f"Failed to sign operation: {str(e)}") from e


def verify_signature(operation_type: str, payload: Dict[str, Any]) -> bool:
    """
    Verify the signature of an operation.
    
    Args:
        operation_type: Type of operation being verified
        payload: The payload with signature to verify
        
    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Extract signature from payload
        signature = payload.pop("signature", None)
        if not signature:
            logger.warning("No signature found in payload")
            return False
        
        # Get agent_id
        agent_id = payload.get("agent_id") or payload.get("id")
        if not agent_id:
            logger.warning("No agent_id found in payload")
            return False
        
        # Load keys
        keys = load_agent_keys(agent_id)
        if not keys:
            logger.warning(f"No keys found for agent {agent_id}")
            return False
        
        _, public_key = keys
        
        # Create verification payload
        verification_payload = {
            "operation": operation_type,
            "timestamp": payload.get("timestamp", 0),
            "data": payload
        }
        
        # Serialize and hash the payload
        serialized = json.dumps(verification_payload, sort_keys=True).encode('utf-8')
        digest = hashlib.sha256(serialized).digest()
        
        # Verify the signature
        try:
            decoded_signature = base64.b64decode(signature)
            
            public_key.verify(
                decoded_signature,
                digest,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            
            return True
            
        except InvalidSignature:
            logger.warning("Invalid signature detected")
            return False
    
    except Exception as e:
        logger.error(f"Failed to verify signature: {str(e)}")
        return False


def hash_data(data: Union[str, bytes, Dict[str, Any]]) -> str:
    """
    Create a hash of the provided data.
    
    Args:
        data: The data to hash (string, bytes or dict)
        
    Returns:
        Hex string of the hash
    """
    try:
        if isinstance(data, dict):
            data = json.dumps(data, sort_keys=True).encode('utf-8')
        elif isinstance(data, str):
            data = data.encode('utf-8')
        
        return hashlib.sha256(data).hexdigest()
        
    except Exception as e:
        logger.error(f"Failed to hash data: {str(e)}")
        raise CryptographicError(f"Failed to hash data: {str(e)}") from e


def encrypt_data(data: Union[str, bytes], public_key=None) -> str:
    """
    Encrypt data using the provided public key or agent public key.
    
    Args:
        data: The data to encrypt
        public_key: Optional public key to use
        
    Returns:
        Base64-encoded encrypted data
    """
    try:
        if isinstance(data, str):
            data = data.encode('utf-8')
        
        # If no public key provided, use a new one
        if not public_key:
            _, public_key = generate_key_pair()
        
        # Encrypt data
        encrypted = public_key.encrypt(
            data,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        # Encode the encrypted data
        encoded = base64.b64encode(encrypted).decode('utf-8')
        
        return encoded
        
    except Exception as e:
        logger.error(f"Failed to encrypt data: {str(e)}")
        raise CryptographicError(f"Failed to encrypt data: {str(e)}") from e


def decrypt_data(encrypted_data: str, private_key) -> bytes:
    """
    Decrypt data using the provided private key.
    
    Args:
        encrypted_data: Base64-encoded encrypted data
        private_key: Private key to use for decryption
        
    Returns:
        Decrypted data as bytes
    """
    try:
        # Decode the encrypted data
        decoded = base64.b64decode(encrypted_data)
        
        # Decrypt data
        decrypted = private_key.decrypt(
            decoded,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        return decrypted
        
    except Exception as e:
        logger.error(f"Failed to decrypt data: {str(e)}")
        raise CryptographicError(f"Failed to decrypt data: {str(e)}") from e
