# app/routes/messages.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from app.services.message_service import MessageService
from app.middlewares.auth_middleware import get_current_user, role_required

router = APIRouter()

# Modelos para mensajes
class MessageCreate(BaseModel):
    titulo: str
    contenido: str
    tipo: str = "informativo"
    visible_hasta: Optional[datetime] = None
    destinatarios: Optional[List[str]] = None

class MessageRead(BaseModel):
    message_id: str

# Inicializar servicio
message_service = MessageService()

@router.post("/create")
async def create_message(message: MessageCreate, user=Depends(role_required(["admin", "operador"]))):
    """Crea un nuevo mensaje (solo admin y operador)"""
    admin_id = user.get("sub")
    try:
        created_message = message_service.create_message(
            titulo=message.titulo,
            contenido=message.contenido,
            tipo=message.tipo,
            creado_por=admin_id,
            visible_hasta=message.visible_hasta,
            destinatarios=message.destinatarios
        )
        return created_message
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/")
async def get_messages(user=Depends(get_current_user)):
    """Obtiene los mensajes para el usuario actual"""
    user_id = user.get("sub")
    messages = message_service.get_messages_for_user(user_id)
    return {"data": messages, "count": len(messages)}

@router.post("/mark-read")
async def mark_message_as_read(request: MessageRead, user=Depends(get_current_user)):
    """Marca un mensaje como leido por el usuario actual"""
    user_id = user.get("sub")
    success = message_service.mark_message_as_read(request.message_id, user_id)
    return {"success": success}

@router.delete("/{message_id}")
async def delete_message(message_id: str, user=Depends(role_required(["admin", "operador"]))):
    """Elimina un mensaje (solo admin y operador)"""
    success = message_service.delete_message(message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mensaje no encontrado")
    return {"message": "Mensaje eliminado correctamente"}