# app/models/user.py - Actualización
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
    pendiente = "pendiente"  # Nuevo estado para usuarios que esperan aprobación

class User(BaseModel):
    nombre: str
    email: EmailStr
    password_hash: str
    rol: Rol = Rol.lector
    estado: Estado = Estado.pendiente  # Cambiamos el estado por defecto a pendiente
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    intentos_fallidos: int = 0
    token_recuperacion: Optional[str] = None
    aprobado_por: Optional[str] = None  # ID del administrador que aprobó al usuario
    fecha_aprobacion: Optional[datetime] = None  # Fecha de aprobación