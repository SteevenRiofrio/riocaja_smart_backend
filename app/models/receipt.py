from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ReceiptModel(BaseModel):
    fecha: str
    hora: str
    tipo: str
    nroTransaccion: str = Field(alias="nro_transaccion")
    valorTotal: float = Field(alias="valor_total")
    fullText: str = Field(alias="full_text")
    
    userId: Optional[str] = Field(None, alias="user_id")
    createdAt: Optional[datetime] = Field(None, alias="created_at")

    class Config:
        populate_by_name = True
        allow_population_by_field_name = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }