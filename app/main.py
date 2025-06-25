import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']  # Google DNS

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.routes import receipts, auth, messages, password_reset
from app.config import API_PREFIX, PORT, HOST
import logging
import os

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Detectar entorno de producción
IS_PRODUCTION = os.getenv("RAILWAY_ENVIRONMENT") is not None or os.getenv("RAILWAY_PROJECT_ID") is not None

# Crear la aplicacion FastAPI
app = FastAPI(
    title="RioCaja Smart API",
    description="Backend API para la aplicacion RioCaja Smart",
    version="1.0.0",
    # SEGURIDAD: Ocultar documentacion en produccion
    docs_url="/docs" if not IS_PRODUCTION else None,
    redoc_url="/redoc" if not IS_PRODUCTION else None,
)

# SEGURIDAD: Lista de endpoints sospechosos para bloquear
BLOCKED_PATHS = {
    "/actuator",
    "/actuator/",
    "/actuator/gateway",
    "/actuator/gateway/routes",
    "/actuator/health",
    "/actuator/env",
    "/actuator/configprops",
    "/management",
    "/admin",
    "/.env",
    "/wp-admin",
    "/wp-login.php",
    "/phpmyadmin",
    "/mysql",
    "/api/health",
    "/status",
    "/info",
    "/debug",
}

# SEGURIDAD: Middleware para bloquear peticiones sospechosas
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    # Bloquear rutas sospechosas
    if any(request.url.path.startswith(blocked) for blocked in BLOCKED_PATHS):
        logger.warning(f"Blocked suspicious request from {request.client.host}: {request.url.path}")
        return JSONResponse(
            status_code=404,
            content={"detail": "Not Found"}
        )
    
    # Bloquear User-Agents sospechosos (más flexible en producción)
    user_agent = request.headers.get("user-agent", "").lower()
    suspicious_agents = ["scanner", "exploit", "hack", "sqlmap", "nikto"]
    if any(agent in user_agent for agent in suspicious_agents):
        logger.warning(f"Blocked suspicious user-agent from {request.client.host}: {user_agent}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Forbidden"}
        )
    
    # Log de peticiones válidas (ajustado para Railway)
    if not request.url.path.startswith("/static") and not IS_PRODUCTION:
        logger.info(f"Valid request: {request.method} {request.url.path} from {request.client.host}")
    elif IS_PRODUCTION and request.url.path.startswith("/api"):
        # En producción, solo log de APIs
        logger.info(f"API request: {request.method} {request.url.path}")
    
    response = await call_next(request)
    return response

# CORS configuración (más estricto en producción)
allowed_origins = ["*"]  # Desarrollo
if IS_PRODUCTION:
    allowed_origins = [
        "https://tu-frontend-domain.com",  # Reemplaza con tu dominio real
        "https://riocaja-smart.netlify.app",  # Ejemplo si usas Netlify
        # Agrega aquí los dominios de tu aplicación Flutter/frontend
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# Incluir rutas con barras finales consistentes
app.include_router(
    receipts.router,
    prefix=f"{API_PREFIX}/receipts",
    tags=["receipts"],
)

app.include_router(
    auth.router,
    prefix=f"{API_PREFIX}/auth",
    tags=["auth"],
)

# CORREGIDO: Asegurar consistencia en rutas de mensajes
app.include_router(
    messages.router,
    prefix=f"{API_PREFIX}/messages",
    tags=["messages"],
)

app.include_router(
    password_reset.router,
    prefix=f"{API_PREFIX}/auth",
    tags=["password-reset"],
)

@app.get("/", tags=["root"])
async def read_root():
    return {
        "message": "Bienvenido a la API de RioCaja Smart",
        "environment": "production" if IS_PRODUCTION else "development",
        "version": "1.0.0"
    }

# SEGURIDAD: Endpoint básico de health (sin información sensible)
@app.get("/ping", tags=["health"])
async def ping():
    return {
        "status": "ok", 
        "service": "riocaja-smart-api",
        "environment": "production" if IS_PRODUCTION else "development"
    }

# NUEVO: Health check para Railway
@app.get("/health", tags=["health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "riocaja-smart-api",
        "environment": "production" if IS_PRODUCTION else "development"
    }

# SEGURIDAD: Manejar errores 404 personalizados
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    logger.warning(f"404 Not Found: {request.method} {request.url.path} from {request.client.host}")
    return JSONResponse(
        status_code=404,
        content={"detail": "Endpoint not found"}
    )

# Para ejecutar con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=HOST, port=PORT, reload=not IS_PRODUCTION)