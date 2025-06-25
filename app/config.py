import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

MONGO_URI = "mongodb://riocajasmart09:riocajas12345@cluster0-shard-00-00.ow7d1gr.mongodb.net:27017,cluster0-shard-00-01.ow7d1gr.mongodb.net:27017,cluster0-shard-00-02.ow7d1gr.mongodb.net:27017/riocaja_smart?ssl=true&replicaSet=atlas-14rkz9-shard-0&authSource=admin&retryWrites=true&w=majority"


DATABASE_NAME = os.getenv("DATABASE_NAME", "riocaja_smart")

# Resto de la configuración...
API_PREFIX = "/api/v1"
SECRET_KEY = os.getenv("SECRET_KEY", "mtaz fuoi eusc xowf")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))

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

# Configuración específica para Railway
PORT = int(os.getenv("PORT", "8080"))
HOST = os.getenv("HOST", "0.0.0.0")

# Detectar entorno de producción
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RAILWAY_PROJECT_ID") is not None