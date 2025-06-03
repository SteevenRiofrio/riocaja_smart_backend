from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum

class Estado(str, Enum):
    pendiente = "pendiente"
    activo = "activo"
    inactivo = "inactivo"

class Rol(str, Enum):
    lector = "lector"
    operador = "operador"
    admin = "admin"

class User(BaseModel):
    nombre: str
    email: EmailStr
    password_hash: str
    rol: str = "lector"
    estado: Estado = Estado.pendiente
    fecha_registro: datetime = datetime.utcnow()
    intentos_fallidos: int = 0
    
    # NUEVOS CAMPOS PARA CORRESPONSAL
    codigo_corresponsal: Optional[str] = None  # Asignado por admin al aprobar
    nombre_local: Optional[str] = None         # Completado por usuario
    perfil_completo: bool = False              # Indica si completo el perfil inicial
    
    # Campos de auditoria
    aprobado_por: Optional[str] = None
    fecha_aprobacion: Optional[datetime] = None
    fecha_perfil_completado: Optional[datetime] = None

class UserProfile(BaseModel):
    """Modelo para completar perfil de usuario"""
    codigo_corresponsal: str
    nombre_local: str
    nombre_completo: str
    password: str  # Nueva contraseña

class UserApprovalWithCode(BaseModel):
    """Modelo para aprobacion con codigo de corresponsal"""
    user_id: str
    codigo_corresponsal: str