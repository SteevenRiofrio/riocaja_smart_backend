# app/utils/security.py
from passlib.context import CryptContext
import logging

logger = logging.getLogger(__name__)

# Configuración más robusta para passlib y bcrypt
try:
    pwd_context = CryptContext(
        schemes=["bcrypt"], 
        deprecated="auto",
        bcrypt__rounds=12  # Especificar rounds explícitamente
    )
except Exception as e:
    logger.warning(f"Error configurando CryptContext: {e}")
    # Fallback más simple
    pwd_context = CryptContext(schemes=["bcrypt"])

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    try:
        return pwd_context.hash(password)
    except Exception as e:
        logger.error(f"Error hashing password: {e}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
        return False