# app/services/message_service.py
import logging
from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from pymongo import MongoClient, DESCENDING
from app.config import MONGO_URI, DATABASE_NAME
from app.models.message import Mensaje, TipoMensaje

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para mensajes...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.messages = self.db["messages"]
            logger.info(f"Conexion exitosa a la base de datos: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise
    
    def create_message(self, titulo: str, contenido: str, tipo: str, 
                      creado_por: str, visible_hasta: Optional[datetime] = None,
                      destinatarios: Optional[List[str]] = None) -> dict:
        """Crea un nuevo mensaje"""
        if tipo not in [t.value for t in TipoMensaje]:
            raise ValueError(f"Tipo de mensaje invalido: {tipo}")
            
        message = Mensaje(
            titulo=titulo,
            contenido=contenido,
            tipo=tipo,
            creado_por=creado_por,
            visible_hasta=visible_hasta,
            destinatarios=destinatarios
        )
        
        message_dict = message.dict()
        result = self.messages.insert_one(message_dict)
        message_dict["_id"] = str(result.inserted_id)
        
        logger.info(f"Mensaje creado: {message_dict['_id']}")
        return message_dict
    
    def get_messages_for_user(self, user_id: str) -> List[dict]:
        """Obtiene los mensajes visibles para un usuario especifico"""
        # Buscar mensajes que son para todos o específicamente para este usuario
        query = {
            "$or": [
                {"destinatarios": None},  # Para todos los usuarios
                {"destinatarios": user_id}  # Específicamente para este usuario
            ]
        }
        
        # Si el mensaje tiene fecha límite, verificar que no haya expirado
        current_time = datetime.utcnow()
        query["$or"].append({"visible_hasta": None})  # Sin fecha de expiración
        query["$or"].append({"visible_hasta": {"$gt": current_time}})  # No expirado
        
        messages = list(self.messages.find(query).sort("fecha_creacion", DESCENDING))
        
        # Convertir ObjectId a string
        for message in messages:
            message["_id"] = str(message["_id"])
            
        return messages
    
    def mark_message_as_read(self, message_id: str, user_id: str) -> bool:
        """Marca un mensaje como leido por un usuario"""
        result = self.messages.update_one(
            {"_id": ObjectId(message_id), "leido_por": {"$ne": user_id}},
            {"$addToSet": {"leido_por": user_id}}
        )
        return result.modified_count > 0
    
    def delete_message(self, message_id: str) -> bool:
        """Elimina un mensaje"""
        result = self.messages.delete_one({"_id": ObjectId(message_id)})
        return result.deleted_count > 0