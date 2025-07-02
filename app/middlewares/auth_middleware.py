from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional, List
from app.services.auth_service import decode_token
import logging  # ← AÑADIR AQUÍ

logger = logging.getLogger(__name__)  # ← AÑADIR AQUÍ
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Obtener usuario actual desde el token JWT con validación de estado y sesión"""
    try:
        token = credentials.credentials
        payload = decode_token(token)
        
        if payload is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        user_id = payload.get("sub")
        token_session_id = payload.get("session_id")  # session_id del token
        
        if user_id:
            # CORREGIDO: Importar aquí para evitar import circular
            from app.services.user_service import UserService
            user_service = UserService()
            user_info = user_service.get_user_info(user_id)
            
            if user_info:
                user_state = user_info.get("estado", "pendiente")
                current_session_id = user_info.get("session_id")  # session_id actual en BD
                
                # CORREGIDO: Solo verificar session_id si ambos existen
                if (token_session_id and current_session_id and 
                    token_session_id != current_session_id):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Tu sesión fue cerrada porque iniciaste sesión en otro dispositivo.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # Verificar estado del usuario
                if user_state != "activo":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Cuenta {user_state}. Contacte al administrador.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                # Actualizar payload con datos frescos del usuario
                payload["estado"] = user_state
                payload["rol"] = user_info.get("rol", payload.get("rol"))
                payload["session_id"] = current_session_id
        
        return payload
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en get_current_user: {e}")
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

def admin_or_asesor_required(current_user: dict = Depends(get_current_user)):
    """Verificar que el usuario sea admin u asesor"""
    user_role = current_user.get("rol")
    if user_role not in ["admin", "asesor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Se requieren permisos de administrador u asesor"
        )
    return current_user