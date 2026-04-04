"""
Authentication module for OMR Scanner.
Verifies Supabase JWT tokens and extracts user_id.
Uses JWKS endpoint for RS256 tokens, falls back to HS256 with legacy secret.
"""

import os
import logging
import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
USE_AUTH = bool(SUPABASE_URL)

# JWKS client for RS256 token verification
_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None and SUPABASE_URL:
        jwks_url = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
        logger.info(f"JWKS client initialized: {jwks_url}")
    return _jwks_client


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """Extract user_id from Supabase JWT token."""
    if not USE_AUTH:
        return "dev-user"

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmanız gerekiyor",
        )

    token = credentials.credentials
    try:
        # Check token header algorithm
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        logger.info(f"JWT alg: {alg}")

        if alg.startswith("RS") or alg.startswith("ES"):
            # Asymmetric algorithm — use JWKS public key
            jwks_client = _get_jwks_client()
            if not jwks_client:
                raise jwt.InvalidTokenError("JWKS client not available")
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=[alg],
                options={"verify_aud": False},
            )
        else:
            # Symmetric algorithm (HS256) — use legacy JWT secret
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )

        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token",
            )
        logger.info(f"Auth OK: user_id={user_id}")
        return user_id

    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Oturum süresi doldu, tekrar giriş yapın",
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT error: {type(e).__name__}: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Geçersiz token: {type(e).__name__}",
        )
