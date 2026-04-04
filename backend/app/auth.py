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
    """Extract user_id from Supabase JWT token.
    In dev mode (no Supabase), returns a fixed dev user.
    """
    if not USE_AUTH:
        return "dev-user"

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Giriş yapmanız gerekiyor",
        )

    token = credentials.credentials
    try:
        # First try with audience check
        payload = jwt.decode(
            token,
            SUPABASE_JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
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
    except jwt.InvalidAudienceError:
        # Try without audience check (some Supabase versions don't set aud)
        try:
            payload = jwt.decode(
                token,
                SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
            user_id = payload.get("sub")
            if user_id:
                logger.info(f"Auth OK (no aud): user_id={user_id}")
                return user_id
        except Exception as e2:
            logger.error(f"Auth fallback failed: {e2}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Geçersiz token",
        )
    except jwt.InvalidTokenError as e:
        logger.error(f"JWT error: {type(e).__name__}: {e}")
        logger.error(f"JWT secret length: {len(SUPABASE_JWT_SECRET)}, starts with: {SUPABASE_JWT_SECRET[:10]}...")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Geçersiz token: {type(e).__name__}",
        )
