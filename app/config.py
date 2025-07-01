# app/config.py - VERSIÓN PARA RAILWAY
import os
from dotenv import load_dotenv

load_dotenv()

# Detectar si estamos en Railway
IS_RAILWAY = os.getenv("RAILWAY_ENVIRONMENT") is not None

# MongoDB - URI que funciona en Railway
if IS_RAILWAY:
    # En Railway, usar variables de entorno
    MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://riocajasmart09:riocajas12345@cluster0.ow7d1gr.mongodb.net/riocaja_smart?retryWrites=true&w=majority&ssl=true&authSource=admin")
else:
    # En desarrollo local
    MONGO_URI = "mongodb+srv://riocajasmart09:riocajas12345@cluster0.ow7d1gr.mongodb.net/riocaja_smart?retryWrites=true&w=majority&ssl=true&authSource=admin"

DATABASE_NAME = "riocaja_smart"

# JWT
SECRET_KEY = os.getenv("SECRET_KEY", "mtaz fuoi eusc xowf")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# Configuración de EMAIL
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "riocaja.smart09@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "mtazfuoieuscxowf")
MAIL_FROM = os.getenv("MAIL_FROM", "riocaja.smart09@gmail.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "RíoCaja Smart")

# Configuración SMTP
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

# Códigos de recuperación
RESET_CODE_EXPIRE_MINUTES = int(os.getenv("RESET_CODE_EXPIRE_MINUTES", "10"))
RESET_CODE_LENGTH = int(os.getenv("RESET_CODE_LENGTH", "6"))

# Server - Railway automáticamente asigna el puerto
PORT = int(os.getenv("PORT", "8080"))
HOST = "0.0.0.0"

# API
API_PREFIX = "/api/v1"

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)