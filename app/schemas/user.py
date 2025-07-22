from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import Optional, List
from datetime import datetime
from enum import Enum

# Enums para validación API
class Estado(str, Enum):
    pendiente = "pendiente"
    activo = "activo"
    inactivo = "inactivo"

class Rol(str, Enum):
    admin = "admin"
    asesor = "asesor"
    cnb = "cnb"

# Schemas base para User
class UserBase(BaseModel):
    """Schema base para operaciones de usuario"""
    nombre: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    rol: Rol = Rol.cnb
    estado: Estado = Estado.pendiente
    
    # Campos opcionales
    nombre_local: Optional[str] = Field(None, max_length=255)
    codigo_corresponsal: Optional[str] = Field(None, max_length=50)

class UserCreate(UserBase):
    """Schema para crear usuario"""
    password: str = Field(..., min_length=8, max_length=100)

class UserUpdate(BaseModel):
    """Schema para actualizar usuario"""
    nombre: Optional[str] = Field(None, min_length=2, max_length=255)
    email: Optional[EmailStr] = None
    rol: Optional[Rol] = None
    estado: Optional[Estado] = None
    nombre_local: Optional[str] = Field(None, max_length=255)
    codigo_corresponsal: Optional[str] = Field(None, max_length=50)
    perfil_completo: Optional[bool] = None

class UserProfile(BaseModel):
    """Schema para completar perfil"""
    codigo_corresponsal: str = Field(..., min_length=1, max_length=50)
    nombre_local: str = Field(..., min_length=2, max_length=255)

class UserApprovalWithCode(BaseModel):
    """Schema para aprobar usuario con código"""
    user_id: str
    codigo_corresponsal: str = Field(..., min_length=1, max_length=50)

# Schemas de respuesta (con datos de BD)
class UserResponse(UserBase):
    """Schema para respuestas de usuario (lectura)"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    fecha_registro: datetime
    perfil_completo: bool
    activo: bool
    intentos_fallidos: int
    fecha_aprobacion: Optional[datetime] = None
    fecha_perfil_completado: Optional[datetime] = None
    aprobado_por: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UserWithPrivacy(UserResponse):
    """Schema de usuario con información de privacidad"""
    has_valid_consent: bool = False
    pending_right_requests: int = 0
    last_consent_date: Optional[datetime] = None

# Schemas para operaciones específicas
class UserLogin(BaseModel):
    """Schema para login"""
    email: EmailStr
    password: str

class UserPasswordChange(BaseModel):
    """Schema para cambio de contraseña"""
    current_password: str
    new_password: str = Field(..., min_length=8, max_length=100)

class UserList(BaseModel):
    """Schema para listas de usuarios"""
    users: List[UserResponse]
    total: int
    page: int
    size: int