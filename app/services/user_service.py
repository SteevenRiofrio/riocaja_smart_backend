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

     def _ensure_connection(self):
         """Asegurar que la conexión a MongoDB está activa"""
    try:
        if self.client is None:
            logger.info("Reconectando a MongoDB...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db.users
        
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
                "perfil_completo": False
            }
            
            result = self.users.insert_one(user_data)
            logger.info(f"Usuario registrado: {email}")
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
        try:
            self._ensure_connection()
            
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                return user
            return None
            
        except Exception as e:
            logger.error(f"Error obteniendo info del usuario {user_id}: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[dict]:
        try:
            self._ensure_connection()
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
            return user
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
            for user in users:
                user["_id"] = str(user["_id"])
                user.pop("password_hash", None)
            return users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios pendientes: {e}")
            return []

    def get_all_users(self) -> List[dict]:
        """Obtener todos los usuarios del sistema"""
    try:
        self._ensure_connection()
        
        # ✅ CORRECCIÓN: Agregar logging detallado para debuggear
        logger.info("Intentando obtener todos los usuarios de la base de datos")
        
        # ✅ CORRECCIÓN: Verificar que la colección existe
        if self.users is None:
            logger.error("La colección 'users' no está inicializada")
            return []
        
        # ✅ CORRECCIÓN: Obtener usuarios con manejo de errores específico
        try:
            users_cursor = self.users.find({})
            users = list(users_cursor)
            logger.info(f"Se encontraron {len(users)} usuarios en la base de datos")
            
        except Exception as db_error:
            logger.error(f"Error al consultar la base de datos: {db_error}")
            return []
        
        # ✅ CORRECCIÓN: Procesar usuarios con validación
        processed_users = []
        for user in users:
            try:
                # Verificar que el usuario tiene los campos básicos
                if "_id" not in user:
                    logger.warning(f"Usuario sin _id encontrado: {user}")
                    continue
                
                # Convertir ObjectId a string y limpiar datos sensibles
                user["_id"] = str(user["_id"])
                user.pop("password_hash", None)
                user.pop("session_id", None)  # También remover session_id por seguridad
                
                processed_users.append(user)
                
            except Exception as user_error:
                logger.error(f"Error procesando usuario individual: {user_error}")
                logger.error(f"Datos del usuario problemático: {user}")
                continue
        
        logger.info(f"Se procesaron exitosamente {len(processed_users)} usuarios")
        return processed_users
        
    except Exception as e:
        logger.error(f"Error crítico obteniendo todos los usuarios: {e}")
        logger.error(f"Tipo de error: {type(e).__name__}")
        import traceback
        logger.error(f"Stack trace completo: {traceback.format_exc()}")
        return []

    # ✅ FUNCIONES ADMIN CORREGIDAS
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
            for user in users:
                user["_id"] = str(user["_id"])
                user.pop("password_hash", None)
            return users
        except Exception as e:
            logger.error(f"Error obteniendo usuarios por rol {role}: {e}")
            return []

    def get_user_by_email(self, email: str):
        try:
            self._ensure_connection()
            
            user = self.users.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
                return user
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