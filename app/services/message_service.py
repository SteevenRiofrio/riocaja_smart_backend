        return result.deleted_count > 0
# app/services/message_service.py
import logging
from datetime import datetime
from typing import List, Optional, Dict
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

class MessageService:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.messages = self.db["messages"]
            self.users = self.db["users"]
            logger.info("MessageService inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def create_message(self, titulo: str, contenido: str, tipo: str = "informativo", 
                      creado_por: str = None, visible_hasta: datetime = None, 
                      destinatarios: List[str] = None) -> dict:
        try:
            message_data = {
                "titulo": titulo,
                "contenido": contenido,
                "tipo": tipo,
                "fecha_creacion": datetime.utcnow(),
                "creado_por": creado_por,
                "visible_hasta": visible_hasta,
                "destinatarios": destinatarios,
                "leido_por": []
            }
            
            result = self.messages.insert_one(message_data)
            logger.info(f"Mensaje creado: {titulo}")
            
            return {
                "id": str(result.inserted_id),
                "message": "Mensaje creado exitosamente"
            }
        except Exception as e:
            logger.error(f"Error al crear mensaje: {e}")
            raise ValueError("Error al crear el mensaje")

    def get_messages_for_user(self, user_id: str) -> List[dict]:
        try:
            query = {
                "$and": [
                    {
                        "$or": [
                            {"destinatarios": None},
                            {"destinatarios": {"$in": [user_id]}}
                        ]
                    },
                    {
                        "$or": [
                            {"visible_hasta": None},
                            {"visible_hasta": {"$gte": datetime.utcnow()}}
                        ]
                    }
                ]
            }
            
            messages = list(self.messages.find(query).sort("fecha_creacion", DESCENDING))
            
            for message in messages:
                message["_id"] = str(message["_id"])
                message["leido"] = user_id in message.get("leido_por", [])
                if message.get("creado_por"):
                    message["creado_por"] = str(message["creado_por"])
            
            return messages
        except Exception as e:
            logger.error(f"Error al obtener mensajes: {e}")
            return []

    def mark_message_as_read(self, message_id: str, user_id: str) -> bool:
        try:
            result = self.messages.update_one(
                {"_id": ObjectId(message_id)},
                {"$addToSet": {"leido_por": user_id}}
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error al marcar mensaje como leido: {e}")
            return False

    def delete_message(self, message_id: str) -> bool:
        try:
            result = self.messages.delete_one({"_id": ObjectId(message_id)})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"Error al eliminar mensaje: {e}")
            return False