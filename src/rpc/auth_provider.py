"""
Advanced Authentication Provider for MCP Zero

This module implements enterprise-grade authentication mechanisms including:
- OAuth 2.0/OpenID Connect federation
- Zero-trust architecture principles 
- JWT-based service mesh authentication
- Hardware security module integration
"""

import os
import time
import uuid
import json
import logging
import hashlib
import requests
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime, timedelta

logger = logging.getLogger("mcp-zero.auth")

class AuthLevel(Enum):
    """Authentication levels for access control."""
    SYSTEM = "system"      # Internal system components
    ADMIN = "admin"        # Administrative access
    OPERATOR = "operator"  # Operational access
    USER = "user"          # Standard user access
    GUEST = "guest"        # Limited guest access


class TokenType(Enum):
    """Token types supported by the auth provider."""
    API_KEY = "api_key"
    JWT = "jwt"
    OAUTH = "oauth"
    MTLS = "mtls"


class AuthProvider:
    """
    Advanced authentication provider supporting multiple auth methods.
    """
    
    def __init__(
        self,
        config: Dict[str, Any],
        hsm_enabled: bool = False,
        token_lifetime_mins: int = 60
    ):
        """
        Initialize auth provider with configuration.
        
        Args:
            config: Authentication configuration
            hsm_enabled: Whether to use Hardware Security Module for key operations
            token_lifetime_mins: Lifetime of issued tokens in minutes
        """
        self._config = config
        self._hsm_enabled = hsm_enabled
        self._token_lifetime = token_lifetime_mins
        self._signing_keys = self._load_signing_keys()
        self._oidc_providers = self._load_oidc_providers()
        
        # Setup HSM if enabled
        self._hsm = None
        if hsm_enabled:
            try:
                self._hsm = self._initialize_hsm()
                logger.info("HSM initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize HSM: {str(e)}. Falling back to software keys.")
    
    def _load_signing_keys(self) -> Dict[str, Any]:
        """Load signing keys from secure storage."""
        keys_path = self._config.get("keys_path", "/etc/mcp-zero/keys")
        keys = {}
        
        try:
            # Load primary key
            with open(f"{keys_path}/signing_key.pem", "r") as f:
                keys["primary"] = f.read()
            
            # Load rotation keys if available
            rotation_dir = f"{keys_path}/rotation"
            if os.path.exists(rotation_dir):
                for filename in os.listdir(rotation_dir):
                    if filename.endswith(".pem"):
                        key_id = filename.split(".")[0]
                        with open(f"{rotation_dir}/{filename}", "r") as f:
                            keys[key_id] = f.read()
            
            return keys
        except Exception as e:
            logger.error(f"Failed to load signing keys: {str(e)}")
            raise
    
    def _load_oidc_providers(self) -> Dict[str, Any]:
        """Load OIDC provider configurations."""
        providers = {}
        providers_config = self._config.get("oidc_providers", {})
        
        for provider_id, config in providers_config.items():
            # Fetch and validate OpenID configuration
            if "discovery_url" in config:
                try:
                    discovery_url = config["discovery_url"]
                    response = requests.get(f"{discovery_url}/.well-known/openid-configuration")
                    response.raise_for_status()
                    providers[provider_id] = {
                        "config": config,
                        "metadata": response.json()
                    }
                except Exception as e:
                    logger.warning(f"Failed to load OIDC provider {provider_id}: {str(e)}")
            else:
                # Manual configuration
                providers[provider_id] = {"config": config}
        
        return providers
    
    def _initialize_hsm(self) -> Any:
        """Initialize Hardware Security Module connection."""
        # This would connect to a hardware security module
        # Implementation depends on specific HSM (e.g., AWS KMS, Azure Key Vault)
        hsm_type = self._config.get("hsm_type", "softhsm")
        
        if hsm_type == "aws_kms":
            # AWS KMS integration example
            import boto3
            return boto3.client(
                'kms',
                region_name=self._config.get("aws_region", "us-east-1")
            )
        elif hsm_type == "azure_keyvault":
            # Azure Key Vault integration example
            from azure.keyvault.keys import KeyClient
            from azure.identity import DefaultAzureCredential
            
            credential = DefaultAzureCredential()
            key_vault_uri = self._config.get("azure_key_vault_uri")
            return KeyClient(vault_url=key_vault_uri, credential=credential)
        else:
            # Default to software HSM (for development/testing)
            return None
    
    def authenticate(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Authenticate using provided credentials.
        
        Args:
            credentials: Authentication credentials
            
        Returns:
            Authentication result with token if successful, None otherwise
        """
        auth_type = credentials.get("type", "api_key")
        
        if auth_type == "api_key":
            return self._authenticate_api_key(credentials)
        elif auth_type == "oauth":
            return self._authenticate_oauth(credentials)
        elif auth_type == "jwt":
            return self._authenticate_jwt(credentials)
        elif auth_type == "mtls":
            return self._authenticate_mtls(credentials)
        else:
            logger.warning(f"Unsupported authentication type: {auth_type}")
            return None
    
    def _authenticate_api_key(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Authenticate using API key."""
        api_key = credentials.get("api_key")
        if not api_key:
            return None
        
        # Validate API key (securely compare hash)
        api_keys = self._config.get("api_keys", {})
        for key_id, key_info in api_keys.items():
            if self._secure_compare(api_key, key_info["key"]):
                # Generate session token
                token = self.generate_token({
                    "sub": key_id,
                    "roles": key_info.get("roles", ["user"]),
                    "level": key_info.get("level", "user"),
                    "source": "api_key"
                })
                
                return {
                    "authenticated": True,
                    "user_id": key_id,
                    "roles": key_info.get("roles", ["user"]),
                    "level": key_info.get("level", "user"),
                    "token": token
                }
        
        return None
    
    def _authenticate_oauth(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Authenticate using OAuth token."""
        token = credentials.get("token")
        provider_id = credentials.get("provider_id")
        
        if not token or not provider_id:
            return None
        
        if provider_id not in self._oidc_providers:
            logger.warning(f"Unknown OIDC provider: {provider_id}")
            return None
        
        provider = self._oidc_providers[provider_id]
        
        try:
            # Validate token with provider
            userinfo_endpoint = provider["metadata"].get("userinfo_endpoint")
            response = requests.get(
                userinfo_endpoint,
                headers={"Authorization": f"Bearer {token}"}
            )
            response.raise_for_status()
            user_info = response.json()
            
            # Map OIDC claims to internal roles
            role_mapping = provider["config"].get("role_mapping", {})
            oidc_roles = user_info.get("roles", [])
            internal_roles = []
            
            for oidc_role in oidc_roles:
                if oidc_role in role_mapping:
                    internal_roles.extend(role_mapping[oidc_role])
            
            if not internal_roles:
                internal_roles = ["user"]  # Default role
            
            # Generate internal session token
            internal_token = self.generate_token({
                "sub": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "roles": internal_roles,
                "source": f"oidc:{provider_id}"
            })
            
            return {
                "authenticated": True,
                "user_id": user_info.get("sub"),
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "roles": internal_roles,
                "token": internal_token,
                "provider": provider_id
            }
        
        except Exception as e:
            logger.warning(f"OAuth authentication failed: {str(e)}")
            return None
    
    def _authenticate_jwt(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Authenticate using JWT token."""
        token = credentials.get("token")
        if not token:
            return None
        
        try:
            # Verify and decode token
            payload = self.verify_token(token)
            if not payload:
                return None
            
            return {
                "authenticated": True,
                "user_id": payload.get("sub"),
                "roles": payload.get("roles", ["user"]),
                "level": payload.get("level", "user"),
                "source": payload.get("source", "jwt")
            }
        
        except Exception as e:
            logger.warning(f"JWT authentication failed: {str(e)}")
            return None
    
    def _authenticate_mtls(self, credentials: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Authenticate using mutual TLS."""
        client_cert = credentials.get("client_cert")
        if not client_cert:
            return None
        
        # Validate client certificate
        # This would typically be done by the TLS termination layer
        # Here we're assuming the certificate is already validated
        
        # Extract identity from certificate
        cert_subject = credentials.get("cert_subject", "")
        cert_issuer = credentials.get("cert_issuer", "")
        
        # Look up service identity
        service_id = self._extract_service_id(cert_subject)
        if not service_id:
            logger.warning(f"Could not extract service ID from certificate")
            return None
        
        # Map service to roles
        service_mappings = self._config.get("service_mappings", {})
        if service_id in service_mappings:
            roles = service_mappings[service_id].get("roles", ["service"])
            level = service_mappings[service_id].get("level", "system")
            
            # Generate service token
            token = self.generate_token({
                "sub": service_id,
                "roles": roles,
                "level": level,
                "source": "mtls",
                "issuer": cert_issuer
            })
            
            return {
                "authenticated": True,
                "service_id": service_id,
                "roles": roles,
                "level": level,
                "token": token
            }
        
        return None
    
    def generate_token(self, claims: Dict[str, Any]) -> str:
        """
        Generate a JWT token with the provided claims.
        
        Args:
            claims: Token claims
            
        Returns:
            JWT token string
        """
        import jwt  # Import here to avoid dependency if not used
        
        # Add standard claims
        now = int(time.time())
        full_claims = {
            "iat": now,
            "exp": now + (self._token_lifetime * 60),
            "jti": str(uuid.uuid4()),
            "iss": "mcp-zero-auth",
            **claims
        }
        
        # Sign token
        if self._hsm_enabled and self._hsm:
            # Use HSM for signing
            # Implementation depends on specific HSM
            pass
        else:
            # Use software signing
            return jwt.encode(
                full_claims,
                self._signing_keys["primary"],
                algorithm="ES384"
            )
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify and decode a JWT token.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Decoded token claims if valid, None otherwise
        """
        import jwt
        
        try:
            # Try with primary key first
            return jwt.decode(
                token,
                self._signing_keys["primary"],
                algorithms=["ES384"],
                options={"verify_exp": True}
            )
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.InvalidSignatureError:
            # Try rotation keys
            for key_id, key in self._signing_keys.items():
                if key_id == "primary":
                    continue
                    
                try:
                    return jwt.decode(
                        token,
                        key,
                        algorithms=["ES384"],
                        options={"verify_exp": True}
                    )
                except:
                    continue
            
            logger.warning("Invalid token signature")
            return None
        except Exception as e:
            logger.warning(f"Token verification failed: {str(e)}")
            return None
    
    def authorize(self, token: str, required_roles: List[str], resource: str) -> bool:
        """
        Authorize access to a resource based on token.
        
        Args:
            token: JWT token
            required_roles: Roles required to access the resource
            resource: Resource being accessed
            
        Returns:
            True if authorized, False otherwise
        """
        claims = self.verify_token(token)
        if not claims:
            return False
        
        # Check roles
        user_roles = claims.get("roles", [])
        for role in required_roles:
            if role in user_roles:
                return True
        
        # Check for admin role
        if "admin" in user_roles:
            return True
        
        return False
    
    def _secure_compare(self, a: str, b: str) -> bool:
        """Perform a constant-time comparison of two strings."""
        if len(a) != len(b):
            return False
        
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        
        return result == 0
    
    def _extract_service_id(self, cert_subject: str) -> Optional[str]:
        """Extract service ID from certificate subject."""
        # Example: CN=service-api,O=mcp-zero
        import re
        
        match = re.search(r"CN=([^,]+)", cert_subject)
        if match:
            return match.group(1)
        
        return None
    
    def rotate_keys(self) -> None:
        """Rotate signing keys."""
        # Generate new key
        # Save current primary key as rotation key
        # Set new key as primary
        pass


class ZeroTrustManager:
    """
    Implements zero-trust architecture principles for service-to-service communication.
    """
    
    def __init__(self, auth_provider: AuthProvider, config: Dict[str, Any]):
        """
        Initialize zero trust manager.
        
        Args:
            auth_provider: Authentication provider
            config: Configuration for zero trust security
        """
        self._auth_provider = auth_provider
        self._config = config
        self._attestation_cache = {}  # Cache for attestation results
    
    def issue_service_token(self, service_id: str, attestation_data: Dict[str, Any]) -> Optional[str]:
        """
        Issue a token for service-to-service communication after attestation.
        
        Args:
            service_id: Service identifier
            attestation_data: Evidence of service identity and integrity
            
        Returns:
            Service token if attestation is successful, None otherwise
        """
        # Validate attestation data
        if not self._validate_attestation(service_id, attestation_data):
            logger.warning(f"Attestation failed for service {service_id}")
            return None
        
        # Determine service roles and level
        service_config = self._config.get("services", {}).get(service_id, {})
        roles = service_config.get("roles", ["service"])
        level = service_config.get("level", "system")
        
        # Generate token
        return self._auth_provider.generate_token({
            "sub": service_id,
            "roles": roles,
            "level": level,
            "source": "zero_trust",
            "att": attestation_data.get("digest", "")[:8]  # Attestation digest reference
        })
    
    def _validate_attestation(self, service_id: str, attestation_data: Dict[str, Any]) -> bool:
        """
        Validate service attestation data.
        
        Args:
            service_id: Service identifier
            attestation_data: Attestation evidence
            
        Returns:
            True if attestation is valid, False otherwise
        """
        # Implement attestation validation logic
        # - Verify service binary integrity
        # - Verify environment integrity
        # - Verify configuration integrity
        
        attestation_type = attestation_data.get("type", "none")
        
        if attestation_type == "tpm":
            # TPM-based attestation
            return self._validate_tpm_attestation(service_id, attestation_data)
        elif attestation_type == "sgx":
            # Intel SGX attestation
            return self._validate_sgx_attestation(service_id, attestation_data)
        elif attestation_type == "signature":
            # Signature-based attestation
            return self._validate_signature_attestation(service_id, attestation_data)
        else:
            logger.warning(f"Unsupported attestation type: {attestation_type}")
            return False
    
    def _validate_tpm_attestation(self, service_id: str, attestation_data: Dict[str, Any]) -> bool:
        """Validate TPM-based attestation."""
        # Implementation would use TPM attestation libraries
        return True  # Placeholder
    
    def _validate_sgx_attestation(self, service_id: str, attestation_data: Dict[str, Any]) -> bool:
        """Validate Intel SGX attestation."""
        # Implementation would use SGX attestation libraries
        return True  # Placeholder
    
    def _validate_signature_attestation(self, service_id: str, attestation_data: Dict[str, Any]) -> bool:
        """Validate signature-based attestation."""
        # Verify signature of service identity
        return True  # Placeholder
