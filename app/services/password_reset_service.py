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
from app.utils.security import hash_password

logger = logging.getLogger(__name__)

class PasswordResetService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para password reset...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db["users"]
            self.reset_codes = self.db["password_reset_codes"]
            logger.info("Conexion exitosa a la base de datos")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def _generate_reset_code(self) -> str:
        return ''.join(random.choices(string.digits, k=RESET_CODE_LENGTH))

    def _send_email(self, to_email: str, subject: str, body: str) -> bool:
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
                            Este es un mensaje automatico, por favor no responder a este email.
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
        try:
            logger.info(f"Procesando solicitud de reset para: {email}")
            
            user = self.users.find_one({"email": email})
            if not user:
                logger.warning(f"Intento de reset para email no registrado: {email}")
                return {
                    "success": True,
                    "message": "Si el email esta registrado, recibiras un codigo de recuperacion."
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

            subject = "RioCaja Smart - Codigo de Recuperacion de Contrasena"
            body = f"""
Hola {user.get('nombre', 'Usuario')},

Has solicitado recuperar tu contrasena en RioCaja Smart.

Tu codigo de recuperacion es: {reset_code}

Este codigo:
- Es valido por {RESET_CODE_EXPIRE_MINUTES} minutos
- Solo puede usarse una vez
- Expira el {expires_at.strftime('%d/%m/%Y a las %H:%M')}

Si no solicitaste este cambio, puedes ignorar este mensaje.

Saludos,
Equipo RioCaja Smart
            """

            email_sent = self._send_email(email, subject, body)
            
            if email_sent:
                logger.info(f"Codigo de reset enviado a: {email}")
                return {
                    "success": True,
                    "message": "Codigo de recuperacion enviado a tu email."
                }
            else:
                self.reset_codes.delete_one({"email": email, "code": reset_code})
                logger.error(f"Fallo envio de email para: {email}")
                return {
                    "success": False,
                    "message": "Error al enviar el email. Intenta nuevamente."
                }

        except Exception as e:
            logger.error(f"Error en request_password_reset: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    def verify_reset_code(self, email: str, code: str) -> Dict[str, any]:
        try:
            logger.info(f"Verificando codigo para: {email}")
            
            reset_request = self.reset_codes.find_one({
                "email": email,
                "code": code,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            if not reset_request:
                logger.warning(f"Codigo invalido o expirado para: {email}")
                return {
                    "success": False,
                    "message": "Codigo invalido o expirado."
                }

            self.reset_codes.update_one(
                {"_id": reset_request["_id"]},
                {"$inc": {"attempts": 1}}
            )

            logger.info(f"Codigo verificado exitosamente para: {email}")
            return {
                "success": True,
                "message": "Codigo valido.",
                "reset_id": str(reset_request["_id"])
            }

        except Exception as e:
            logger.error(f"Error en verify_reset_code: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    async def reset_password(self, email: str, code: str, new_password: str) -> Dict[str, any]:
        try:
            logger.info(f"Ejecutando reset de contrasena para: {email}")
            
            reset_request = self.reset_codes.find_one({
                "email": email,
                "code": code,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            if not reset_request:
                logger.warning(f"Codigo invalido para reset de: {email}")
                return {
                    "success": False,
                    "message": "Codigo invalido o expirado."
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

            subject = "RioCaja Smart - Contrasena Cambiada"
            body = f"""
Hola {user.get('nombre', 'Usuario')},

Tu contrasena ha sido cambiada exitosamente.

Detalles del cambio:
- Fecha: {datetime.utcnow().strftime('%d/%m/%Y a las %H:%M')}
- Email: {email}

Si no realizaste este cambio, contacta inmediatamente con el administrador.

Saludos,
Equipo RioCaja Smart
            """

            self._send_email(email, subject, body)

            logger.info(f"Contrasena cambiada exitosamente para: {email}")
            return {
                "success": True,
                "message": "Contrasena cambiada exitosamente."
            }

        except Exception as e:
            logger.error(f"Error en reset_password: {str(e)}")
            return {
                "success": False,
                "message": "Error interno del servidor."
            }

    def get_reset_stats(self, email: str) -> Dict[str, any]:
        try:
            active_request = self.reset_codes.find_one({
                "email": email,
                "expires_at": {"$gt": datetime.utcnow()},
                "used": False
            })

            last_request = self.reset_codes.find_one(
                {"email": email},
                sort=[("created_at", -1)]
            )

            return {
                "email": email,
                "has_active_request": active_request is not None,
                "attempts_remaining": 3 - (active_request.get("attempts", 0) if active_request else 0),
                "expires_at": active_request.get("expires_at") if active_request else None,
                "last_request_at": last_request.get("created_at") if last_request else None
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

    def cleanup_expired_codes(self):
        try:
            result = self.reset_codes.delete_many({
                "expires_at": {"$lt": datetime.utcnow()}
            })
            logger.info(f"Eliminados {result.deleted_count} codigos expirados")
        except Exception as e:
            logger.error(f"Error en cleanup_expired_codes: {str(e)}")