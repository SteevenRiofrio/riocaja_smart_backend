from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class ConsentRequest(BaseModel):
    consent_version: str = Field(..., description="Versión del consentimiento")
    essential_consent: bool = Field(..., description="Consentimiento para datos esenciales")
    marketing_consent: bool = Field(default=False, description="Consentimiento para marketing")
    consent_details: Dict[str, Any] = Field(..., description="Detalles técnicos del consentimiento")
    ip_address: Optional[str] = Field(None, description="Dirección IP del usuario")
    user_agent: Optional[str] = Field(None, description="User agent del dispositivo")

class ConsentResponse(BaseModel):
    success: bool
    message: str
    consent_id: int
    valid_until: datetime

class RightRequest(BaseModel):
    right_type: str = Field(..., description="Tipo de derecho: ACCESO, RECTIFICACION, etc.")
    description: Optional[str] = Field(None, description="Descripción opcional de la solicitud")

class ConsentStatus(BaseModel):
    has_valid_consent: bool
    essential_consent: bool
    marketing_consent: bool
    consent_version: str
    granted_at: datetime
    valid_until: datetime
    requires_consent: bool