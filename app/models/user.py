# -*- coding: utf-8 -*-
# app/models/user.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from enum import Enum

class Estado(str, Enum):
    pendiente = "pendiente"
    activo = "activo"
    inactivo = "inactivo"

class Rol(str, Enum):
    admin = "admin"
    operador = "operador"
    lector = "lector"

class User(BaseModel):
    nombre: str
    email: EmailStr
    password_hash: str
    rol: str = "lector"
    estado: str = "pendiente"
    fecha_registro: datetime = Field(default_factory=datetime.utcnow)
    perfil_completo: bool = False
    
    # Campos opcionales
    nombre_local: Optional[str] = None
    codigo_corresponsal: Optional[str] = None
    aprobado_por: Optional[str] = None
    fecha_aprobacion: Optional[datetime] = None
    fecha_perfil_completado: Optional[datetime] = None
    intentos_fallidos: int = 0

class UserProfile(BaseModel):
    codigo_corresponsal: str
    nombre_local: str
    nombre_completo: str
    password: str = Field(min_length=8)

class UserApprovalWithCode(BaseModel):
    user_id: str
    codigo_corresponsal: str