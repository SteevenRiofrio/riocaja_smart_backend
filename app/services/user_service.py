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
            logger.info(f"Conexión exitosa a la base de datos: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def register_user(self, nombre: str, email: str, password: str, rol: str = "lector") -> dict:
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
            estado=Estado.pendiente  # Todos los usuarios comienzan en estado pendiente
        )
        user_dict = user.dict()
        result = self.users.insert_one(user_dict)
        logger.info(f"Usuario registrado con email: {email}, estado: pendiente")
        return {
            "msg": "Usuario registrado. Un administrador revisará su solicitud.",
            "id": str(result.inserted_id)
        }
    
    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        user_db = self.users.find_one({"email": email})
        if not user_db:
            return None

        if user_db.get("estado") == "pendiente":
            # Si el usuario está pendiente, no permitir el inicio de sesion
            logger.info(f"Intento de inicio de sesion de usuario pendiente: {email}")
            return None
            
        if user_db.get("estado") == "inactivo":
            # Si el usuario está inactivo, no permitir el inicio de sesion
            logger.info(f"Intento de inicio de sesion de usuario inactivo: {email}")
            return None

        if not verify_password(password, user_db["password_hash"]):
            # Incrementa intentos fallidos
            self.users.update_one({"email": email}, {"$inc": {"intentos_fallidos": 1}})
            return None

        # Reiniciar intentos fallidos tras inicio de sesión exitoso
        self.users.update_one({"email": email}, {"$set": {"intentos_fallidos": 0}})
        
        user_db["_id"] = str(user_db["_id"])  # Convierte ObjectId a str
        return user_db
    
    # Nuevos métodos para gestión de aprobación de usuarios
    
    def get_pending_users(self) -> List[dict]:
        """Obtiene todos los usuarios en estado pendiente"""
        users = list(self.users.find({"estado": "pendiente"}).sort("fecha_registro", DESCENDING))
        for user in users:
            user["_id"] = str(user["_id"])
        return users
    
    def approve_user(self, user_id: str, admin_id: str) -> bool:
        """Aprueba un usuario pendiente"""
        result = self.users.update_one(
            {"_id": ObjectId(user_id), "estado": "pendiente"},
            {
                "$set": {
                    "estado": "activo", 
                    "aprobado_por": admin_id,
                    "fecha_aprobacion": datetime.utcnow()
                }
            }
        )
        return result.modified_count > 0
    
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
            
        result = self.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"rol": new_role}}
        )
        return result.modified_count > 0