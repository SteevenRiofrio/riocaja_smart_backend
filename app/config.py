# app/config.py - CONFIGURACIÓN COMPLETA
import os
from dotenv import load_dotenv

load_dotenv()

# MongoDB con timeouts extendidos y configuración robusta
MONGO_URI = "mongodb+srv://riocajasmart09:riocajas12345@cluster0.ow7d1gr.mongodb.net/riocaja_smart?retryWrites=true&w=majority&ssl=true&authSource=admin"


DATABASE_NAME = "riocaja_smart"

# JWT
SECRET_KEY = "mtaz fuoi eusc xowf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

# Configuración de EMAIL
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "riocaja.smart09@gmail.com")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "espe@050702")
MAIL_FROM = os.getenv("MAIL_FROM", "riocaja.smart09@gmail.com")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "RíoCaja Smart")

# Configuración SMTP de Gmail
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "True").lower() == "true"
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "False").lower() == "true"

# Configuración de códigos de recuperación
RESET_CODE_EXPIRE_MINUTES = int(os.getenv("RESET_CODE_EXPIRE_MINUTES", "10"))
RESET_CODE_LENGTH = int(os.getenv("RESET_CODE_LENGTH", "6"))

# Server
PORT = int(os.getenv("PORT", "8080"))
HOST = "0.0.0.0"

# API
API_PREFIX = "/api/v1"

# Detectar entorno de producción
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RAILWAY_PROJECT_ID") is not None

# Logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)