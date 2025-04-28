# app/models/receipt.py
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field

class ReceiptModel(BaseModel):
    banco: str
    fecha: str
    hora: str
    tipo: str
    nroTransaccion: str = Field(..., alias="nro_transaccion")
    nroControl: str = Field(..., alias="nro_control")
    local: str
    fechaAlternativa: str = Field("", alias="fecha_alternativa")
    corresponsal: str
    tipoCuenta: str = Field("", alias="tipo_cuenta")
    valorTotal: float = Field(..., alias="valor_total")
    fullText: str = Field("", alias="full_text")

    class Config:
        allow_population_by_field_name = True