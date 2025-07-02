# app/routes/auth.py - VERSIÓN COMPLETA CON EMAIL DE LOGIN
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user, role_required
from app.models.user import UserProfile, UserApprovalWithCode
from app.services.auth_service import refresh_access_token, create_refresh_token
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class UserRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: Optional[str] = "cnb"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class ChangeUserStateRequest(BaseModel):
    user_id: str
    state: str
    reason: Optional[str] = None

class DeleteUserRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None

class RejectUserRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None

user_service = UserService()

@router.post("/register")
def register(user: UserRegister):
    """Registro de usuario CON notificaciones automáticas"""
    try:
        # El register_user ahora envía emails automáticamente
        return user_service.register_user(
            nombre=user.nombre,
            email=user.email,
            password=user.password,
            rol=user.rol
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error en registro: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/login")
def login(user: UserLogin):
    """Login CON notificación de seguridad"""
    try:
        user_db = user_service.authenticate_user(user.email, user.password)
        if not user_db:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")

        # Verificar estado del usuario
        user_state = user_db.get("estado", "pendiente")
        
        if user_state != "activo":
            state_messages = {
                "pendiente": "Su cuenta está pendiente de aprobación. Contacte al administrador.",
                "suspendido": "Su cuenta ha sido suspendida. Contacte al administrador.", 
                "inactivo": "Su cuenta está inactiva. Contacte al administrador.",
                "rechazado": "Su cuenta ha sido rechazada. Contacte al administrador."
            }
            
            message = state_messages.get(user_state, f"Su cuenta está en estado {user_state}. Contacte al administrador.")
            
            raise HTTPException(
                status_code=403, 
                detail=message
            )

        # Crear tokens
        token_data = {
            "sub": user_db["_id"],
            "email": user_db["email"],
            "rol": user_db["rol"],
            "estado": user_state,
            "session_id": user_db["session_id"],
            "perfil_completo": user_db.get("perfil_completo", False)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # NUEVO: Enviar email de notificación de login
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            email_service.send_login_notification(
                user_email=user_db['email'],
                user_name=user_db['nombre'],
                login_info={
                    'rol': user_db['rol'],
                    'email': user_db['email'],
                    'session_id': user_db['session_id'][:8] + "..."
                }
            )
            logger.info(f"Email de login enviado a: {user_db['email']}")
        except Exception as email_error:
            logger.warning(f"No se pudo enviar email de login: {email_error}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "perfil_completo": user_db.get("perfil_completo", False),
            "codigo_corresponsal": user_db.get("codigo_corresponsal")
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión")

@router.get("/me")
def me(user=Depends(get_current_user)):
    try:
        user_id = user.get("sub")
        user_data = user_service.get_user_by_id(user_id)
        if user_data:
            user_data.pop("password_hash", None)
            return user_data
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en me: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/complete-profile")
def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    try:
        user_id = user.get("sub")
        
        success = user_service.complete_user_profile_simple(
            user_id=user_id,
            nombre_local=profile.nombre_local
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Error al completar perfil")
        
        return {"message": "Perfil completado correctamente"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en complete-profile: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.get("/pending-users", response_model=List[dict])
async def get_pending_users(user=Depends(role_required(["admin", "asesor"]))):
    try:
        return user_service.get_pending_users()
    except Exception as e:
        logger.error(f"Error en pending-users: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/all-users", response_model=List[dict])
async def get_all_users(user=Depends(role_required(["admin", "asesor"]))):
    try:
        return user_service.get_all_users()
    except Exception as e:
        logger.error(f"Error en all-users: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")



@router.post("/approve-user")
async def approve_user_with_code(
    approval: UserApprovalWithCode, 
    current_user=Depends(role_required(["admin", "asesor"]))
):
    """Aprobar usuario CON email automático"""
    try:
        # El approve_user_with_code ahora envía email automáticamente
        success = user_service.approve_user_with_code(
            user_id=approval.user_id,
            codigo_corresponsal=approval.codigo_corresponsal,
            approved_by=current_user.get("sub")
        )
        
        if success:
            return {"message": "Usuario aprobado exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al aprobar usuario")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en approve-user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/reject-user")
async def reject_user(
    request: RejectUserRequest,
    current_user=Depends(role_required(["admin", "asesor"]))
):
    """Rechazar usuario CON email automático"""
    try:
        # El reject_user ahora envía email automáticamente
        success = user_service.reject_user(
            user_id=request.user_id,
            reason=request.reason
        )
        
        if success:
            return {"message": "Usuario rechazado exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al rechazar usuario")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reject-user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/change-user-state")
async def change_user_state(
    request: ChangeUserStateRequest,
    current_user=Depends(role_required(["admin", "asesor"]))
):
    """Cambiar estado de usuario CON email automático"""
    try:
        # El change_user_state ahora envía email automáticamente
        success = user_service.change_user_state(
            user_id=request.user_id,
            new_state=request.state,
            reason=request.reason,
            changed_by=current_user.get("sub")
        )
        
        if success:
            return {"message": f"Estado cambiado a {request.state} exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al cambiar estado")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en change-user-state: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/delete-user")
async def delete_user(
    request: DeleteUserRequest,
    current_user=Depends(role_required(["admin"]))  # Solo admins pueden eliminar
):
    """Eliminar usuario CON email automático"""
    try:
        # El delete_user ahora envía email automáticamente
        success = user_service.delete_user(
            user_id=request.user_id,
            reason=request.reason,
            deleted_by=current_user.get("sub")
        )
        
        if success:
            return {"message": "Usuario eliminado exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al eliminar usuario")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en delete-user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/create-admin")
def create_admin(admin_data: dict, current_user=Depends(role_required(["admin"]))):
    """Crear usuario admin directamente"""
    try:
        result = user_service.create_admin_user(admin_data)
        return {"message": "Admin creado exitosamente", "user_id": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-first-admin")
def setup_first_admin(admin_data: dict):
    """Crear primer admin del sistema"""
    try:
        existing_admins = user_service.count_admins()
        if existing_admins > 0:
            raise HTTPException(status_code=400, detail="Ya existe un admin en el sistema")
        
        result = user_service.create_first_admin(admin_data)
        return {"message": "Primer admin creado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/make-me-admin")
def make_me_admin(request: dict):
    """Convertir usuario existente en admin"""
    try:
        email = request.get("email")
        secret_key = request.get("secret_key")
        
        if not email or not secret_key:
            raise HTTPException(status_code=400, detail="Email y clave secreta requeridos")
        
        success = user_service.make_user_admin(email, secret_key)
        if success:
            return {"message": "Usuario convertido a admin exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Credenciales inválidas o usuario no encontrado")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en make-me-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.post("/refresh")
def refresh_token(refresh_token: str):
    """Refrescar token de acceso"""
    try:
        new_token = refresh_access_token(refresh_token)
        if new_token:
            return {"access_token": new_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=401, detail="Token de refresh inválido")
    except Exception as e:
        logger.error(f"Error en refresh: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")


@router.put("/change-state")
async def change_user_state(
    request: ChangeUserStateRequest,
    current_user=Depends(role_required(["admin", "asesor"]))
):
    """Cambiar estado de un usuario (solo admin y asesor)"""
    try:
        # Validar estados permitidos
        valid_states = ["activo", "suspendido", "inactivo", "pendiente"]
        if request.state not in valid_states:
            raise HTTPException(
                status_code=400, 
                detail=f"Estado inválido. Estados permitidos: {valid_states}"
            )
        
        # Cambiar estado en la base de datos
        success = user_service.change_user_state(request.user_id, request.state)
        
        if success:
            admin_id = current_user.get("sub")
            logger.info(f"Admin {admin_id} cambió estado del usuario {request.user_id} a {request.state}")
            
            return {
                "success": True,
                "message": f"Estado del usuario cambiado a {request.state}"
            }
        else:
            raise HTTPException(
                status_code=404, 
                detail="Usuario no encontrado o no se pudo actualizar"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en change-state: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")