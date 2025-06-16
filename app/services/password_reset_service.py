# app/services/password_reset_service.py
from datetime import datetime
from typing import Optional
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME
from app.services.email_service import EmailService
from app.services.crypto_service import hash_password
import logging

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self):
        try:
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db["users"]
            self.password_resets = self.db["password_resets"]
            self.email_service = EmailService()
            logger.info("PasswordResetService inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar PasswordResetService: {e}")
            raise
    
    async def request_password_reset(self, email: str) -> dict:
        """
        Solicita un reset de contraseña para el email dado
        
        Args:
            email: Email del usuario
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            # Verificar que el usuario existe y está activo
            user = self.users.find_one({
                "email": email.lower().strip(),
                "estado": "activo"
            })
            
            if not user:
                # Por seguridad, no revelamos si el email existe o no
                logger.warning(f"Intento de reset para email no registrado o inactivo: {email}")
                return {
                    "success": True,
                    "message": "Si el email está registrado, recibirás un código de recuperación."
                }
            
            # Limpiar códigos anteriores del mismo usuario
            self.password_resets.delete_many({"email": email.lower().strip()})
            
            # Generar nuevo código
            reset_code = self.email_service.generate_reset_code()
            expires_at = self.email_service.get_reset_code_expiry()
            
            # Guardar código en la base de datos
            reset_document = {
                "email": email.lower().strip(),
                "user_id": str(user["_id"]),
                "code": reset_code,
                "expires_at": expires_at,
                "used": False,
                "created_at": datetime.utcnow(),
                "attempts": 0  # Contador de intentos de verificación
            }
            
            result = self.password_resets.insert_one(reset_document)
            
            if result.inserted_id:
                # Enviar email
                email_sent = await self.email_service.send_password_reset_email(
                    email=email,
                    name=user.get("nombre", "Usuario"),
                    reset_code=reset_code
                )
                
                if email_sent:
                    logger.info(f"Código de recuperación generado y enviado para: {email}")
                    return {
                        "success": True,
                        "message": "Si el email está registrado, recibirás un código de recuperación."
                    }
                else:
                    # Si falla el envío del email, eliminar el código
                    self.password_resets.delete_one({"_id": result.inserted_id})
                    logger.error(f"Error enviando email de recuperación a: {email}")
                    return {
                        "success": False,
                        "message": "Error al enviar el email de recuperación. Intenta más tarde."
                    }
            else:
                logger.error(f"Error al guardar código de recuperación para: {email}")
                return {
                    "success": False,
                    "message": "Error interno. Intenta más tarde."
                }
                
        except Exception as e:
            logger.error(f"Error en request_password_reset para {email}: {str(e)}")
            return {
                "success": False,
                "message": "Error interno. Intenta más tarde."
            }
    
    def verify_reset_code(self, email: str, code: str) -> dict:
        """
        Verifica si el código de recuperación es válido
        
        Args:
            email: Email del usuario
            code: Código de verificación
            
        Returns:
            dict: Resultado de la verificación
        """
        try:
            email = email.lower().strip()
            code = code.strip()
            
            # Buscar código válido
            reset_request = self.password_resets.find_one({
                "email": email,
                "code": code,
                "used": False,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if not reset_request:
                # Incrementar intentos si existe el registro
                self.password_resets.update_one(
                    {"email": email, "used": False},
                    {"$inc": {"attempts": 1}}
                )
                
                logger.warning(f"Código inválido o expirado para: {email}")
                return {
                    "success": False,
                    "message": "Código inválido o expirado."
                }
            
            # Verificar número de intentos (máximo 3)
            if reset_request.get("attempts", 0) >= 3:
                # Marcar como usado para evitar más intentos
                self.password_resets.update_one(
                    {"_id": reset_request["_id"]},
                    {"$set": {"used": True}}
                )
                
                logger.warning(f"Demasiados intentos fallidos para: {email}")
                return {
                    "success": False,
                    "message": "Demasiados intentos fallidos. Solicita un nuevo código."
                }
            
            logger.info(f"Código verificado correctamente para: {email}")
            return {
                "success": True,
                "message": "Código verificado correctamente.",
                "reset_id": str(reset_request["_id"])
            }
            
        except Exception as e:
            logger.error(f"Error en verify_reset_code para {email}: {str(e)}")
            return {
                "success": False,
                "message": "Error interno. Intenta más tarde."
            }
    
    async def reset_password(self, email: str, code: str, new_password: str) -> dict:
        """
        Cambia la contraseña del usuario usando el código de verificación
        
        Args:
            email: Email del usuario
            code: Código de verificación
            new_password: Nueva contraseña
            
        Returns:
            dict: Resultado de la operación
        """
        try:
            email = email.lower().strip()
            code = code.strip()
            
            # Verificar que el código sigue siendo válido
            verification = self.verify_reset_code(email, code)
            if not verification["success"]:
                return verification
            
            # Validar nueva contraseña
            if len(new_password) < 8:
                return {
                    "success": False,
                    "message": "La contraseña debe tener al menos 8 caracteres."
                }
            
            # Buscar el usuario
            user = self.users.find_one({
                "email": email,
                "estado": "activo"
            })
            
            if not user:
                logger.error(f"Usuario no encontrado o inactivo durante reset: {email}")
                return {
                    "success": False,
                    "message": "Usuario no encontrado."
                }
            
            # Hashear nueva contraseña
            hashed_password = hash_password(new_password)
            
            # Actualizar contraseña en la base de datos
            update_result = self.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "password_hash": hashed_password,
                        "password_changed_at": datetime.utcnow()
                    }
                }
            )
            
            if update_result.modified_count > 0:
                # Marcar código como usado
                self.password_resets.update_one(
                    {"email": email, "code": code},
                    {"$set": {"used": True, "used_at": datetime.utcnow()}}
                )
                
                # Enviar notificación de cambio de contraseña
                await self.email_service.send_password_changed_notification(
                    email=email,
                    name=user.get("nombre", "Usuario")
                )
                
                logger.info(f"Contraseña actualizada exitosamente para: {email}")
                return {
                    "success": True,
                    "message": "Contraseña actualizada exitosamente."
                }
            else:
                logger.error(f"Error al actualizar contraseña para: {email}")
                return {
                    "success": False,
                    "message": "Error al actualizar la contraseña. Intenta más tarde."
                }
                
        except Exception as e:
            logger.error(f"Error en reset_password para {email}: {str(e)}")
            return {
                "success": False,
                "message": "Error interno. Intenta más tarde."
            }
    
    def cleanup_expired_codes(self):
        """
        Limpia códigos expirados de la base de datos
        """
        try:
            result = self.password_resets.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            if result.deleted_count > 0:
                logger.info(f"Se eliminaron {result.deleted_count} códigos expirados")
                
        except Exception as e:
            logger.error(f"Error en cleanup_expired_codes: {str(e)}")
    
    def get_reset_stats(self, email: str) -> dict:
        """
        Obtiene estadísticas de intentos de reset para un email
        
        Args:
            email: Email del usuario
            
        Returns:
            dict: Estadísticas de intentos
        """
        try:
            email = email.lower().strip()
            
            # Buscar solicitud activa
            active_request = self.password_resets.find_one({
                "email": email,
                "used": False,
                "expires_at": {"$gt": datetime.utcnow()}
            })
            
            if active_request:
                time_remaining = active_request["expires_at"] - datetime.utcnow()
                minutes_remaining = int(time_remaining.total_seconds() / 60)
                
                return {
                    "has_active_request": True,
                    "attempts": active_request.get("attempts", 0),
                    "max_attempts": 3,
                    "minutes_remaining": max(0, minutes_remaining),
                    "can_retry": active_request.get("attempts", 0) < 3
                }
            else:
                return {
                    "has_active_request": False,
                    "can_request_new": True
                }
                
        except Exception as e:
            logger.error(f"Error en get_reset_stats para {email}: {str(e)}")
            return {
                "has_active_request": False,
                "can_request_new": True
            }