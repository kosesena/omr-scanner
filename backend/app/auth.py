"""
Authentication module for OMR Scanner.
Verifies Supabase JWT tokens and extracts user_id.
"""

import os
import logging
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

SUPABASE_JWT_SECRET = os.environ.get("SUPABASE_JWT_SECRET", "")
USE_AUTH = bool(os.environ.get("SUPABASE_URL", ""))


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
        # Peek at the token header to see which algorithm is used
        header = jwt.get_unverified_header(token)
        alg = header.get("alg", "HS256")
        logger.info(f"JWT header alg: {alg}")

        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=[alg, "HS256", "HS384", "HS512"],
            options={"verify_aud": False},
        )
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Geçersiz token: user_id bulunamadı",
            )
        logger.info(f"Auth OK: user_id={user_id}")
        return user_id
    except jwt.ExpiredSignatureError:
        logger.warning("Token expired")
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
