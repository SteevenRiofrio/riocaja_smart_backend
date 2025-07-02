# -*- coding: utf-8 -*-
# app/services/password_reset_service.py
import smtplib
import ssl
import random
import string
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pymongo import MongoClient
from bson import ObjectId
from app.config import (
    MONGO_URI, DATABASE_NAME, MAIL_USERNAME, MAIL_PASSWORD, 
    MAIL_FROM, MAIL_FROM_NAME, MAIL_SERVER, MAIL_PORT,
    MAIL_STARTTLS, RESET_CODE_EXPIRE_MINUTES, RESET_CODE_LENGTH
)
from app.services.crypto_service import hash_password

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para password reset...")
            self.client = MongoClient(
                MONGO_URI,
                connect=False,  # No conectar inmediatamente
                serverSelectionTimeoutMS=30000,
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                retryWrites=True,
                retryReads=True,
                maxIdleTimeMS=45000,
                waitQueueTimeoutMS=10000
            )
            
            self.db = self.client[DATABASE_NAME]
            self.users = self.db["users"]
            self.reset_codes = self.db["password_reset_codes"]
            
            # Probar conexión sin fallar
            try:
                self.client.admin.command('ping')
                logger.info("✅ Conexión exitosa para password reset")
            except Exception as ping_error:
                logger.warning(f"⚠️ No se pudo hacer ping a MongoDB (password_reset): {ping_error}")
                # Continuar sin fallar
                
        except Exception as e:
            logger.error(f"❌ Error al inicializar conexión MongoDB (password_reset): {e}")
            # No hacer raise aquí
            self.client = None
            self.db = None
            self.users = None
            self.reset_codes = None

    def _ensure_connection(self):
        """Asegurar que la conexión esté disponible antes de usar"""
        if self.client is None or self.db is None or self.users is None or self.reset_codes is None:
            logger.error("Conexión a MongoDB no está inicializada")
            raise Exception("Error de conexión a la base de datos")

    def _generate_reset_code(self) -> str:
        """Generar código de reset de 6 dígitos"""
        return ''.join(random.choices(string.digits, k=RESET_CODE_LENGTH))

    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
        """Enviar email de notificación"""
        try:
            logger.info(f"Intentando enviar email a: {to_email}")
            
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
            message["To"] = to_email

            text_part = MIMEText(body, "plain", "utf-8")
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2 style="color: #2c5282;">RioCaja Smart</h2>
                        {body.replace(chr(10), '<br>')}
                        <hr style="margin: 20px 0; border: none; border-top: 1px solid #eee;">
                        <p style="font-size: 12px; color: #666;">
                            Este es un mensaje automático, por favor no responder a este email.
                        </p>
                    </div>
                </body>
            </html>
            """
            html_part = MIMEText(html_body, "html", "utf-8")

            message.attach(text_part)
            message.attach(html_part)

            context = ssl.create_default_context()
            
            with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
                if MAIL_STARTTLS:
                    server.starttls(context=context)
                
                server.login(MAIL_USERNAME, MAIL_PASSWORD)
                server.send_message(message)
                
            logger.info(f"Email enviado exitosamente a: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error al enviar email a {to_email}: {str(e)}")
            return False

    async def request_password_reset(self, email: str) -> Dict[str, any]:
        """Solicitar código de recuperación de contraseña"""
        try:
            self._ensure_connection()
            logger.info(f"Procesando solicitud de reset para: {email}")
            
            user = self.users.find_one({"email": email})
            if not user:
                logger.warning(f"Intento de reset para email no registrado: {email}")
                return {
                    "success": True,
                    "message": "Si el email está registrado, recibirás un código de recuperación."
                }

            existing_request = self.reset_codes.find_one({
                "email": email,
                "expires_at": {"$gt": datetime.utcnow()}
            })

            if existing_request:
                logger.info(f"Ya existe solicitud activa para: {email}")
                return {
                    "success": True,
                    "message": "Ya tienes una solicitud activa. Revisa tu email o espera unos minutos."
                }

            reset_code = self._generate_reset_code()
            expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_EXPIRE_MINUTES)

            reset_data = {
                "email": email,
                "user_id": str(user["_id"]),
                "code": reset_code,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
                "attempts": 0,
                "used": False
            }

            self.reset_codes.insert_one(reset_data)

            subject = "RioCaja Smart - Código de Recuperación de Contraseña"
            body = f"""
Hola {user.get('nombre', 'Usuario')},

Has solicitado recuperar tu contraseña en RioCaja Smart.

Tu código de recuperación es: {reset_code}

Este código:
- Es válido por {RESET_CODE_EXPIRE_MINUTES} minutos
- Solo puede usarse una vez
- Expira el {expires_at.strftime('%d/%m/%Y a las %H:%M')}

Si no solicitaste este cambio, puedes ignorar este mensaje.

Saludos,
Equipo RioCaja Smart
            """

            email_sent = self._send_email(to_email, subject, body)
            
            if email_sent:
                logger.info(f"Código de reset enviado a: {email}")
                return {
                    "success": True,
                    "message": "Código de recuperación enviado a tu email."
                }
            else:
                logger.error(f"Error enviando email a: {email}")
                return {
                    "success": False,
                    "message": "Error al enviar el código. Intenta más tarde."
                }

        except Exception as e:
            logger.error(f"Error en request_password_reset: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    def verify_reset_code(self, email: str, code: str) -> Dict[str, any]:
        """Verificar código de recuperación"""
        try:
            self._ensure_connection()
            logger.info(f"Verificando código para: {email}")
            
            reset_request = self.reset_codes.find_one({
                "email": email,
                "code": code,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            if not reset_request:
                logger.warning(f"Código inválido para: {email}")
                return {
                    "success": False,
                    "message": "Código inválido o expirado."
                }

            logger.info(f"Código verificado exitosamente para: {email}")
            return {
                "success": True,
                "message": "Código verificado. Puedes cambiar tu contraseña.",
                "reset_id": str(reset_request["_id"])
            }

        except Exception as e:
            logger.error(f"Error en verify_reset_code: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    async def reset_password(self, email: str, code: str, new_password: str) -> Dict[str, any]:
        """Cambiar contraseña usando código de verificación"""
        try:
            self._ensure_connection()
            logger.info(f"Ejecutando reset de contraseña para: {email}")
            
            reset_request = self.reset_codes.find_one({
                "email": email,
                "code": code,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            if not reset_request:
                logger.warning(f"Código inválido para reset de: {email}")
                return {
                    "success": False,
                    "message": "Código inválido o expirado."
                }

            user = self.users.find_one({"email": email})
            if not user:
                logger.error(f"Usuario no encontrado para reset: {email}")
                return {
                    "success": False,
                    "message": "Usuario no encontrado."
                }

            hashed_password = hash_password(new_password)
            
            self.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "password_hash": hashed_password,
                        "password_changed_at": datetime.utcnow()
                    }
                }
            )

            self.reset_codes.update_one(
                {"_id": reset_request["_id"]},
                {"$set": {"used": True, "used_at": datetime.utcnow()}}
            )

            subject = "RioCaja Smart - Contraseña Cambiada"
            body = f"""
Hola {user.get('nombre', 'Usuario')},

Tu contraseña ha sido cambiada exitosamente.

Detalles del cambio:
- Fecha: {datetime.utcnow().strftime('%d/%m/%Y a las %H:%M')}
- Email: {email}

Si no realizaste este cambio, contacta inmediatamente con el administrador.

Saludos,
Equipo RioCaja Smart
            """

            self._send_email(email, subject, body)

            logger.info(f"Contraseña cambiada exitosamente para: {email}")
            return {
                "success": True,
                "message": "Contraseña cambiada exitosamente."
            }

        except Exception as e:
            logger.error(f"Error en reset_password: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    def get_reset_stats(self, email: str) -> Dict[str, any]:
        """Obtener estadísticas de intentos de reset"""
        try:
            self._ensure_connection()
            
            active_request = self.reset_codes.find_one({
                "email": email,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            if active_request:
                return {
                    "email": email,
                    "has_active_request": True,
                    "attempts_remaining": max(0, 3 - active_request.get("attempts", 0)),
                    "expires_at": active_request["expires_at"],
                    "last_request_at": active_request["created_at"]
                }
            else:
                return {
                    "email": email,
                    "has_active_request": False,
                    "attempts_remaining": 3,
                    "expires_at": None,
                    "last_request_at": None
                }

        except Exception as e:
            logger.error(f"Error en get_reset_stats: {str(e)}")
            return {
                "email": email,
                "has_active_request": False,
                "attempts_remaining": 0,
                "expires_at": None,
                "last_request_at": None
            }

    def cleanup_expired_codes(self) -> int:
        """Limpiar códigos expirados"""
        try:
            self._ensure_connection()
            
            result = self.reset_codes.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            
            deleted_count = result.deleted_count
            logger.info(f"Códigos expirados eliminados: {deleted_count}")
            return deleted_count

        except Exception as e:
            logger.error(f"Error en cleanup_expired_codes: {str(e)}")
            return 0