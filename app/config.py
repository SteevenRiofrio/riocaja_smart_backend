# app/config.py
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de la base de datos
MONGO_URI = os.getenv(
    'MONGO_URI', 
    'mongodb+srv://riocajasmart09:riocaja12345@cluster0.ow7d1gr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
)
DATABASE_NAME = os.getenv('DATABASE_NAME', 'riocaja_smart')

# Configuración del servidor
HOST = os.getenv('HOST', '0.0.0.0')
PORT = int(os.getenv('PORT', 8000))
API_PREFIX = os.getenv('API_PREFIX', '/api/v1')

# Configuración de autenticación
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'riocaja-smart-secret-key-2025')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', 30))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', 30))

# Configuración de email
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', os.getenv('MAIL_USERNAME'))
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', os.getenv('MAIL_PASSWORD'))
FROM_EMAIL = os.getenv('FROM_EMAIL', os.getenv('MAIL_FROM'))

# Configuración de email (compatibilidad)
MAIL_USERNAME = os.getenv('MAIL_USERNAME', 'riocaja.smart09@gmail.com')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD', 'mtazfuoieuscxowf')
MAIL_FROM = os.getenv('MAIL_FROM', 'riocaja.smart09@gmail.com')
MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME', 'RioCaja Smart')
MAIL_SERVER = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
MAIL_PORT = int(os.getenv('MAIL_PORT', 587))
MAIL_STARTTLS = os.getenv('MAIL_STARTTLS', 'true').lower() == 'true'
MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'

# Configuración de códigos de reset
RESET_CODE_EXPIRE_MINUTES = int(os.getenv('RESET_CODE_EXPIRE_MINUTES', 15))
RESET_CODE_LENGTH = int(os.getenv('RESET_CODE_LENGTH', 6))

# Configuración de desarrollo
DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')

print(f"🔧 Configuración cargada:")
print(f"   - Environment: {ENVIRONMENT}")
print(f"   - Database: {DATABASE_NAME}")
print(f"   - Host: {HOST}:{PORT}")
print(f"   - Email: {MAIL_FROM}")
print(f"   - Debug: {DEBUG}")