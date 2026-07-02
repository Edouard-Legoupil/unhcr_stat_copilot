"""
Azure Entra ID Authentication for FastAPI.

This module provides authentication middleware for Azure App Service
with built-in Entra ID (formerly Azure AD) authentication.

When deployed on Azure App Service with Entra ID authentication enabled,
Azure handles the OAuth2 flow and injects user claims into request headers.
This module validates those headers and extracts user information.

Environment Variables:
- AZURE_AUTH_ENABLED: Set to 'true' to enable authentication (default: 'true')
- AZURE_AUTH_SKIP_PATHS: Comma-separated list of paths to skip authentication
- AZURE_ALLOWED_USERS: Comma-separated list of allowed user emails (optional)
- AZURE_ALLOWED_GROUPS: Comma-separated list of allowed group IDs (optional)
"""

import logging
import os
from typing import Callable, List, Optional

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security.utils import get_authorization_scheme_param

logger = logging.getLogger(__name__)


class UserInfo:
    """Container for authenticated user information."""
    
    def __init__(
        self,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
        name: Optional[str] = None,
        groups: Optional[List[str]] = None,
        is_authenticated: bool = False
    ):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.groups = groups or []
        self.is_authenticated = is_authenticated
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "groups": self.groups,
            "is_authenticated": self.is_authenticated
        }


def get_azure_config() -> dict:
    """Get Azure authentication configuration from environment."""
    return {
        "enabled": os.getenv("AZURE_AUTH_ENABLED", "true").lower() == "true",
        "skip_paths": os.getenv("AZURE_AUTH_SKIP_PATHS", "/health,/docs,/openapi.json").split(","),
        "allowed_users": os.getenv("AZURE_ALLOWED_USERS", "").split(",") if os.getenv("AZURE_ALLOWED_USERS") else None,
        "allowed_groups": os.getenv("AZURE_ALLOWED_GROUPS", "").split(",") if os.getenv("AZURE_ALLOWED_GROUPS") else None
    }


def extract_user_from_azure_headers(
    request: Request,
    x_ms_client_principal: Optional[str] = Header(None),
    x_ms_client_principal_id: Optional[str] = Header(None),
    x_ms_client_principal_name: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None)
) -> Optional[UserInfo]:
    """
    Extract user information from Azure App Service authentication headers.
    
    Azure App Service with Entra ID authentication injects these headers:
    - X-MS-Client-Principal: Base64-encoded JSON with user claims
    - X-MS-Client-Principal-Id: User ID
    - X-MS-Client-Principal-Name: User email or name
    - Authorization: Bearer token (if using token authentication)
    
    Args:
        request: FastAPI request object
        x_ms_client_principal: Base64-encoded user claims
        x_ms_client_principal_id: User ID
        x_ms_client_principal_name: User email/name
        authorization: Bearer token
        
    Returns:
        UserInfo object if authenticated, None otherwise
    """
    import base64
    import json
    
    config = get_azure_config()
    
    # Skip authentication for certain paths
    path = request.url.path
    if any(path.startswith(skip_path.strip()) for skip_path in config["skip_paths"]):
        return UserInfo(is_authenticated=False)
    
    # Try to extract user from headers
    user_info = UserInfo()
    
    # Method 1: X-MS-Client-Principal header (Azure App Service Easy Auth)
    if x_ms_client_principal:
        try:
            # Decode the base64-encoded JSON
            decoded = base64.b64decode(x_ms_client_principal + "==").decode("utf-8")
            claims = json.loads(decoded)
            
            user_info.user_id = claims.get("sub") or x_ms_client_principal_id
            user_info.email = claims.get("email") or claims.get("upn") or x_ms_client_principal_name
            user_info.name = claims.get("name") or user_info.email
            user_info.groups = claims.get("roles", []) or claims.get("groups", [])
            user_info.is_authenticated = True
            
            logger.debug(f"Authenticated user from Azure headers: {user_info.email}")
            return user_info
            
        except (ValueError, json.JSONDecodeError, AttributeError) as e:
            logger.warning(f"Failed to decode Azure client principal: {e}")
    
    # Method 2: Authorization header with Bearer token
    if authorization:
        scheme, token = get_authorization_scheme_param(authorization)
        if scheme.lower() == "bearer":
            # In production, validate the JWT token
            # For now, just check if token exists
            user_info.is_authenticated = True
            user_info.user_id = "token_user"
            logger.debug("Authenticated via Bearer token")
            return user_info
    
    # No valid authentication found
    return None


async def verify_azure_auth(
    request: Request,
    user_info: Optional[UserInfo] = Depends(extract_user_from_azure_headers)
) -> UserInfo:
    """
    FastAPI dependency that verifies Azure authentication.
    
    Args:
        request: FastAPI request object
        user_info: UserInfo from header extraction
        
    Returns:
        UserInfo object if authenticated
        
    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if authenticated but not authorized
    """
    config = get_azure_config()
    
    # If authentication is disabled, create a default user
    if not config["enabled"]:
        logger.debug("Azure authentication disabled")
        return UserInfo(
            user_id="anonymous",
            email="anonymous@unhcr.org",
            name="Anonymous User",
            is_authenticated=False
        )
    
    # Check if user is authenticated
    if user_info is None or not user_info.is_authenticated:
        logger.warning(f"Unauthorized access attempt to {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in via Azure Entra ID.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Check allowed users (if configured)
    if config["allowed_users"]:
        if user_info.email not in config["allowed_users"]:
            logger.warning(f"User {user_info.email} not in allowed users list")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource."
            )
    
    # Check allowed groups (if configured)
    if config["allowed_groups"]:
        user_groups = user_info.groups or []
        if not any(group in config["allowed_groups"] for group in user_groups):
            logger.warning(f"User {user_info.email} not in allowed groups")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to access this resource."
            )
    
    return user_info


async def get_optional_user(
    request: Request,
    user_info: Optional[UserInfo] = Depends(extract_user_from_azure_headers)
) -> UserInfo:
    """
    FastAPI dependency that returns user info if authenticated, or anonymous user.
    
    Use this for endpoints that work for both authenticated and anonymous users.
    
    Args:
        request: FastAPI request object
        user_info: UserInfo from header extraction
        
    Returns:
        UserInfo object (may be anonymous)
    """
    config = get_azure_config()
    
    # If authentication is disabled
    if not config["enabled"]:
        return UserInfo(
            user_id="anonymous",
            email="anonymous@unhcr.org",
            name="Anonymous User",
            is_authenticated=False
        )
    
    # Return authenticated user or anonymous
    if user_info and user_info.is_authenticated:
        return user_info
    
    return UserInfo(
        user_id="anonymous",
        email="anonymous@unhcr.org",
        name="Anonymous User",
        is_authenticated=False
    )


def create_auth_dependency(
    require_auth: bool = True,
    allowed_users: Optional[List[str]] = None,
    allowed_groups: Optional[List[str]] = None
) -> Callable:
    """
    Factory function to create custom authentication dependencies.
    
    Args:
        require_auth: Whether authentication is required
        allowed_users: List of allowed user emails
        allowed_groups: List of allowed group IDs
        
    Returns:
        FastAPI dependency function
    """
    async def dependency(
        request: Request,
        user_info: Optional[UserInfo] = Depends(extract_user_from_azure_headers)
    ) -> UserInfo:
        config = get_azure_config()
        
        # If authentication is disabled globally
        if not config["enabled"]:
            if require_auth:
                # Still require auth even if globally disabled
                if user_info is None or not user_info.is_authenticated:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Authentication required"
                    )
            return user_info or UserInfo(is_authenticated=False)
        
        # Check authentication
        if user_info is None or not user_info.is_authenticated:
            if require_auth:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required"
                )
            return UserInfo(is_authenticated=False)
        
        # Check user restrictions
        if allowed_users:
            if user_info.email not in allowed_users:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        # Check group restrictions
        if allowed_groups:
            user_groups = user_info.groups or []
            if not any(group in allowed_groups for group in user_groups):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access denied"
                )
        
        return user_info
    
    return dependency
