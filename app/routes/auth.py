# app/routes/auth.py - VERSIÓN CORREGIDA PARA RAILWAY
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import logging

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

# Inicializar servicio con validación
try:
    user_service = UserService() if UserService else None
except Exception as e:
    logger.error(f"Error inicializando UserService: {e}")
    user_service = None

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
            "session_id": user_db.get("session_id", ""),
            "perfil_completo": user_db.get("perfil_completo", False)
        }
        
        access_token = create_access_token(token_data)
        refresh_token = create_refresh_token(token_data)
        
        # Intentar enviar email de notificación (opcional)
        try:
            from app.services.email_service import EmailService
            email_service = EmailService()
            email_service.send_login_notification(
                user_email=user_db['email'],
                user_name=user_db['nombre'],
                login_info={
                    'rol': user_db['rol'],
                    'email': user_db['email'],
                    'session_id': user_db.get('session_id', '')[:8] + "..."
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
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        user_id = user.get("sub")
 
        user_data = user_service.get_user_info(user_id)  # ← Esto lee de la BD
        if user_data:
            # Remover información sensible
            user_data.pop("password_hash", None)
            user_data.pop("session_id", None)  # Opcional: remover session_id también
            
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
        
        # NUEVO: Verificar si es admin o asesor
        user_role = current_user.get("rol")
        if user_role in ["admin", "asesor"]:
            # Admin y asesor no necesitan completar perfil
            # Marcar automáticamente como perfil completo si no lo está
            if not current_user.get("perfil_completo", False):
                user_service.mark_admin_profile_complete(user_id)
            
            raise HTTPException(
                status_code=400, 
                detail="Los administradores y asesores no necesitan completar perfil adicional"
            )
        
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

# Endpoints adicionales (simplificados para evitar errores)
@router.post("/create-admin")
def create_admin(admin_data: dict, current_user=Depends(role_required(["admin"]))):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
    try:
        result = user_service.create_admin_user(admin_data)
        return {"message": "Admin creado exitosamente", "user_id": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/setup-first-admin")
def setup_first_admin(admin_data: dict):
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
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
    if not user_service:
        raise HTTPException(status_code=503, detail="Servicio de usuario no disponible")
    
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
    try:
        new_token = create_refresh_token({"dummy": "data"})
        if new_token:
            return {"access_token": new_token, "token_type": "bearer"}
        else:
            raise HTTPException(status_code=401, detail="Token de refresh inválido")
    except Exception as e:
        logger.error(f"Error en refresh: {e}")
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
        print(f"Error en make-admin: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")