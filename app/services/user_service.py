# app/services/user_service.py - VERSIÓN ARREGLADA COMPLETA
import logging
import uuid
import os
from datetime import datetime
from typing import Optional, List, Dict, Any
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME
from app.services.crypto_service import hash_password, verify_password

def clean_objectid_fields(data):
    """
    Recursivamente convierte todos los ObjectId a string en un diccionario o lista
    """
    if isinstance(data, list):
        return [clean_objectid_fields(item) for item in data]
    elif isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            if isinstance(value, ObjectId):
                cleaned[key] = str(value)
            elif isinstance(value, (dict, list)):
                cleaned[key] = clean_objectid_fields(value)
            else:
                cleaned[key] = value
        return cleaned
    elif isinstance(data, ObjectId):
        return str(data)
    else:
        return data

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        try:
            self.client = MongoClient(
                MONGO_URI,
                connect=False,
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
            self.collection = self.users  # Para compatibilidad
            
            try:
                self.client.admin.command('ping')
                logger.info("✅ Conexión a MongoDB exitosa")
            except Exception as ping_error:
                logger.warning(f"⚠️ No se pudo hacer ping a MongoDB: {ping_error}")
                
        except Exception as e:
            logger.error(f"❌ Error al inicializar conexión MongoDB: {e}")
            self.client = None
            self.db = None
            self.users = None
            self.collection = None

    def change_user_role(self, user_id: str, new_role: str, changed_by: str = None) -> bool:
        """Cambiar rol de usuario"""
        try:
            self._ensure_connection()
            
            # Roles válidos en tu sistema
            valid_roles = ["admin", "asesor", "cnb"]
            if new_role not in valid_roles:
                logger.error(f"Rol inválido: {new_role}")
                return False
            
            # Verificar que el usuario existe
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # Datos de actualización
            update_data = {
                "rol": new_role,
                "fecha_cambio_rol": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            # Si es admin o asesor, marcar perfil como completo y asignar códigos especiales
            if new_role in ["admin", "asesor"]:
                update_data.update({
                    "perfil_completo": True,
                    "estado": "activo",
                    "codigo_corresponsal": new_role.upper(),
                    "nombre_local": "Administración" if new_role == "admin" else "Asesoría"
                })
            
            # Registrar quién hizo el cambio
            if changed_by:
                update_data["rol_cambiado_por"] = changed_by
            
            # Actualizar en la base de datos
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Rol de usuario cambiado a '{new_role}' para usuario: {user_id}")
            else:
                logger.warning(f"No se pudo cambiar rol de usuario: {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error cambiando rol de usuario: {e}")
            return False

    def _ensure_connection(self):
        """Asegurar que la conexión a MongoDB está activa"""
        try:
            if self.client is None:
                logger.info("Reconectando a MongoDB...")
                self.client = MongoClient(MONGO_URI)
                self.db = self.client[DATABASE_NAME]
                self.users = self.db.users
            
            # ✅ CORRECCIÓN: Verificar la conexión con ping
            self.client.admin.command('ping')
            logger.debug("Conexión a MongoDB verificada exitosamente")
            
        except Exception as e:
            logger.error(f"Error en conexión a MongoDB: {e}")
            # Reintentar una vez
            try:
                self.client = MongoClient(MONGO_URI)
                self.db = self.client[DATABASE_NAME]
                self.users = self.db.users
                self.client.admin.command('ping')
                logger.info("Reconexión a MongoDB exitosa")
            except Exception as retry_error:
                logger.error(f"Error en reintento de conexión: {retry_error}")
                raise Exception(f"No se pudo conectar a MongoDB: {retry_error}")

    def register_user(self, nombre: str, email: str, password: str, rol: str = "cnb"):
        try:
            self._ensure_connection()
            
            if self.users.find_one({"email": email}):
                raise ValueError("El email ya está registrado")
            
            user_data = {
                "nombre": nombre,
                "email": email,
                "password_hash": hash_password(password),
                "rol": rol,
                "estado": "pendiente",
                "fecha_registro": datetime.utcnow(),
                "perfil_completo": False,
                "acepto_terminos": True,
                "fecha_acepta_terminos": datetime.utcnow()
            }
        
            result = self.users.insert_one(user_data)
            logger.info(f"Usuario registrado: {email}")

            # --- Envío de emails de confirmación y notificación a admins ---
            try:
                from app.services.email_service import EmailService
                email_service = EmailService()
                
                # Enviar email de confirmación al usuario
                email_service.send_registration_confirmation(
                    user_email=email.lower(),
                    user_name=nombre
                )
                logger.info(f"✅ Email de confirmación enviado a: {email}")
                
                # Enviar notificación a administradores
                admin_users = self.users.find({"rol": "admin"})
                for admin in admin_users:
                    admin_email = admin.get('email')
                    if admin_email:
                        email_service.send_admin_new_user_notification(
                            admin_email=admin_email,
                            user_data={
                                'nombre': nombre,
                                'email': email,
                                'rol': rol
                            }
                        )
                        logger.info(f"✅ Notificación enviada al admin: {admin_email}")
                        
            except Exception as email_error:
                logger.warning(f"⚠️ Error enviando emails de registro: {email_error}")
                # No fallar el registro por error de email

            return {"message": "Usuario registrado exitosamente", "user_id": str(result.inserted_id)}
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Error registrando usuario: {e}")
            raise Exception("Error interno del servidor")

    def authenticate_user(self, email: str, password: str):
        try:
            self._ensure_connection()
            
            user = self.users.find_one({"email": email})
            if not user:
                logger.info(f"Usuario no encontrado: {email}")
                return None
                
            if not verify_password(password, user["password_hash"]):
                logger.info(f"Contraseña incorrecta para: {email}")
                return None

            new_session_id = str(uuid.uuid4())
            
            self.users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "session_id": new_session_id,
                        "last_login": datetime.utcnow()
                    }
                }
            )
            
            user["session_id"] = new_session_id
            user["_id"] = str(user["_id"])
            
            logger.info(f"Autenticación exitosa: {email} con session: {new_session_id[:8]}...")
            return user
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            return None

def get_user_info(self, user_id: str):
    """
    Obtener información del usuario INCLUYENDO session_id para middleware
    """
    try:
        self._ensure_connection()
        
        user = self.users.find_one({"_id": ObjectId(user_id)})
        if user:
            # Limpiar datos sensibles
            user.pop("password_hash", None)
            # user.pop("session_id", None)  # ← COMENTADA
            
            # Convertir ObjectIds a string
            cleaned_user = clean_objectid_fields(user)
            return cleaned_user
        return None
        
    except Exception as e:
        logger.error(f"Error obteniendo info del usuario {user_id}: {e}")
        return None
            
        except Exception as e:
            logger.error(f"Error obteniendo info del usuario {user_id}: {e}")
            return None

    def get_user_public_info(self, user_id: str):
        """
        Obtener información pública del usuario (sin session_id ni datos sensibles)
        """
        try:
             self._ensure_connection()
        
             user = self.users.find_one({"_id": ObjectId(user_id)})
             if user:
                 # Eliminar TODOS los datos sensibles para uso público
                 user.pop("password_hash", None)
                 user.pop("session_id", None)
            
                 # Convertir ObjectIds a string
                 cleaned_user = clean_objectid_fields(user)
                 return cleaned_user
             return None
        
         except Exception as e:
             logger.error(f"Error obteniendo info pública del usuario {user_id}: {e}")
             return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        try:
            self._ensure_connection()
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                # Limpiar datos sensibles
                user.pop("password_hash", None)
                user.pop("session_id", None)
                
                # Convertir ObjectIds a string
                cleaned_user = clean_objectid_fields(user)
                return cleaned_user
            return None
        except Exception as e:
            logger.error(f"Error obteniendo usuario por ID {user_id}: {e}")
            return None

    def approve_user_with_code(self, user_id: str, codigo_corresponsal: str, approved_by: str) -> bool:
        try:
            self._ensure_connection()
            
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
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
                # --- Envío de email de aprobación ---
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    
                    # Obtener datos del usuario actualizado
                    updated_user = self.users.find_one({"_id": ObjectId(user_id)})
                    if updated_user:
                        email_service.send_account_approved_notification(
                            user_email=updated_user['email'],
                            user_name=updated_user['nombre'],
                            codigo_corresponsal=codigo_corresponsal
                        )
                        logger.info(f"✅ Email de aprobación enviado a: {updated_user['email']}")
                        
                except Exception as email_error:
                    logger.warning(f"⚠️ Error enviando email de aprobación: {email_error}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error aprobando usuario: {e}")
            return False

    def complete_user_profile_simple(self, user_id: str, nombre_local: str) -> bool:
        try:
            self._ensure_connection()
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "nombre_local": nombre_local,
                        "perfil_completo": True,
                        "fecha_perfil_completado": datetime.utcnow()
                    }
                }
            )
            success = result.modified_count > 0
            if success:
                logger.info(f"Perfil completado para usuario {user_id}")
            return success
        except Exception as e:
            logger.error(f"Error completando perfil: {e}")
            return False

    def get_pending_users(self) -> List[dict]:
        try:
            self._ensure_connection()
            
            users = list(self.users.find({"estado": "pendiente"}))
            processed_users = []
            
            for user in users:
                # Limpiar datos sensibles
                user.pop("password_hash", None)
                user.pop("session_id", None)
                
                # Convertir TODOS los ObjectIds a string
                cleaned_user = clean_objectid_fields(user)
                processed_users.append(cleaned_user)
                
            return processed_users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios pendientes: {e}")
            return []

    def get_all_users(self) -> List[dict]:
        """Obtener todos los usuarios del sistema"""
        try:
            self._ensure_connection()
            
            logger.info("Intentando obtener todos los usuarios de la base de datos")
            
            if self.users is None:
                logger.error("La colección 'users' no está inicializada")
                return []
            
            try:
                users_cursor = self.users.find({})
                users = list(users_cursor)
                logger.info(f"Se encontraron {len(users)} usuarios en la base de datos")
                
            except Exception as db_error:
                logger.error(f"Error al consultar la base de datos: {db_error}")
                return []
            
            processed_users = []
            for user in users:
                try:
                    if "_id" not in user:
                        logger.warning(f"Usuario sin _id encontrado: {user}")
                        continue
                    
                    # Limpiar datos sensibles ANTES de convertir ObjectIds
                    user.pop("password_hash", None)
                    user.pop("session_id", None)
                    
                    # Convertir TODOS los ObjectIds a string recursivamente
                    cleaned_user = clean_objectid_fields(user)
                    
                    processed_users.append(cleaned_user)
                    
                except Exception as user_error:
                    logger.error(f"Error procesando usuario individual: {user_error}")
                    continue
            
            logger.info(f"Se procesaron exitosamente {len(processed_users)} usuarios")
            return processed_users
            
        except Exception as e:
            logger.error(f"Error crítico obteniendo todos los usuarios: {e}")
            return []

    def mark_admin_profile_complete(self, user_id: str) -> bool:
        """Marcar perfil de admin/asesor como completo automáticamente"""
        try:
            self._ensure_connection()
            
            if not ObjectId.is_valid(user_id):
                return False
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "perfil_completo": True,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Perfil de admin marcado como completo: {user_id}")
                return True
            else:
                logger.warning(f"⚠️  No se pudo marcar perfil como completo: {user_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error marcando perfil admin como completo: {e}")
            return False

    def create_admin_user(self, admin_data: dict) -> str:
        """Crear usuario administrador directamente"""
        try:
            self._ensure_connection()
            
            # Validar datos requeridos
            required_fields = ["nombre", "email", "password"]
            for field in required_fields:
                if not admin_data.get(field):
                    raise ValueError(f"Campo requerido faltante: {field}")
            
            # Verificar si el email ya existe
            existing_user = self.users.find_one({"email": admin_data["email"].lower()})
            if existing_user:
                raise ValueError("Email ya registrado")
            
            # Hash de la contraseña
            password_hash = hash_password(admin_data["password"])
            
            # Crear documento de usuario admin
            user_doc = {
                "nombre": admin_data["nombre"],
                "email": admin_data["email"].lower(),
                "password_hash": password_hash,
                "rol": "admin",
                "estado": "activo",  # Admin se activa inmediatamente
                "perfil_completo": True,  # Admin no necesita completar perfil
                "fecha_registro": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "approved_at": datetime.utcnow(),
                "approved_by": "system",
                "codigo_corresponsal": "ADMIN",  # Admin tiene código especial
                "nombre_local": "Administración",  # Admin tiene local especial
            }
            
            # Insertar en la base de datos
            result = self.users.insert_one(user_doc)
            
            if result.inserted_id:
                logger.info(f"✅ Usuario admin creado: {admin_data['email']}")
                return str(result.inserted_id)
            else:
                raise Exception("Error al insertar en la base de datos")
                
        except ValueError as e:
            logger.error(f"❌ Error de validación creando admin: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error creando usuario admin: {e}")
            raise Exception("Error interno al crear administrador")

    def create_first_admin(self, admin_data: dict) -> bool:
        """Crear el primer administrador del sistema"""
        try:
            self._ensure_connection()
            
            # Verificar que no existan admins
            admin_count = self.users.count_documents({"rol": "admin"})
            if admin_count > 0:
                raise ValueError("Ya existe un administrador en el sistema")
            
            # Crear admin usando la función existente
            admin_id = self.create_admin_user(admin_data)
            
            if admin_id:
                logger.info(f"✅ Primer administrador creado exitosamente: {admin_id}")
                return True
            else:
                return False
                
        except Exception as e:
            logger.error(f"❌ Error creando primer admin: {e}")
            raise

    def count_admins(self) -> int:
        """Contar cuántos administradores existen"""
        try:
            self._ensure_connection()
            return self.users.count_documents({"rol": "admin"})
        except Exception as e:
            logger.error(f"❌ Error contando admins: {e}")
            return 0

    def make_user_admin(self, email: str, secret_key: str = None) -> bool:
        """Convertir usuario existente en administrador"""
        try:
            self._ensure_connection()
            
            # Si se proporciona secret_key, validarla
            if secret_key:
                expected_key = os.getenv("ADMIN_SECRET_KEY", "riocaja2024")
                if secret_key != expected_key:
                    logger.warning(f"⚠️  Intento de crear admin con clave incorrecta")
                    return False
            
            # Buscar usuario por email
            user = self.users.find_one({"email": email.lower()})
            if not user:
                logger.warning(f"⚠️  Usuario no encontrado para hacer admin: {email}")
                return False
            
            # Actualizar usuario a admin
            result = self.users.update_one(
                {"email": email.lower()},
                {
                    "$set": {
                        "rol": "admin",
                        "estado": "activo",
                        "perfil_completo": True,  # Admin no necesita completar perfil
                        "codigo_corresponsal": "ADMIN",
                        "nombre_local": "Administración",
                        "updated_at": datetime.utcnow(),
                        "promoted_to_admin_at": datetime.utcnow()
                    }
                }
            )
            
            if result.modified_count > 0:
                logger.info(f"✅ Usuario convertido a admin: {email}")
                return True
            else:
                logger.warning(f"⚠️  No se pudo convertir usuario a admin: {email}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Error convirtiendo usuario a admin: {e}")
            return False

    def make_user_asesor(self, email: str) -> bool:
        try:
            self._ensure_connection()
            
            result = self.users.update_one(
                {"email": email},
                {
                    "$set": {
                        "rol": "asesor",
                        "estado": "activo",
                        "perfil_completo": True,
                        "codigo_corresponsal": "ASESOR",
                        "nombre_local": "Asesoría",
                        "fecha_asesor": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario convertido en asesor: {email}")
            return success
            
        except Exception as e:
            logger.error(f"Error convirtiendo usuario en asesor: {e}")
            return False

    def update_user_session(self, user_id: str, new_session_id: str):
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

    def reject_user(self, user_id: str, reason: str = None, rejected_by: str = None) -> bool:
        try:
            self._ensure_connection()
            
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "estado": "rechazado",
                        "fecha_rechazo": datetime.utcnow(),
                        "motivo_rechazo": reason,
                        "rechazado_por": rejected_by
                    }
                }
            )
            
            if result.modified_count > 0:
                # --- Envío de email de rechazo ---
                try:
                    from app.services.email_service import EmailService
                    email_service = EmailService()
                    
                    email_service.send_account_rejected_notification(
                        user_email=user_data['email'],
                        user_name=user_data['nombre'],
                        reason=reason
                    )
                    logger.info(f"✅ Email de rechazo enviado a: {user_data['email']}")
                    
                except Exception as email_error:
                    logger.warning(f"⚠️ Error enviando email de rechazo: {email_error}")
                
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error rechazando usuario: {e}")
            return False

    def change_user_state(self, user_id: str, new_state: str, reason: str = None, changed_by: str = None) -> bool:
        try:
            self._ensure_connection()
            
            valid_states = ["activo", "inactivo", "suspendido", "pendiente", "rechazado"]
            if new_state not in valid_states:
                logger.error(f"Estado inválido: {new_state}")
                return False
            
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            update_data = {
                "estado": new_state,
                f"fecha_{new_state}": datetime.utcnow()
            }
            
            if reason:
                update_data["motivo_cambio"] = reason
            if changed_by:
                update_data["cambiado_por"] = changed_by
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Estado de usuario cambiado a {new_state}: {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error cambiando estado de usuario: {e}")
            return False

    def delete_user(self, user_id: str, reason: str = None, deleted_by: str = None) -> bool:
        try:
            self._ensure_connection()
            
            user_data = self.users.find_one({"_id": ObjectId(user_id)})
            if not user_data:
                logger.error(f"Usuario no encontrado: {user_id}")
                return False
            
            # Eliminar usuario
            result = self.users.delete_one({"_id": ObjectId(user_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Usuario eliminado: {user_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error eliminando usuario: {e}")
            return False

    def get_users_by_role(self, role: str) -> List[Dict[str, Any]]:
        try:
            self._ensure_connection()
            
            users = list(self.users.find({"rol": role}))
            processed_users = []
            
            for user in users:
                # Limpiar datos sensibles
                user.pop("password_hash", None)
                user.pop("session_id", None)
                
                # Convertir ObjectIds a string
                cleaned_user = clean_objectid_fields(user)
                processed_users.append(cleaned_user)
                
            return processed_users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios por rol {role}: {e}")
            return []

    def get_user_by_email(self, email: str):
        try:
            self._ensure_connection()
            
            user = self.users.find_one({"email": email})
            if user:
                # Limpiar datos sensibles
                user.pop("password_hash", None)
                user.pop("session_id", None)
                
                # Convertir ObjectIds a string
                cleaned_user = clean_objectid_fields(user)
                return cleaned_user
            return None
            
        except Exception as e:
            logger.error(f"Error al obtener usuario por email {email}: {e}")
            return None

    def update_password(self, user_id: str, new_password: str):
        try:
            self._ensure_connection()
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "password_hash": hash_password(new_password),
                        "password_updated_at": datetime.utcnow()
                    },
                    "$unset": {
                        "session_id": ""
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Contraseña actualizada para usuario {user_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error al actualizar contraseña del usuario {user_id}: {e}")
            return False

    def close_connection(self):
        try:
            if self.client:
                self.client.close()
                logger.info("Conexión a MongoDB cerrada")
        except Exception as e:
            logger.error(f"Error al cerrar conexión MongoDB: {e}")
    
    def update_terms_acceptance(self, user_id: str, acepta: bool) -> bool:
        """
        Actualizar aceptación de términos y condiciones para un usuario
        
        Args:
            user_id: ID del usuario
            acepta: True si acepta, False si no acepta
        
        Returns:
            bool: True si se actualizó correctamente
        """
        try:
            self._ensure_connection()
            
            update_data = {
                "acepto_terminos": acepta,
                "updated_at": datetime.utcnow()
            }
            
            # Si acepta, guardar la fecha
            if acepta:
                update_data["fecha_acepta_terminos"] = datetime.utcnow()
            
            result = self.users.update_one(
                {"_id": user_id},
                {"$set": update_data}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Términos {'aceptados' if acepta else 'rechazados'} para usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error actualizando términos para usuario {user_id}: {e}")
            return False

    def check_terms_acceptance(self, user_id: str) -> dict:
        """
        Verificar si un usuario ha aceptado los términos y condiciones
        
        Args:
            user_id: ID del usuario
        
        Returns:
            dict: Estado de aceptación de términos
        """
        try:
            self._ensure_connection()
            
            user = self.users.find_one(
                {"_id": user_id},
                {"acepto_terminos": 1, "fecha_acepta_terminos": 1}
            )
            
            if not user:
                return {"error": "Usuario no encontrado"}
            
            return {
                "acepto_terminos": user.get("acepto_terminos", False),
                "fecha_acepta_terminos": user.get("fecha_acepta_terminos"),
                "necesita_aceptar": not user.get("acepto_terminos", False)
            }
            
        except Exception as e:
            logger.error(f"Error verificando términos para usuario {user_id}: {e}")
            return {"error": "Error interno"}