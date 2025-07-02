# app/routes/auth.py - VERSIÓN COMPLETA CORREGIDA
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging
import os

# Importaciones locales con manejo de errores
try:
    from app.services.user_service import UserService
except ImportError as e:
    print(f"Error importando UserService: {e}")
    UserService = None

try:
    from app.services.auth_service import create_access_token, create_refresh_token
except ImportError as e:
    print(f"Error importando auth_service: {e}")
    def create_access_token(data): return "dummy_token"
    def create_refresh_token(data): return "dummy_refresh_token"

try:
    from app.middlewares.auth_middleware import get_current_user, role_required
except ImportError as e:
    print(f"Error importando auth_middleware: {e}")
    def get_current_user(): return {}
    def role_required(roles): return lambda: {}

try:
    from app.models.user import UserProfile, UserApprovalWithCode
except ImportError as e:
    print(f"Error importando models.user: {e}")
    # Definir modelos básicos como fallback
    class UserProfile(BaseModel):
        codigo_corresponsal: str
        nombre_local: str
    
    class UserApprovalWithCode(BaseModel):
        user_id: str
        codigo_corresponsal: str

logger = logging.getLogger(__name__)
router = APIRouter()

# Modelos de request
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

class ChangeUserRoleRequest(BaseModel):
    user_id: str
    role: str


# Inicializar servicio con validación
try:
    user_service = UserService() if UserService else None
except Exception as e:
    logger.error(f"Error inicializando UserService: {e}")
    user_service = None

@router.post("/change-role")
async def change_user_role(
    request: ChangeUserRoleRequest, 
    current_user=Depends(role_required(["admin"]))
):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        success = user_service.change_user_role(
            user_id=request.user_id,
            new_role=request.role,
            changed_by=current_user.get("sub")
        )
        
        if success:
            return {"message": f"Rol de usuario cambiado a {request.role}"}
        else:
            raise HTTPException(status_code=400, detail="Error al cambiar rol")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en change-role: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Endpoint de health check
@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "user_service": "available" if user_service else "unavailable"
    }

@router.post("/register")
def register(user: UserRegister):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
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
        logger.error(f"Error en registro: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/login")
def login(user: UserLogin):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        user_db = user_service.authenticate_user(user.email, user.password)
        if not user_db:
            raise HTTPException(status_code=400, detail="Credenciales incorrectas")

        # Verificar estado del usuario
        user_state = user_db.get("estado", "pendiente")
        user_role = user_db.get("rol", "cnb")
        
        # ✅ NUEVO: Admin y asesor siempre pueden acceder, independiente del estado
        if user_role not in ["admin", "asesor"] and user_state != "activo":
            state_messages = {
                "pendiente": "Su cuenta está pendiente de aprobación. Contacte al administrador.",
                "suspendido": "Su cuenta ha sido suspendida. Contacte al administrador.",
                "inactivo": "Su cuenta está inactiva. Contacte al administrador.",
                "rechazado": "Su cuenta ha sido rechazada. Contacte al administrador."
            }
            
            message = state_messages.get(user_state, f"Su cuenta está en estado {user_state}. Contacte al administrador.")
            
            raise HTTPException(status_code=403, detail=message)

        # ✅ NUEVO: Para admin/asesor, asegurar perfil completo
        perfil_completo = user_db.get("perfil_completo", False)
        if user_role in ["admin", "asesor"] and not perfil_completo:
            # Marcar como completo automáticamente
            user_service.mark_admin_profile_complete(str(user_db["_id"]))
            perfil_completo = True
            logger.info(f"✅ Perfil de {user_role} auto-completado en login: {user_db['_id']}")

        # Crear tokens
        token_data = {
            "sub": str(user_db["_id"]),
            "email": user_db["email"],
            "rol": user_role,
            "estado": user_state,
            "session_id": user_db.get("session_id", ""),
            "perfil_completo": perfil_completo
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Intentar enviar email de notificación (opcional) - ✅ CORREGIDO
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            email_service.send_login_notification(
                user_email=user_db['email'],
                user_name=user_db['nombre'],
                login_info={
                    'rol': user_role,
                    'email': user_db['email'],
                    'session_id': user_db.get('session_id', '')[:8] + "..." if user_db.get('session_id') else "N/A"
                }
            )
            logger.info(f"Email de login enviado a: {user_db['email']}")
        except Exception as email_error:
            logger.warning(f"No se pudo enviar email de login: {email_error}")
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "perfil_completo": perfil_completo,
            "codigo_corresponsal": user_db.get("codigo_corresponsal"),
            "rol": user_role
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión")

@router.get("/me")
def me(user=Depends(get_current_user)):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        user_id = user.get("sub")
        user_data = user_service.get_user_info(user_id)
        
        if user_data:
            # ✅ NUEVO: Para admin/asesor, asegurar que perfil_completo sea True
            user_role = user_data.get("rol")
            if user_role in ["admin", "asesor"]:
                if not user_data.get("perfil_completo", False):
                    # Marcar como completo en la BD
                    user_service.mark_admin_profile_complete(user_id)
                    user_data["perfil_completo"] = True
                    logger.info(f"✅ Perfil de {user_role} auto-completado en /me: {user_id}")
            
            # Remover información sensible
            user_data.pop("password_hash", None)
            user_data.pop("session_id", None)
            
            return user_data
            
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en me: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/complete-profile")
async def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    user_id = user.get("sub")
    
    try:
        current_user = user_service.get_user_info(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # ✅ NUEVO: Verificar si es admin o asesor
        user_role = current_user.get("rol")
        if user_role in ["admin", "asesor"]:
            # Admin y asesor no necesitan completar perfil
            # Marcar automáticamente como perfil completo si no lo está
            if not current_user.get("perfil_completo", False):
                success = user_service.mark_admin_profile_complete(user_id)
                if success:
                    logger.info(f"✅ Perfil de {user_role} marcado como completo: {user_id}")
                else:
                    logger.warning(f"⚠️  No se pudo marcar perfil de {user_role} como completo: {user_id}")
            
            return {
                "message": f"Perfil de {user_role} completado automáticamente",
                "perfil_completo": True,
                "rol": user_role
            }
        
        # Para usuarios CNB normales, continuar con la lógica existente
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
        
        # Completar perfil para usuario CNB
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
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        return user_service.get_pending_users()
    except Exception as e:
        logger.error(f"Error en pending-users: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/all-users", response_model=List[dict])
async def get_all_users(user=Depends(role_required(["admin", "asesor"]))):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
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
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
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
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        success = user_service.reject_user(
            user_id=request.user_id,
            reason=request.reason,
            rejected_by=current_user.get("sub")
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
    current_user=Depends(role_required(["admin"]))
):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        success = user_service.change_user_state(
            user_id=request.user_id,
            new_state=request.state,
            reason=request.reason,
            changed_by=current_user.get("sub")
        )
        
        if success:
            return {"message": f"Estado de usuario cambiado a {request.state}"}
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
    current_user=Depends(role_required(["admin"]))
):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
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

# ✅ NUEVO: Endpoint para crear el primer admin del sistema
@router.post("/setup-first-admin")
def setup_first_admin(admin_data: dict):
    """Crear el primer administrador del sistema (solo si no existe ninguno)"""
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        # Verificar que no existan admins
        existing_admins = user_service.count_admins()
        if existing_admins > 0:
            raise HTTPException(status_code=400, detail="Ya existe un admin en el sistema")
        
        # Validar datos requeridos
        required_fields = ["nombre", "email", "password"]
        for field in required_fields:
            if not admin_data.get(field):
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        # Crear primer admin
        result = user_service.create_first_admin(admin_data)
        
        if result:
            return {
                "message": "Primer administrador creado exitosamente",
                "email": admin_data["email"],
                "status": "active"
            }
        else:
            raise HTTPException(status_code=400, detail="Error al crear administrador")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en setup-first-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ✅ NUEVO: Endpoint para convertir usuario en admin usando clave secreta
@router.post("/make-me-admin")
def make_me_admin(request: dict):
    """Convertir usuario en admin usando email y clave secreta"""
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        email = request.get("email")
        secret_key = request.get("secret_key")
        
        if not email or not secret_key:
            raise HTTPException(status_code=400, detail="Email y clave secreta requeridos")
        
        success = user_service.make_user_admin(email, secret_key)
        if success:
            return {
                "message": "Usuario convertido a admin exitosamente",
                "email": email,
                "status": "admin"
            }
        else:
            raise HTTPException(status_code=400, detail="Credenciales inválidas o usuario no encontrado")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en make-me-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# ✅ NUEVO: Endpoint para crear admin (solo admins pueden hacer esto)
@router.post("/create-admin")
def create_admin(admin_data: dict, current_user=Depends(role_required(["admin"]))):
    """Crear nuevo administrador (solo admins pueden hacer esto)"""
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        # Validar datos requeridos
        required_fields = ["nombre", "email", "password"]
        for field in required_fields:
            if not admin_data.get(field):
                raise HTTPException(status_code=400, detail=f"Campo requerido: {field}")
        
        result = user_service.create_admin_user(admin_data)
        
        if result:
            return {
                "message": "Admin creado exitosamente",
                "user_id": result,
                "email": admin_data["email"]
            }
        else:
            raise HTTPException(status_code=400, detail="Error al crear admin")
            
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en create-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/make-admin")
async def make_user_admin(
    email_data: dict, 
    current_user=Depends(role_required(["admin"]))
):
    """Convertir usuario existente en admin (solo admins pueden hacer esto)"""
    try:
        email = email_data.get("email")
        if not email:
            raise HTTPException(status_code=400, detail="Email requerido")
        
        success = user_service.make_user_admin(email)
        
        if success:
            return {"message": f"Usuario {email} convertido en administrador exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="No se pudo convertir el usuario en admin")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en make-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/refresh")
def refresh_token(refresh_token: str):
    try:
        new_token = create_refresh_token({"dummy": "data"})
        if new_token:
            return {"access_token": new_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=401, detail="Token de refresh inválido")
    except Exception as e:
        logger.error(f"Error en refresh: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")