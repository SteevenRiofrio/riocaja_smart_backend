# -*- coding: utf-8 -*-
# app/services/user_service.py - CODIGO COMPLETO CORREGIDO
import logging
from typing import Optional, List
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from datetime import datetime
from app.config import MONGO_URI, DATABASE_NAME
from app.models.user import User, Estado, Rol
from app.services.crypto_service import hash_password, verify_password

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para usuarios...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.users = self.db["users"]
            logger.info(f"Conexion exitosa a la base de datos: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def register_user(self, nombre: str, email: str, password: str, rol: str = "lector") -> dict:
        """Registra un nuevo usuario en estado pendiente"""
        if self.users.find_one({"email": email}):
            raise ValueError("Email ya registrado")

        if len(password) < 8:
            raise ValueError("Contraseña debe tener minimo 8 caracteres")

        hashed_pw = hash_password(password)
        user = User(
            nombre=nombre,
            email=email,
            password_hash=hashed_pw,
            rol=rol,
            estado=Estado.pendiente,
            perfil_completo=False  # Iniciar con perfil incompleto
        )
        user_dict = user.dict()
        result = self.users.insert_one(user_dict)
        logger.info(f"Usuario registrado con email: {email}, estado: pendiente")
        return {
            "msg": "Usuario registrado. Un administrador revisara su solicitud.",
            "id": str(result.inserted_id)
        }
    
    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        """Autentica un usuario y devuelve sus datos si es valido"""
        user_db = self.users.find_one({"email": email})
        if not user_db:
            return None

        if user_db.get("estado") == "pendiente":
            logger.info(f"Intento de inicio de sesion de usuario pendiente: {email}")
            return None
            
        if user_db.get("estado") == "inactivo":
            logger.info(f"Intento de inicio de sesion de usuario inactivo: {email}")
            return None

        if not verify_password(password, user_db["password_hash"]):
            self.users.update_one({"email": email}, {"$inc": {"intentos_fallidos": 1}})
            return None

        # Reiniciar intentos fallidos tras inicio de sesion exitoso
        self.users.update_one({"email": email}, {"$set": {"intentos_fallidos": 0}})
        
        user_db["_id"] = str(user_db["_id"])
        return user_db
    
    def complete_user_profile(self, user_id: str, codigo_corresponsal: str, 
                            nombre_local: str, nombre_completo: str, nueva_password: str) -> bool:
        """Completa el perfil del usuario verificando el codigo de corresponsal"""
        try:
            # Verificar que el usuario existe y tiene el codigo correcto
            user = self.users.find_one({
                "_id": ObjectId(user_id),
                "codigo_corresponsal": codigo_corresponsal,
                "estado": "activo"
            })
            
            if not user:
                logger.warning(f"Usuario {user_id} no encontrado o codigo incorrecto")
                return False
            
            # Validar datos
            if len(nueva_password) < 8:
                raise ValueError("La nueva contraseña debe tener al menos 8 caracteres")
            
            if not nombre_local.strip():
                raise ValueError("El nombre del local es requerido")
            
            if not nombre_completo.strip():
                raise ValueError("El nombre completo es requerido")
            
            # Actualizar usuario con nueva informacion
            hashed_pw = hash_password(nueva_password)
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "nombre_local": nombre_local.strip(),
                        "nombre": nombre_completo.strip(),  # Actualizar nombre completo
                        "password_hash": hashed_pw,         # Nueva contraseña
                        "perfil_completo": True,            # Marcar como completado
                        "fecha_perfil_completado": datetime.utcnow()
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Perfil completado para usuario {user_id}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al completar perfil: {e}")
            return False
    
    def verify_corresponsal_code(self, user_id: str, codigo: str) -> bool:
        """Verifica si el codigo de corresponsal es valido para el usuario"""
        try:
            user = self.users.find_one({
                "_id": ObjectId(user_id),
                "codigo_corresponsal": codigo,
                "estado": "activo"
            })
            return user is not None
        except Exception as e:
            logger.error(f"Error al verificar codigo: {e}")
            return False
    
    def approve_user_with_code(self, user_id: str, admin_id: str, codigo_corresponsal: str) -> bool:
        """Aprueba un usuario y le asigna un codigo de corresponsal"""
        try:
            # Verificar que el codigo no este ya en uso
            existing_code = self.users.find_one({"codigo_corresponsal": codigo_corresponsal})
            if existing_code:
                raise ValueError("El codigo de corresponsal ya esta en uso")
            
            # Validar formato del codigo
            if not codigo_corresponsal.strip() or len(codigo_corresponsal.strip()) < 3:
                raise ValueError("El codigo de corresponsal debe tener al menos 3 caracteres")
            
            # Obtener el usuario para verificar su rol
            user_to_approve = self.users.find_one({"_id": ObjectId(user_id), "estado": "pendiente"})
            if not user_to_approve:
                raise ValueError("Usuario no encontrado o ya procesado")
            
            # Determinar si necesita completar perfil basado en el rol
            user_role = user_to_approve.get("rol", "lector")
            perfil_completo = user_role in ["admin", "operador"]  # Admin y operador no necesitan completar perfil
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id), "estado": "pendiente"},
                {
                    "$set": {
                        "estado": "activo",
                        "codigo_corresponsal": codigo_corresponsal.strip().upper(),
                        "aprobado_por": admin_id,
                        "fecha_aprobacion": datetime.utcnow(),
                        "perfil_completo": perfil_completo  # True para admin/operador, False para lector
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} aprobado con codigo: {codigo_corresponsal}, rol: {user_role}, perfil_completo: {perfil_completo}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al aprobar usuario con codigo: {e}")
            raise ValueError(str(e))
    
    def get_pending_users(self) -> List[dict]:
        """Obtiene todos los usuarios en estado pendiente"""
        users = list(self.users.find({"estado": "pendiente"}).sort("fecha_registro", DESCENDING))
        for user in users:
            user["_id"] = str(user["_id"])
        return users
    
    def approve_user(self, user_id: str, admin_id: str) -> bool:
        """Aprueba un usuario pendiente (metodo legacy sin codigo)"""
        try:
            # Obtener el usuario para verificar su rol
            user_to_approve = self.users.find_one({"_id": ObjectId(user_id), "estado": "pendiente"})
            if not user_to_approve:
                return False
            
            # Determinar si necesita completar perfil basado en el rol
            user_role = user_to_approve.get("rol", "lector")
            perfil_completo = user_role in ["admin", "operador"]
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id), "estado": "pendiente"},
                {
                    "$set": {
                        "estado": "activo", 
                        "aprobado_por": admin_id,
                        "fecha_aprobacion": datetime.utcnow(),
                        "perfil_completo": perfil_completo
                    }
                }
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Usuario {user_id} aprobado (metodo legacy), rol: {user_role}, perfil_completo: {perfil_completo}")
            
            return success
        except Exception as e:
            logger.error(f"Error al aprobar usuario: {e}")
            return False
    
    def reject_user(self, user_id: str) -> bool:
        """Rechaza un usuario pendiente"""
        result = self.users.update_one(
            {"_id": ObjectId(user_id), "estado": "pendiente"},
            {"$set": {"estado": "inactivo"}}
        )
        return result.modified_count > 0
        
    def change_user_role(self, user_id: str, new_role: str) -> bool:
        """Cambia el rol de un usuario"""
        if new_role not in [r.value for r in Rol]:
            raise ValueError(f"Rol invalido: {new_role}")
        
        # Si el nuevo rol es admin/operador, marcar perfil como completo
        perfil_completo = new_role in ["admin", "operador"]
        
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "rol": new_role,
                    "perfil_completo": perfil_completo
                }
            }
        )
        return result.modified_count > 0
    
    def get_user_info(self, user_id: str) -> Optional[dict]:
        """Obtiene informacion completa del usuario"""
        try:
            user = self.users.find_one({"_id": ObjectId(user_id)})
            if user:
                user["_id"] = str(user["_id"])
                # No devolver el hash de la contraseña
                user.pop("password_hash", None)
            return user
        except Exception as e:
            logger.error(f"Error al obtener informacion del usuario: {e}")
            return None
    
    def create_admin_user(self, nombre: str, email: str, password: str) -> dict:
        """Crea un usuario administrador directamente (para setup inicial)"""
        if self.users.find_one({"email": email}):
            raise ValueError("Email ya registrado")

        if len(password) < 8:
            raise ValueError("Contraseña debe tener minimo 8 caracteres")

        hashed_pw = hash_password(password)
        admin_user = User(
            nombre=nombre,
            email=email,
            password_hash=hashed_pw,
            rol="admin",
            estado=Estado.activo,  # Admin se crea directamente activo
            perfil_completo=True,  # Admin no necesita completar perfil
            fecha_aprobacion=datetime.utcnow()
        )
        user_dict = admin_user.dict()
        result = self.users.insert_one(user_dict)
        logger.info(f"Usuario administrador creado con email: {email}")
        return {
            "msg": "Usuario administrador creado exitosamente",
            "id": str(result.inserted_id)
        }
    
    def get_user_by_email(self, email: str) -> Optional[dict]:
        """Obtiene un usuario por su email"""
        try:
            user = self.users.find_one({"email": email})
            if user:
                user["_id"] = str(user["_id"])
                # No devolver el hash de la contraseña
                user.pop("password_hash", None)
            return user
        except Exception as e:
            logger.error(f"Error al obtener usuario por email: {e}")
            return None
    
    def update_user_info(self, user_id: str, updates: dict) -> bool:
        """Actualiza informacion del usuario"""
        try:
            # Filtrar campos que se pueden actualizar
            allowed_fields = ["nombre", "nombre_local", "codigo_corresponsal"]
            filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
            
            if not filtered_updates:
                return False
            
            result = self.users.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": filtered_updates}
            )
            
            success = result.modified_count > 0
            if success:
                logger.info(f"Informacion actualizada para usuario {user_id}: {filtered_updates}")
            
            return success
        except Exception as e:
            logger.error(f"Error al actualizar informacion del usuario: {e}")
            return False