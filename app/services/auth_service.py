from datetime import datetime, timedelta
from jose import jwt, JWTError
from app.config import SECRET_KEY, ALGORITHM
from typing import Optional

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
        
def authenticate_user(self, email: str, password: str) -> Optional[dict]:
    user_db = self.users.find_one({"email": email})
    if not user_db:
        return None

    if user_db.get("estado") == "pendiente":
        # Si el usuario está pendiente, no permitir el inicio de sesion
        logger.info(f"Intento de inicio de sesion de usuario pendiente: {email}")
        return None
        
    if user_db.get("estado") == "inactivo":
        # Si el usuario esta inactivo, no permitir el inicio de sesion
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
