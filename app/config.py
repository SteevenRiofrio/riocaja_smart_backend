import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de MongoDB
MONGO_URI = "mongodb+srv://riocajasmart09:riocajas12345@cluster0.ow7d1gr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "riocaja_smart"

# Configuración de la API
API_PREFIX = "/api/v1"
SECRET_KEY = "mtaz fuoi eusc xowf"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 horas

# NUEVA CONFIGURACIÓN DE EMAIL
MAIL_USERNAME = os.getenv("MAIL_USERNAME", "riocaja.smart09@gmail.com")  # Tu email de Gmail
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "espe@050702")     # Contraseña de aplicación
MAIL_FROM = os.getenv("MAIL_FROM", "riocaja.smart09@gmail.com")          # Email remitente
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "RíoCaja Smart")     # Nombre del remitente

# Configuración SMTP de Gmail
MAIL_PORT = 587
MAIL_SERVER = "smtp.gmail.com"
MAIL_STARTTLS = True
MAIL_SSL_TLS = False

# Configuración de códigos de recuperación
RESET_CODE_EXPIRE_MINUTES = 10  # Los códigos expiran en 10 minutos
RESET_CODE_LENGTH = 6           # Códigos de 6 dígitos