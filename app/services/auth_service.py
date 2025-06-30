from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt, ExpiredSignatureError
from app.config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crear token de acceso JWT con refresh token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Crear refresh token con mayor duración"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)  # 30 días
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def refresh_access_token(refresh_token: str):
    """Generar nuevo access token desde refresh token"""
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        
        # Crear nuevo access token
        user_data = {
            "sub": payload.get("sub"),
            "email": payload.get("email"),
            "rol": payload.get("rol"),
            "perfil_completo": payload.get("perfil_completo")
        }
        return create_access_token(user_data)
    except (JWTError, ExpiredSignatureError):
        return None