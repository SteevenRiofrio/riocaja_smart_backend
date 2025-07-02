import jwt
from datetime import datetime, timedelta
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
from app.config import SECRET_KEY, ALGORITHM
from app.services.user_service import UserService

security = HTTPBearer()
user_service = UserService()

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener el usuario actual desde el token"""
    token = credentials.credentials
    
    try:
        # Decodificar token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        current_session_id = payload.get("session_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validar usuario actual en BD
        user_info = user_service.get_user_by_id(user_id)
        if not user_info:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuario no encontrado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Verificar sesión activa si session_id está presente
        if current_session_id:
            db_session_id = user_info.get("session_id")
            if db_session_id and current_session_id != db_session_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Sesión cerrada por login en otro dispositivo",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        
        # Si no hay session_id en el token (tokens antiguos), validar solo estado
        user_state = user_info.get("estado", "inactivo")
        
        # Si el usuario está inactivo, mostrar mensaje específico
        if user_state == "inactivo":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Cuenta inactiva. Contacte al administrador.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Si el usuario está en cualquier otro estado que no sea activo
        if user_state != "activo":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Cuenta {user_state}. Contacte al administrador.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Actualizar payload con datos frescos del usuario
        payload["estado"] = user_state
        payload["rol"] = user_info.get("rol", payload.get("rol"))
        payload["session_id"] = current_session_id  # NUEVO: mantener session_id actualizado

        return payload
    except HTTPException:
        raise
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
    """Verificar que el usuario sea admin o operador (antes operador)"""
    user_role = current_user.get("rol")
    if user_role not in ["admin", "operador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador o operador"
        )
    return current_user