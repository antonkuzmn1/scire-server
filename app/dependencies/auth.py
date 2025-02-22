from fastapi import Depends, HTTPException, Header, status
from app.settings import settings
import httpx


async def verify_token(authorization: str = Header(default=None, description="Bearer token")) -> dict:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is required"
        )

    token = authorization.split(" ")[1]
    if not token:
        raise HTTPException(
            status_code=401,
            detail="Token not provided"
        )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{settings.OAUTH_CHECK_URL}/check",
                headers={"Authorization": f"Bearer {token}"},
                timeout=3.0
            )
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        raise HTTPException(401, detail=f"Auth service error: {e.response.text}")
    except httpx.RequestError as e:
        raise HTTPException(503, detail=f"Auth service unavailable: {str(e)}")
    except Exception as e:
        raise HTTPException(500, detail=f"Unexpected error: {str(e)}")

def require_roles(required_roles: list):
    def role_checker(user_data: dict = Depends(verify_token)):
        if user_data.get("role") not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user_data
    return Depends(role_checker)