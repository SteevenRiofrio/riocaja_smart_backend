from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from typing import Optional
from app.services.user_service import UserService
from app.services.auth_service import create_access_token
from app.middlewares.auth_middleware import get_current_user

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
