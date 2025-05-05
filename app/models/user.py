from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class Rol(str, Enum):
    admin = "admin"
    operador = "operador"
    lector = "lector"

class Estado(str, Enum):
    activo = "activo"
    inactivo = "inactivo"

class User(BaseModel):
    nombre: str
    email: EmailStr
    password_hash: str
    rol: Rol = Rol.lector
    estado: Estado = Estado.activo
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    intentos_fallidos: int = 0
    token_recuperacion: Optional[str] = None
