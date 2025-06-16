# app/models/password_reset.py
from pydantic import BaseModel, EmailStr, Field
from typing import Optional

class PasswordResetRequest(BaseModel):
    """Modelo para solicitar recuperación de contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com"
            }
        }

class VerifyResetCodeRequest(BaseModel):
    """Modelo para verificar código de recuperación"""
    email: EmailStr = Field(..., description="Email del usuario")
    code: str = Field(..., min_length=6, max_length=6, description="Código de 6 dígitos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "code": "123456"
            }
        }

class ResetPasswordRequest(BaseModel):
    """Modelo para cambiar contraseña"""
    email: EmailStr = Field(..., description="Email del usuario")
    code: str = Field(..., min_length=6, max_length=6, description="Código de verificación")
    new_password: str = Field(..., min_length=8, max_length=50, description="Nueva contraseña")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "usuario@ejemplo.com",
                "code": "123456",
                "new_password": "MiNuevaPassword123!"
            }
        }

class PasswordResetResponse(BaseModel):
    """Respuesta estándar para operaciones de reset"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    message: str = Field(..., description="Mensaje descriptivo del resultado")
    reset_id: Optional[str] = Field(None, description="ID del reset (solo para verificación exitosa)")
    
class ResetStatsResponse(BaseModel):
    """Respuesta con estadísticas de intentos de reset"""
    has_active_request: bool = Field(..., description="Si hay una solicitud activa")
    attempts: Optional[int] = Field(None, description="Número de intentos realizados")
    max_attempts: Optional[int] = Field(None, description="Máximo número de intentos permitidos")
    minutes_remaining: Optional[int] = Field(None, description="Minutos restantes para expiración")
    can_retry: Optional[bool] = Field(None, description="Si puede intentar nuevamente")
    can_request_new: Optional[bool] = Field(None, description="Si puede solicitar un nuevo código")