# app/routes/auth.py - VERSIÓN CORREGIDA COMPLETA
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user, role_required
from app.models.user import UserProfile, UserApprovalWithCode

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
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en login: {e}")
        raise HTTPException(status_code=500, detail="Error de conexión con la base de datos")

@router.get("/me")
def me(user=Depends(get_current_user)):
    try:
        user_id = user.get("sub")
        user_data = user_service.get_user_info(user_id)
        
        if not user_data:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # DEVOLVER DATOS COMPLETOS Y CORRECTOS DE LA BASE DE DATOS
        return {
            "success": True,
            "data": {
                "_id": user_data["_id"],
                "nombre": user_data["nombre"],  # NOMBRE REAL DE LA BD
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
            return {"message": "Usuario aprobado exitosamente"}
        else:
            raise HTTPException(status_code=400, detail="Error al aprobar usuario")
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error en approve-user: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")