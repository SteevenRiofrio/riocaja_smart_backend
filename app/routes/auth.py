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
    rol: Optional[str] = "lector"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

user_service = UserService()

@router.post("/register")
def register(user: UserRegister):
    try:
        return user_service.register_user(
            nombre=user.nombre,
            email=user.email,
            password=user.password,
            rol=user.rol
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"Error en registro: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/login")
def login(user: UserLogin):
    try:
        user_db = user_service.authenticate_user(user.email, user.password)
        if not user_db:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")

        # NUEVO: Verificar estado del usuario
        user_state = user_db.get("estado", "pendiente")
        
        if user_state != "activo":
            # Devolver mensaje específico según el estado
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

        token_data = {
            "sub": user_db["_id"],
            "email": user_db["email"],
            "rol": user_db["rol"],
            "estado": user_state,  # NUEVO: Incluir estado en el token
            "perfil_completo": user_db.get("perfil_completo", False)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Enviar email de notificacion de login
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            email_service.send_login_notification(
                user_email=user_db['email'],
                user_name=user_db['nombre'],
                login_info={
                    'rol': user_db['rol'],
                    'email': user_db['email']
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
        user_data = user_service.get_user_info(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return {
            "success": True,
            "data": {
                "_id": user_data["_id"],
                "nombre": user_data["nombre"],
                "email": user_data["email"],
                "rol": user_data["rol"],
                "estado": user_data.get("estado", "pendiente"),
                "perfil_completo": user_data.get("perfil_completo", False),
                "codigo_corresponsal": user_data.get("codigo_corresponsal"),
                "nombre_local": user_data.get("nombre_local"),
                "fecha_registro": user_data.get("fecha_registro").isoformat() if user_data.get("fecha_registro") else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en /me: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/complete-profile")
async def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    user_id = user.get("sub")
    
    try:
        current_user = user_service.get_user_info(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        if current_user.get("estado") != "activo":
            raise HTTPException(status_code=400, detail="Su cuenta aún no ha sido aprobada")
        
        if not current_user.get("codigo_corresponsal"):
            raise HTTPException(status_code=400, detail="No tiene un código de corresponsal asignado")
        
        codigo_asignado = current_user.get("codigo_corresponsal")
        codigo_enviado = profile.codigo_corresponsal
        
        if codigo_asignado != codigo_enviado:
            raise HTTPException(
                status_code=400, 
                detail=f"El código proporcionado no coincide con el asignado"
            )
        
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
        print(f"Error en complete-profile: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/pending-users", response_model=List[dict])
async def get_pending_users(user=Depends(role_required(["admin", "operador"]))):
    try:
        return user_service.get_pending_users()
    except Exception as e:
        print(f"Error en pending-users: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/all-users", response_model=List[dict])
async def get_all_users(user=Depends(role_required(["admin", "operador"]))):
    try:
        return user_service.get_all_users()
    except Exception as e:
        print(f"Error en all-users: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/approve-user")
async def approve_user_with_code(
    approval: UserApprovalWithCode, 
    current_user=Depends(role_required(["admin", "operador"]))
):
    try:
        success = user_service.approve_user_with_code(
            user_id=approval.user_id,
            codigo_corresponsal=approval.codigo_corresponsal,
            approved_by=current_user.get("sub")
        )
        
        if success:
            # NUEVO: Enviar email de bienvenida al usuario aprobado
            try:
                user_info = user_service.get_user_info(approval.user_id)
                if user_info:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    email_service.send_welcome_email(
                        user_email=user_info['email'],
                        user_name=user_info['nombre']
                    )
                    logger.info(f"Email de bienvenida enviado a: {user_info['email']}")
            except Exception as email_error:
                logger.warning(f"No se pudo enviar email de bienvenida: {email_error}")
            
            return {"message": "Usuario aprobado exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al aprobar usuario")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en approve-user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/create-admin")
def create_admin(admin_data: dict, current_user=Depends(role_required(["admin"]))):
    """Crear usuario admin directamente (solo admins pueden crear otros admins)"""
    try:
        result = user_service.create_admin_user(admin_data)
        return {"message": "Admin creado exitosamente", "user_id": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-first-admin")
def setup_first_admin(admin_data: dict):
    """Crear primer admin del sistema (solo si no hay admins)"""
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
    """Convertir usuario existente en admin (solo para setup inicial)"""
    try:
        email = request.get("email")
        secret = request.get("secret_key")
        
        if secret != "riocaja_admin_2025":
            raise HTTPException(status_code=403, detail="Clave secreta incorrecta")
        
        user = user_service.users.find_one({"email": email})
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        success = user_service.make_user_admin(email)
        if success:
            return {"message": f"Usuario {email} convertido a ADMIN exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="No se pudo actualizar el usuario")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/refresh")
def refresh_token(request: dict):
    """Renovar access token usando refresh token"""
    try:
        refresh_token_str = request.get("refresh_token")
        if not refresh_token_str:
            raise HTTPException(status_code=400, detail="Refresh token requerido")
        
        new_access_token = refresh_access_token(refresh_token_str)
        if not new_access_token:
            raise HTTPException(status_code=401, detail="Refresh token inválido o expirado")
        
        return {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Error renovando token")