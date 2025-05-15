from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List  # Añade List aquí
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user, role_required

router = APIRouter()

# Modelos de petición
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
        "rol": user_db["rol"]
    }
    token = create_access_token(token_data)
    return {"access_token": token, "token_type": "bearer"}

@router.get("/me")
def me(user=Depends(get_current_user)):
    return user

# Nuevas rutas para aprobación de usuarios
@router.get("/pending-users", response_model=List[dict])
async def get_pending_users(user=Depends(role_required(["admin", "operador"]))):
    """Obtiene todos los usuarios pendientes de aprobación"""
    return user_service.get_pending_users()

@router.post("/approve-user")
async def approve_user(request: UserApprovalRequest, user=Depends(role_required(["admin", "operador"]))):
    """Aprueba un usuario pendiente"""
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