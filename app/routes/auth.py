# app/routes/auth.py - VERSIÓN CORREGIDA
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user, role_required
from app.models.user import UserProfile, UserApprovalWithCode

# CREAR EL ROUTER PRIMERO
router = APIRouter()

# Modelos de petición existentes
class UserRegister(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    rol: Optional[str] = "lector"

class UserLogin(BaseModel):
    email: EmailStr
    password: str
    
class UserApprovalRequest(BaseModel):
    user_id: str

class ChangeRoleRequest(BaseModel):
    user_id: str
    role: str

# NUEVO: Modelo para cambiar estado
class ChangeStateRequest(BaseModel):
    user_id: str
    state: str

# Inicializa el servicio
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

@router.post("/login")
def login(user: UserLogin):
    user_db = user_service.authenticate_user(user.email, user.password)
    if not user_db:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")

    token_data = {
        "sub": user_db["_id"],
        "email": user_db["email"],
        "rol": user_db["rol"],
        "perfil_completo": user_db.get("perfil_completo", False)
    }
    token = create_access_token(token_data)
    
    return {
        "access_token": token, 
        "token_type": "bearer",
        "perfil_completo": user_db.get("perfil_completo", False),
        "codigo_corresponsal": user_db.get("codigo_corresponsal")
    }

@router.get("/me")
def me(user=Depends(get_current_user)):
    return user

# Completar perfil de usuario (existente)
@router.post("/complete-profile")
async def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    """Completa el perfil del usuario en su primer login"""
    user_id = user.get("sub")
    
    try:
        # VERIFICAR QUE EL USUARIO EXISTE Y ESTÁ APROBADO
        current_user = user_service.get_user_info(user_id)
        if not current_user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # VERIFICAR QUE EL USUARIO ESTÁ APROBADO Y TIENE CÓDIGO ASIGNADO
        if current_user.get("estado") != "activo":
            raise HTTPException(status_code=400, detail="Su cuenta aún no ha sido aprobada")
        
        if not current_user.get("codigo_corresponsal"):
            raise HTTPException(status_code=400, detail="No tiene un código de corresponsal asignado. Contacte al administrador.")
        
        # VERIFICAR QUE EL CÓDIGO ENVIADO COINCIDE CON EL ASIGNADO
        codigo_asignado = current_user.get("codigo_corresponsal")
        codigo_enviado = profile.codigo_corresponsal
        
        if codigo_asignado != codigo_enviado:
            raise HTTPException(
                status_code=400, 
                detail=f"El código proporcionado no coincide con el asignado. Código esperado: {codigo_asignado}"
            )
        
        # COMPLETAR EL PERFIL - SOLO ACTUALIZAR NOMBRE LOCAL Y MARCAR COMO COMPLETO
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
        print(f"Error en complete_profile: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

# Verificar código de corresponsal (existente)
@router.get("/verify-code/{codigo}")
async def verify_corresponsal_code(codigo: str, user=Depends(get_current_user)):
    """Verifica si el código de corresponsal es válido para el usuario"""
    user_id = user.get("sub")
    
    is_valid = user_service.verify_corresponsal_code(user_id, codigo)
    return {"valid": is_valid}

# Rutas para administradores
@router.get("/pending-users", response_model=List[dict])
async def get_pending_users(user=Depends(role_required(["admin", "operador"]))):
    """Obtiene todos los usuarios pendientes de aprobación"""
    return user_service.get_pending_users()

# NUEVA: Obtener todos los usuarios
@router.get("/all-users", response_model=List[dict])
async def get_all_users(user=Depends(role_required(["admin", "operador"]))):
    """Obtiene todos los usuarios del sistema"""
    return user_service.get_all_users()

# NUEVA: Obtener detalles de un usuario específico
@router.get("/user-details/{user_id}")
async def get_user_details(user_id: str, user=Depends(role_required(["admin", "operador"]))):
    """Obtiene los detalles completos de un usuario específico"""
    user_details = user_service.get_user_info(user_id)
    if not user_details:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user_details

# NUEVA: Buscar usuarios
@router.get("/search-users", response_model=List[dict])
async def search_users(
    q: str = Query(..., description="Término de búsqueda"),
    user=Depends(role_required(["admin", "operador"]))
):
    """Busca usuarios por nombre, email, código de corresponsal, etc."""
    if len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="El término de búsqueda debe tener al menos 2 caracteres")
    
    return user_service.search_users(q.strip())

# NUEVA: Obtener estadísticas de usuarios
@router.get("/user-stats")
async def get_user_stats(user=Depends(role_required(["admin", "operador"]))):
    """Obtiene estadísticas generales de usuarios"""
    return user_service.get_user_statistics()

# Aprobar usuario con código (existente)
@router.post("/approve-user-with-code")
async def approve_user_with_code(request: UserApprovalWithCode, user=Depends(role_required(["admin", "operador"]))):
    """Aprueba un usuario y le asigna un código de corresponsal"""
    admin_id = user.get("sub")
    
    try:
        success = user_service.approve_user_with_code(
            user_id=request.user_id,
            admin_id=admin_id,
            codigo_corresponsal=request.codigo_corresponsal
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Usuario no encontrado o ya aprobado")
        
        return {"message": "Usuario aprobado y código asignado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/approve-user")
async def approve_user(request: UserApprovalRequest, user=Depends(role_required(["admin", "operador"]))):
    """Aprueba un usuario pendiente (método legacy)"""
    admin_id = user.get("sub")
    success = user_service.approve_user(request.user_id, admin_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o ya aprobado")
    return {"message": "Usuario aprobado correctamente"}

@router.post("/reject-user")
async def reject_user(request: UserApprovalRequest, user=Depends(role_required(["admin", "operador"]))):
    """Rechaza un usuario pendiente"""
    success = user_service.reject_user(request.user_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario no encontrado o ya rechazado")
    return {"message": "Usuario rechazado correctamente"}

@router.post("/change-role")
async def change_user_role(request: ChangeRoleRequest, user=Depends(role_required(["admin"]))):
    """Cambia el rol de un usuario"""
    try:
        success = user_service.change_user_role(request.user_id, request.role)
        if not success:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"message": f"Rol cambiado a {request.role} correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# NUEVA: Cambiar estado del usuario
@router.put("/change-state")
async def change_user_state(request: ChangeStateRequest, user=Depends(role_required(["admin", "operador"]))):
    """Cambia el estado de un usuario (activo, suspendido, inactivo)"""
    try:
        # Validar estados permitidos
        valid_states = ["activo", "suspendido", "inactivo"]
        if request.state not in valid_states:
            raise HTTPException(
                status_code=400, 
                detail=f"Estado inválido. Estados permitidos: {', '.join(valid_states)}"
            )
        
        success = user_service.change_user_state(request.user_id, request.state)
        if not success:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        return {"message": f"Estado cambiado a '{request.state}' correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# NUEVA: Activar usuario suspendido
@router.post("/activate-user")
async def activate_user(request: UserApprovalRequest, user=Depends(role_required(["admin", "operador"]))):
    """Activa un usuario que estaba suspendido o inactivo"""
    try:
        success = user_service.change_user_state(request.user_id, "activo")
        if not success:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"message": "Usuario activado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# NUEVA: Suspender usuario
@router.post("/suspend-user")
async def suspend_user(request: UserApprovalRequest, user=Depends(role_required(["admin", "operador"]))):
    """Suspende un usuario activo"""
    try:
        success = user_service.change_user_state(request.user_id, "suspendido")
        if not success:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        return {"message": "Usuario suspendido correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# NUEVA: Obtener usuarios por estado
@router.get("/users-by-state/{state}")
async def get_users_by_state(state: str, user=Depends(role_required(["admin", "operador"]))):
    """Obtiene usuarios filtrados por estado"""
    valid_states = ["activo", "pendiente", "suspendido", "inactivo"]
    if state not in valid_states:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Estados válidos: {', '.join(valid_states)}"
        )
    
    return user_service.get_users_by_state(state)

# NUEVA: Obtener usuarios por rol
@router.get("/users-by-role/{role}")
async def get_users_by_role(role: str, user=Depends(role_required(["admin", "operador"]))):
    """Obtiene usuarios filtrados por rol"""
    valid_roles = ["admin", "operador", "lector"]
    if role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Rol inválido. Roles válidos: {', '.join(valid_roles)}"
        )
    
    return user_service.get_users_by_role(role)