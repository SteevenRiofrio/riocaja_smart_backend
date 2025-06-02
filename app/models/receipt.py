from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReceiptModel(BaseModel):
    fecha: str = Field(..., description="Fecha en formato dd/MM/yyyy")
    hora: str = Field(..., description="Hora en formato HH:mm:ss")
    tipo: str = Field(..., description="Tipo de comprobante detectado")
    nroTransaccion: str = Field(..., alias="nro_transaccion", description="Numero de transaccion")
    valorTotal: float = Field(..., alias="valor_total", description="Valor total del comprobante")
    fullText: str = Field(..., alias="full_text", description="Texto completo escaneado")
    
    userId: Optional[str] = Field(None, alias="user_id", description="ID del usuario que creo el comprobante")
    createdAt: Optional[datetime] = Field(None, alias="created_at", description="Fecha de creacion en el sistema")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        schema_extra = {
            "example": {
                "fecha": "29/04/2025",
                "hora": "15:30:25",
                "tipo": "PAGO DE SERVICIO",
                "nro_transaccion": "123456789",
                "valor_total": 25.50,
                "full_text": "Texto completo del comprobante escaneado..."
            }
        }