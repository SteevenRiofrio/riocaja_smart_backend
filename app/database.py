import os
import logging
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

# Configuración de la base de datos
MONGO_URI = os.getenv(
    'MONGO_URI', 
    'mongodb+srv://riocajasmart09:riocaja12345@cluster0.ow7d1gr.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
)
DATABASE_NAME = os.getenv('DATABASE_NAME', 'riocaja_smart')

# Cliente MongoDB global
client = None
db = None

def init_database():
    """Inicializar conexión a MongoDB"""
    global client, db
    
    try:
        logger.info("Conectando a MongoDB...")
        
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=30000,
            connectTimeoutMS=30000,
            socketTimeoutMS=30000,
            maxPoolSize=10,
            retryWrites=True,
            retryReads=True
        )
        
        # Probar conexión
        client.admin.command('ping')
        
        # Obtener base de datos
        db = client[DATABASE_NAME]
        
        logger.info(f"✅ Conexión exitosa a MongoDB - Base de datos: {DATABASE_NAME}")
        return True
        
    except ConnectionFailure as e:
        logger.error(f"❌ Error de conexión a MongoDB: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error inesperado conectando a MongoDB: {e}")
        return False

def get_database():
    """Obtener instancia de la base de datos"""
    global db
    if db is None:
        init_database()
    return db

def close_database():
    """Cerrar conexión a MongoDB"""
    global client
    if client:
        client.close()
        logger.info("Conexión a MongoDB cerrada")

# Inicializar automáticamente al importar
init_database()