# tests/conftest.py - Configuraciones y fixtures para testing
import pytest
import asyncio
import os
from unittest.mock import MagicMock, patch

# Importar TestClient solo cuando sea necesario
try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None

# Usar una alternativa más simple para MongoClient mock
try:
    from mongomock import MongoClient
except ImportError:
    # Fallback: crear una clase mock simple
    class MongoClient:
        def __init__(self):
            self.db = MagicMock()
        def __getitem__(self, db_name):
            return self.db

# Mock para configuración de base de datos de testing
TEST_DATABASE_CONFIG = {
    "host": "localhost",
    "port": 27017,
    "database": "riocaja_test",
    "username": "test_user",
    "password": "test_pass"
}

@pytest.fixture(scope="session")
def event_loop():
    """Crear un event loop para toda la sesión de testing"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def mock_mongo_client():
    """Mock del cliente MongoDB para testing"""
    client = MongoClient()
    return client

@pytest.fixture
def mock_database(mock_mongo_client):
    """Mock de la base de datos para testing"""
    return mock_mongo_client[TEST_DATABASE_CONFIG["database"]]

@pytest.fixture
def sample_user_data():
    """Datos de muestra para testing de usuarios"""
    return {
        "nombre": "Usuario Test",
        "email": "test@example.com",
        "password": "test123",
        "rol": "cnb",
        "activo": True,
        "codigo_corresponsal": "TEST001"
    }

@pytest.fixture
def sample_receipt_data():
    """Datos de muestra para testing de comprobantes"""
    return {
        "fecha": "2025-07-28",
        "hora": "14:30:00",
        "tipo": "DEPOSITO",
        "nroTransaccion": "123456789",
        "valorTotal": 150.50,
        "codigo_corresponsal": "TEST001",
        "descripcion": "Depósito de prueba"
    }

@pytest.fixture
def auth_token():
    """Token de autenticación mock para testing"""
    return "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0X3VzZXJfaWQiLCJyb2xlIjoiY25iIn0.test_signature"

@pytest.fixture
def test_client():
    """Cliente de testing para FastAPI"""
    # Importación diferida para evitar problemas circulares
    from app.main import app
    return TestClient(app)

@pytest.fixture(autouse=True)
def mock_database_connection():
    """Mock automático de la conexión a base de datos"""
    with patch('app.services.user_service.UserService._ensure_connection'), \
         patch('app.services.receipt_service.ReceiptService._ensure_connection'), \
         patch('pymongo.MongoClient'):
        yield