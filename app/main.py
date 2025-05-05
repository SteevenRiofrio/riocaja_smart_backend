# app/main.py
import dns.resolver
dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
dns.resolver.default_resolver.nameservers = ['8.8.8.8', '8.8.4.4']  # Google DNS
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routes import receipts
from app.config import API_PREFIX
from app.routes import receipts, auth  # Importa el nuevo router


# Crear la aplicación FastAPI
app = FastAPI(
    title="RíoCaja Smart API",
    description="Backend API para la aplicación RíoCaja Smart",
    version="1.0.0",
)

# Configurar CORS para permitir solicitudes desde la app Flutter
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringe esto a tus dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir rutas
app.include_router(
    receipts.router,
    prefix=f"{API_PREFIX}/receipts",
    tags=["receipts"],
)

app.include_router(
    auth.router,  # Añade las rutas de autenticación
    prefix=f"{API_PREFIX}/auth",
    tags=["auth"],
)

@app.get("/", tags=["root"])
async def read_root():
    return {"message": "Bienvenido a la API de RíoCaja Smart"}

# Para ejecutar con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)