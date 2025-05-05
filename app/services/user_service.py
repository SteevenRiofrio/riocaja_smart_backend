import logging
from typing import Optional
from pymongo import MongoClient
from app.config import MONGO_URI, DATABASE_NAME
from app.models.user import User
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
            raise ValueError("Contraseña debe tener mínimo 8 caracteres")

        hashed_pw = hash_password(password)
        user = User(
            nombre=nombre,
            email=email,
            password_hash=hashed_pw,
            rol=rol
        )
        user_dict = user.dict()
        self.users.insert_one(user_dict)
        logger.info(f"Usuario registrado con email: {email}")
        return {"msg": "Usuario registrado"}

    def authenticate_user(self, email: str, password: str) -> Optional[dict]:
        user_db = self.users.find_one({"email": email})
        if not user_db:
            return None

        if not verify_password(password, user_db["password_hash"]):
            # Incrementa intentos fallidos
            self.users.update_one({"email": email}, {"$inc": {"intentos_fallidos": 1}})
            return None

        user_db["_id"] = str(user_db["_id"])  # Convierte ObjectId a str
        return user_db
