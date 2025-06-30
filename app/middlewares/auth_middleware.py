from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from app.services.auth_service import decode_token

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener usuario actual desde el token JWT"""
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

def role_required(required_roles: List[str]):
    """Decorator para verificar que el usuario tenga uno de los roles requeridos"""
    def role_checker(current_user: dict = Depends(get_current_user)):
        user_role = current_user.get("rol")
        
        if user_role not in required_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tiene permisos para acceder a este recurso"
            )
        
        return current_user
    
    return role_checker

def admin_required(current_user: dict = Depends(get_current_user)):
    """Verificar que el usuario sea admin"""
    if current_user.get("rol") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador"
        )
    return current_user

def admin_or_operador_required(current_user: dict = Depends(get_current_user)):
    """Verificar que el usuario sea admin u operador"""
    user_role = current_user.get("rol")
    if user_role not in ["admin", "operador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador u operador"
        )
    return current_user