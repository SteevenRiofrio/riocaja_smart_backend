import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Cadena de conexión directa (sin SRV)
MONGO_URI = "mongodb+srv://riocajasmart09:riocajas12345@cluster0.ow7d1gr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DATABASE_NAME = "riocaja_smart"

# Configuración de la API
API_PREFIX = "/api/v1"