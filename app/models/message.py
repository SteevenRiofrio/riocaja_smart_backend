# app/models/message.py - Nuevo archivo
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class TipoMensaje(str, Enum):
    informativo = "informativo"
    advertencia = "advertencia"
    urgente = "urgente"

class Mensaje(BaseModel):
    titulo: str
    contenido: str
    tipo: TipoMensaje = TipoMensaje.informativo
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    creado_por: str  # ID del administrador que creó el mensaje
    visible_hasta: Optional[datetime] = None  # Fecha límite de visibilidad
    destinatarios: Optional[List[str]] = None  # Lista de IDs de usuarios, si es None, es para todos
    leido_por: List[str] = []  # IDs de usuarios que han leído el mensaje