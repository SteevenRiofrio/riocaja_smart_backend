from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.auth_service import decode_token
from jose import JWTError, ExpiredSignatureError

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = decode_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido",
            headers={"WWW-Authenticate": "Bearer"}
        )

def role_required(required_roles: list):
    """Decorador para verificar si el usuario tiene el rol requerido"""
    async def wrapper(user=Depends(get_current_user)):
        if user.get("rol") not in required_roles:
            raise HTTPException(status_code=403, detail="No tienes permisos")
        return user
    return wrapper