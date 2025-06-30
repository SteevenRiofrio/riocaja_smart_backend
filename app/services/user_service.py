# app/services/user_service.py - VERSIÓN CORREGIDA CON MEJOR CONEXIÓN
import logging
from datetime import datetime
from typing import List, Optional
from pymongo import MongoClient
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME
from app.services.crypto_service import hash_password, verify_password

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

    def register_user(self, nombre: str, email: str, password: str, rol: str = "lector"):
        try:
            self._ensure_connection()
            
            # Verificar si existe
            if self.users.find_one({"email": email}):
                raise ValueError("El email ya está registrado")
            
            # Crear usuario
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
            logger.error(f"Error al registrar usuario: {e}")
            raise Exception("Error de conexión con la base de datos")

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
            
            user["_id"] = str(user["_id"])
            logger.info(f"Autenticación exitosa: {email}")
            return user
            
        except Exception as e:
            logger.error(f"Error en autenticación: {e}")
            # Devolver None en lugar de raise para que el frontend reciba "credenciales incorrectas"
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
            logger.error(f"Error al obtener usuario {user_id}: {e}")
            return None

    def approve_user_with_code(self, user_id: str, codigo_corresponsal: str, approved_by: str):
        try:
            self._ensure_connection()
            
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
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} aprobado con código {codigo_corresponsal}")
            return success
            
        except Exception as e:
            logger.error(f"Error al aprobar usuario {user_id}: {e}")
            return False

    def complete_user_profile_simple(self, user_id: str, nombre_local: str):
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
            logger.error(f"Error al completar perfil {user_id}: {e}")
            return False

    def get_pending_users(self):
        try:
            self._ensure_connection()
            
            users = list(self.users.find(
                {"estado": "pendiente"}, 
                {"password_hash": 0}  # Excluir password
            ))
            
            for user in users:
                user["_id"] = str(user["_id"])
                
            logger.info(f"Usuarios pendientes obtenidos: {len(users)}")
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener usuarios pendientes: {e}")
            return []

    def get_all_users(self):
        try:
            self._ensure_connection()
            
            users = list(self.users.find(
                {}, 
                {"password_hash": 0}  # Excluir password
            ))
            
            for user in users:
                user["_id"] = str(user["_id"])
                if user.get("aprobado_por"):
                    user["aprobado_por"] = str(user["aprobado_por"])
                    
            logger.info(f"Todos los usuarios obtenidos: {len(users)}")
            return users
            
        except Exception as e:
            logger.error(f"Error al obtener todos los usuarios: {e}")
            return []

    def create_admin_user(self, admin_data: dict):
    '''Crear usuario admin sin necesidad de aprobacion'''
    try:
        # Verificar si existe
        if self.users.find_one({"email": admin_data["email"]}):
            raise ValueError("El email ya está registrado")
        
        from app.utils.password_utils import hash_password
        
        admin_user = {
            "nombre": admin_data["nombre"],
            "email": admin_data["email"],
            "password_hash": hash_password(admin_data["password"]),
            "rol": "admin",
            "estado": "activo",  
            "perfil_completo": True,  
            "fecha_registro": datetime.utcnow(),
            "codigo_corresponsal": "ADMIN",  
            "nombre_local": "Administración"
        }
        
        result = self.users.insert_one(admin_user)
        logger.info(f"Admin creado: {admin_data['email']}")
        return str(result.inserted_id)
        
    except Exception as e:
        logger.error(f"Error creando admin: {e}")
        raise

def create_first_admin(self, admin_data: dict):
    """Crear primer admin del sistema"""
    return self.create_admin_user(admin_data)

def count_admins(self):
    """Contar admins existentes"""
    try:
        return self.users.count_documents({"rol": "admin"})
    except Exception as e:
        logger.error(f"Error contando admins: {e}")
        return 0

def make_user_admin(self, email: str):
    """Convertir usuario existente en admin"""
    try:
        result = self.users.update_one(
            {"email": email},
            {
                "$set": {
                    "rol": "admin",
                    "estado": "activo",
                    "perfil_completo": True,
                    "codigo_corresponsal": "ADMIN001",
                    "nombre_local": "Administración Principal"
                }
            }
        )
        return result.modified_count > 0
    except Exception as e:
        logger.error(f"Error convirtiendo a admin: {e}")
        return False