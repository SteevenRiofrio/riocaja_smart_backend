# app/routes/auth.py - ACTUALIZADO CON CÓDIGO CORRESPONSAL
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user, role_required
from app.models.user import UserProfile, UserApprovalWithCode

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

# NUEVA RUTA: Completar perfil de usuario
@router.post("/complete-profile")
async def complete_profile(profile: UserProfile, user=Depends(get_current_user)):
    """Completa el perfil del usuario en su primer login"""
    user_id = user.get("sub")
    
    try:
        success = user_service.complete_user_profile(
            user_id=user_id,
            codigo_corresponsal=profile.codigo_corresponsal,
            nombre_local=profile.nombre_local,
            nombre_completo=profile.nombre_completo,
            nueva_password=profile.password
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Error al completar perfil o código incorrecto")
        
        return {"message": "Perfil completado correctamente"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# NUEVA RUTA: Verificar código de corresponsal
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

# RUTA ACTUALIZADA: Aprobar usuario con código de corresponsal
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