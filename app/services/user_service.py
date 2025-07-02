# app/services/user_service.py - VERSIÓN COMPLETA Y CORREGIDA
import logging
import uuid
from app.database import db
from datetime import datetime
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME
from app.services.crypto_service import hash_password, verify_password
from werkzeug.security import generate_password_hash, check_password_hash


logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        try:
            # CONFIGURACIÓN DE CONEXIÓN MÁS ROBUSTA
            self.client = MongoClient(
                MONGO_URI,
                connect=False,  # No conectar inmediatamente
                serverSelectionTimeoutMS=30000,  # 30 segundos
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
            
            # Probar conexión
            try:
                self.client.admin.command('ping')
                logger.info("✅ Conexión a MongoDB exitosa")
            except Exception as ping_error:
                logger.warning(f"⚠️ No se pudo hacer ping a MongoDB: {ping_error}")
                # Continuar sin fallar, la conexión se probará en la primera operación
                
        except Exception as e:
            logger.error(f"❌ Error al inicializar conexión MongoDB: {e}")
            # No hacer raise aquí, permitir que el servicio se inicialice
            self.client = None
            self.db = None
            self.users = None

    def _ensure_connection(self):
        """Asegurar que la conexión esté disponible antes de usar"""
        if self.client is None or self.db is None or self.users is None:
            logger.error("Conexión a MongoDB no está inicializada")
            raise Exception("Error de conexión a la base de datos")

    def register_user(self, nombre: str, email: str, password: str, rol: str = "cnb") -> dict:
        """Registrar nuevo usuario CON notificaciones email"""
        try:
            # Verificar si el usuario ya existe
            if self.collection.find_one({"email": email}):
                raise ValueError("El usuario ya existe")
            
            # Crear nuevo usuario
            user_data = {
                "_id": str(ObjectId()),
                "nombre": nombre,
                "email": email,
                "password_hash": generate_password_hash(password),
                "rol": rol,
                "estado": "pendiente",
                "fecha_registro": datetime.utcnow(),
                "perfil_completo": False,
                "session_id": str(uuid.uuid4()),
                "intentos_fallidos": 0
            }
            
            # Insertar usuario en la base de datos
            result = self.collection.insert_one(user_data)
            
            # NUEVO: Enviar notificaciones por email
            try:
                from app.services.email_service import EmailService
                email_service = EmailService()
                
                # 1. Email de confirmación al usuario
                email_service.send_registration_confirmation(
                    user_email=email,
                    user_name=nombre
                )
                logger.info(f"Email de confirmación enviado a: {email}")
                
                # 2. Notificación a asesores sobre nuevo usuario pendiente
                advisor_emails = email_service.get_advisor_emails()
                if advisor_emails:
                    email_service.send_new_user_notification_to_advisors(
                        user_data={
                            'nombre': nombre,
                            'email': email,
                            'rol': rol
                        },
                        advisor_emails=advisor_emails
                    )
                    logger.info(f"Notificación enviada a {len(advisor_emails)} asesores")
                else:
                    logger.warning("No se encontraron emails de asesores para notificar")
                    
            except Exception as email_error:
                logger.error(f"Error enviando emails de registro: {email_error}")
                # No fallar el registro por errores de email
            
            return {
                "message": "Usuario registrado exitosamente. Espere la aprobación del administrador.",
                "user_id": str(result.inserted_id)
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error registrando usuario: {e}")
            raise Exception("Error interno del servidor")

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Autenticar usuario (sin cambios)"""
        try:
            user = self.collection.find_one({"email": email})
            if user and check_password_hash(user["password_hash"], password):
                # Actualizar session_id en cada login
                new_session_id = str(uuid.uuid4())
                self.collection.update_one(
                    {"_id": user["_id"]},
                    {"$set": {"session_id": new_session_id}}
                )
                user["session_id"] = new_session_id
                return user
            return None
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return None

    def get_user_info(self, user_id: str) -> Optional[dict]:
        """Obtener información de un usuario específico"""
        try:
            user = self.collection.find_one({"_id": user_id})
            if user:
                user.pop("password_hash", None)
            return user
        except Exception as e:
            logger.error(f"Error obteniendo info del usuario {user_id}: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        """Obtener usuario por ID"""
        try:
            return self.collection.find_one({"_id": user_id})
        except Exception as e:
            logger.error(f"Error obteniendo usuario por ID {user_id}: {e}")
            return None

    def approve_user_with_code(self, user_id: str, codigo_corresponsal: str, approved_by: str) -> bool:
        """Aprobar usuario con código de corresponsal CON notificación email"""
        try:
            # Obtener datos del usuario antes de actualizar
            user_data = self.collection.find_one({"_id": user_id})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # Actualizar usuario
            result = self.collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "estado": "activo",
                        "codigo_corresponsal": codigo_corresponsal,
                        "aprobado_por": approved_by,
                        "fecha_aprobacion": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                # NUEVO: Enviar email de aprobación
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    
                    email_service.send_account_approved_notification(
                        user_email=user_data['email'],
                        user_name=user_data['nombre'],
                        codigo_corresponsal=codigo_corresponsal
                    )
                    logger.info(f"Email de aprobación enviado a: {user_data['email']}")
                    
                except Exception as email_error:
                    logger.error(f"Error enviando email de aprobación: {email_error}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error aprobando usuario: {e}")
            return False

    def complete_user_profile_simple(self, user_id: str, nombre_local: str) -> bool:
        """Completar perfil simple"""
        try:
            result = self.collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "nombre_local": nombre_local,
                        "perfil_completo": True,
                        "fecha_perfil_completado": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error completando perfil: {e}")
            return False

    def get_pending_users(self) -> List[dict]:
        """Obtener usuarios pendientes"""
        try:
            users = list(self.collection.find({"estado": "pendiente"}))
            for user in users:
                user.pop("password_hash", None)
            return users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios pendientes: {e}")
            return []

    def get_all_users(self) -> List[dict]:
        """Obtener todos los usuarios"""
        try:
            users = list(self.collection.find({}))
            for user in users:
                user.pop("password_hash", None)
            return users
        except Exception as e:
            logger.error(f"Error obteniendo todos los usuarios: {e}")
            return []

    def create_admin_user(self, admin_data: dict) -> str:
        """Crear usuario administrador"""
        try:
            if self.collection.find_one({"email": admin_data["email"]}):
                raise ValueError("El administrador ya existe")
            
            user_data = {
                "_id": str(ObjectId()),
                "nombre": admin_data["nombre"],
                "email": admin_data["email"],
                "password_hash": generate_password_hash(admin_data["password"]),
                "rol": "admin",
                "estado": "activo",
                "fecha_registro": datetime.utcnow(),
                "perfil_completo": True,
                "session_id": str(uuid.uuid4()),
                "creado_por": admin_data.get("creado_por", "sistema")
            }
            
            result = self.collection.insert_one(user_data)
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error creando admin: {e}")
            raise

    def create_first_admin(self, admin_data: dict) -> str:
        """Crear primer administrador del sistema"""
        try:
            admin_data["creado_por"] = "setup_inicial"
            return self.create_admin_user(admin_data)
        except Exception as e:
            logger.error(f"Error creando primer admin: {e}")
            raise

    def count_admins(self) -> int:
        """Contar administradores"""
        try:
            return self.collection.count_documents({"rol": "admin"})
        except Exception as e:
            logger.error(f"Error contando admins: {e}")
            return 0

    def make_user_admin(self, email: str, secret_key: str) -> bool:
        """Convertir usuario en admin (setup inicial)"""
        try:
            # Verificar clave secreta (implementar según necesidades)
            if secret_key != "admin_setup_key_2025":
                return False
            
            result = self.collection.update_one(
                {"email": email},
                {
                    "$set": {
                        "rol": "admin",
                        "estado": "activo",
                        "perfil_completo": True,
                        "fecha_admin": datetime.utcnow()
                    }
                }
            )
            return result.modified_count > 0
        except Exception as e:
            logger.error(f"Error convirtiendo usuario en admin: {e}")
            return False

    def change_user_state(self, user_id: str, new_state: str):
        """Cambiar estado de un usuario"""
        try:
            self._ensure_connection()
            
            # Validar que el usuario existe
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if not user:
                logger.warning(f"Usuario no encontrado: {user_id}")
                return False
            
            # Actualizar estado
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "estado": new_state,
                        "estado_actualizado_en": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Estado del usuario {user_id} cambiado a {new_state}")
            else:
                logger.warning(f"No se pudo cambiar estado del usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al cambiar estado del usuario {user_id}: {e}")
            return False

    def update_user_session(self, user_id: str, new_session_id: str):
        """Actualizar el session_id del usuario (esto cierra otras sesiones)"""
        try:
            self._ensure_connection()
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "session_id": new_session_id,
                        "last_login": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Session ID actualizado para usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar session del usuario {user_id}: {e}")
            return False

    def get_user_session_id(self, user_id: str):

        """Obtener el session_id actual del usuario"""
        try:
            self._ensure_connection()
            
            user = self.users.find_one(
                {"_id": ObjectId(user_id)}, 
                {"session_id": 1}
            )
            
            return user.get("session_id") if user else None
            
        except Exception as e:
            logger.error(f"Error al obtener session del usuario {user_id}: {e}")
            return None

    def reject_user(self, user_id: str, reason: str = None) -> bool:
        """Rechazar usuario CON notificación email"""
        try:
            # Obtener datos del usuario antes de actualizar
            user_data = self.collection.find_one({"_id": user_id})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # Actualizar estado
            result = self.collection.update_one(
                {"_id": user_id},
                {
                    "$set": {
                        "estado": "rechazado",
                        "fecha_rechazo": datetime.utcnow(),
                        "motivo_rechazo": reason
                    }
                }
            )
            
            if result.modified_count > 0:
                # NUEVO: Enviar email de rechazo
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    
                    email_service.send_account_rejected_notification(
                        user_email=user_data['email'],
                        user_name=user_data['nombre'],
                        reason=reason
                    )
                    logger.info(f"Email de rechazo enviado a: {user_data['email']}")
                    
                except Exception as email_error:
                    logger.error(f"Error enviando email de rechazo: {email_error}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error rechazando usuario: {e}")
            return False

    def change_user_state(self, user_id: str, new_state: str, reason: str = None, changed_by: str = None) -> bool:
        """Cambiar estado de usuario CON notificaciones email"""
        try:
            # Validar estados permitidos
            valid_states = ["activo", "inactivo", "suspendido", "pendiente", "rechazado"]
            if new_state not in valid_states:
                logger.error(f"Estado inválido: {new_state}")
                return False
            
            # Obtener datos del usuario antes de actualizar
            user_data = self.collection.find_one({"_id": user_id})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # Actualizar estado
            update_data = {
                "estado": new_state,
                f"fecha_{new_state}": datetime.utcnow()
            }
            
            if reason:
                update_data["motivo_cambio"] = reason
            if changed_by:
                update_data["cambiado_por"] = changed_by
            
            result = self.collection.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
            
            if result.modified_count > 0:
                # NUEVO: Enviar notificación email según el estado
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    
                    if new_state == "suspendido":
                        email_service.send_account_suspended_notification(
                            user_email=user_data['email'],
                            user_name=user_data['nombre'],
                            reason=reason
                        )
                    elif new_state == "inactivo":
                        email_service.send_account_deactivated_notification(
                            user_email=user_data['email'],
                            user_name=user_data['nombre'],
                            reason=reason
                        )
                    elif new_state == "rechazado":
                        email_service.send_account_rejected_notification(
                            user_email=user_data['email'],
                            user_name=user_data['nombre'],
                            reason=reason
                        )
                    
                    logger.info(f"Email de cambio de estado ({new_state}) enviado a: {user_data['email']}")
                    
                except Exception as email_error:
                    logger.error(f"Error enviando email de cambio de estado: {email_error}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error cambiando estado de usuario: {e}")
            return False

    def delete_user(self, user_id: str, reason: str = None, deleted_by: str = None) -> bool:
        """Eliminar usuario CON notificación email"""
        try:
            # Obtener datos del usuario antes de eliminar
            user_data = self.collection.find_one({"_id": user_id})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # NUEVO: Enviar email ANTES de eliminar
            try:
                from app.services.email_service import EmailService
                email_service = EmailService()
                
                email_service.send_account_deleted_notification(
                    user_email=user_data['email'],
                    user_name=user_data['nombre'],
                    reason=reason
                )
                logger.info(f"Email de eliminación enviado a: {user_data['email']}")
                
            except Exception as email_error:
                logger.error(f"Error enviando email de eliminación: {email_error}")
            
            # Eliminar usuario
            result = self.collection.delete_one({"_id": user_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return False

    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        """Obtener usuarios por rol"""
        try:
            users = list(self.collection.find({"rol": role}))
            return users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios por rol {role}: {e}")
            return []

