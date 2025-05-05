from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.services.auth_service import decode_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido o expirado")
    return payload

async def role_required(required_roles: list):
    async def wrapper(user=Depends(get_current_user)):
        if user.get("rol") not in required_roles:
            raise HTTPException(status_code=403, detail="No tienes permisos")
        return user
    return wrapper