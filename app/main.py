# app/main.py - INTEGRADO CON TÉRMINOS Y CONDICIONES
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.routes import auth, receipts, password_reset, messages
from app.config import API_PREFIX
from app.services.user_service import UserService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="RioCaja Smart API",
    description="API para gestion de comprobantes y usuarios",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== ROUTERS EXISTENTES =====
app.include_router(auth.router, prefix=f"{API_PREFIX}/auth", tags=["Auth"])
app.include_router(receipts.router, prefix=f"{API_PREFIX}/receipts", tags=["Receipts"])
app.include_router(password_reset.router, prefix=f"{API_PREFIX}/password-reset", tags=["Password Reset"])
app.include_router(messages.router, prefix=f"{API_PREFIX}/messages", tags=["Messages"])

# ===== MODELOS PARA TÉRMINOS Y CONDICIONES =====
class TermsAcceptanceRequest(BaseModel):
    user_id: str
    acepta: bool

class TermsAcceptanceResponse(BaseModel):
    success: bool
    message: str
    necesita_aceptar: bool = False

# ===== ENDPOINTS EXISTENTES =====
@app.get("/")
async def root():
    return {
        "message": "RioCaja Smart API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# ===== 🆕 NUEVOS ENDPOINTS PARA TÉRMINOS Y CONDICIONES =====

@app.post(f"{API_PREFIX}/users/terms/accept", response_model=TermsAcceptanceResponse, tags=["Terms"])
async def accept_terms(request: TermsAcceptanceRequest):
    """
    Endpoint para que un usuario acepte o rechace términos y condiciones
    
    - **user_id**: ID del usuario
    - **acepta**: True para aceptar, False para rechazar
    """
    user_service = UserService()
    
    try:
        logger.info(f"Procesando aceptación de términos para usuario: {request.user_id}")
        
        # Verificar que el usuario existe
        user = user_service.get_user_by_id(request.user_id)
        if not user:
            logger.warning(f"Usuario no encontrado: {request.user_id}")
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Actualizar aceptación de términos
        success = user_service.update_terms_acceptance(request.user_id, request.acepta)
        
        if not success:
            logger.error(f"Error actualizando términos para usuario: {request.user_id}")
            raise HTTPException(status_code=500, detail="Error actualizando términos")
        
        if request.acepta:
            logger.info(f"Términos aceptados por usuario: {request.user_id}")
            return TermsAcceptanceResponse(
                success=True,
                message="Términos y condiciones aceptados correctamente",
                necesita_aceptar=False
            )
        else:
            logger.info(f"Términos rechazados por usuario: {request.user_id}")
            return TermsAcceptanceResponse(
                success=True,
                message="Términos y condiciones rechazados. No puede acceder a la aplicación",
                necesita_aceptar=True
            )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno en accept_terms: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.get(f"{API_PREFIX}/users/{{user_id}}/terms/status", tags=["Terms"])
async def check_terms_status(user_id: str):
    """
    Verificar el estado de aceptación de términos de un usuario
    
    - **user_id**: ID del usuario a verificar
    
    Returns:
    - acepto_terminos: boolean
    - fecha_acepta_terminos: datetime o null
    - necesita_aceptar: boolean
    """
    user_service = UserService()
    
    try:
        logger.info(f"Verificando estado de términos para usuario: {user_id}")
        
        result = user_service.check_terms_acceptance(user_id)
        
        if "error" in result:
            logger.warning(f"Error verificando términos: {result['error']}")
            raise HTTPException(status_code=404, detail=result["error"])
        
        logger.info(f"Estado de términos para {user_id}: {result['acepto_terminos']}")
        
        return {
            "user_id": user_id,
            "acepto_terminos": result["acepto_terminos"],
            "fecha_acepta_terminos": result["fecha_acepta_terminos"],
            "necesita_aceptar": result["necesita_aceptar"]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error interno en check_terms_status: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@app.post(f"{API_PREFIX}/users/terms/migrate", tags=["Terms", "Admin"])
async def migrate_terms_field():
    """
    Endpoint para migrar usuarios existentes (agregar campo acepto_terminos=False)
    
    ⚠️ **IMPORTANTE**: Solo usar una vez para usuarios existentes que no tienen el campo
    
    Este endpoint es para migración de base de datos. Ejecutar una sola vez.
    """
    user_service = UserService()
    
    try:
        logger.info("Iniciando migración de términos para usuarios existentes")
        
        success = user_service.migrate_existing_users_terms()
        
        if success:
            logger.info("Migración de términos completada exitosamente")
            return {
                "success": True,
                "message": "Migración de términos completada exitosamente",
                "warning": "Este endpoint debe ejecutarse solo una vez"
            }
        else:
            logger.error("Error en la migración de términos")
            raise HTTPException(status_code=500, detail="Error en la migración")
    
    except Exception as e:
        logger.error(f"Error en migración: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error en migración: {str(e)}")

@app.get(f"{API_PREFIX}/users/without-terms", tags=["Terms", "Admin"])
async def get_users_without_terms():
    """
    Obtener lista de usuarios que no han aceptado términos y condiciones
    
    Útil para administradores para ver qué usuarios necesitan aceptar términos
    """
    user_service = UserService()
    
    try:
        logger.info("Obteniendo usuarios sin aceptar términos")
        
        users = user_service.get_users_without_terms_acceptance()
        
        logger.info(f"Encontrados {len(users)} usuarios sin aceptar términos")
        
        return {
            "users": users,
            "total": len(users),
            "message": f"Se encontraron {len(users)} usuarios sin aceptar términos",
            "timestamp": "2025-01-25T10:00:00Z"
        }
    
    except Exception as e:
        logger.error(f"Error obteniendo usuarios sin términos: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ===== 🆕 ENDPOINT ADICIONAL PARA VERIFICAR CUMPLIMIENTO TOTAL =====
@app.get(f"{API_PREFIX}/users/{{user_id}}/compliance", tags=["Terms"])
async def check_user_compliance(user_id: str):
    """
    Verificar cumplimiento total del usuario (términos + privacidad + estado)
    
    - **user_id**: ID del usuario a verificar
    
    Returns información completa sobre el cumplimiento del usuario
    """
    user_service = UserService()
    
    try:
        logger.info(f"Verificando cumplimiento total para usuario: {user_id}")
        
        # Obtener usuario completo
        user = user_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # Verificar términos
        terms_result = user_service.check_terms_acceptance(user_id)
        
        return {
            "user_id": user_id,
            "cumplimiento": {
                "acepto_terminos": terms_result.get("acepto_terminos", False),
                "fecha_acepta_terminos": terms_result.get("fecha_acepta_terminos"),
                "usuario_activo": user.get("activo", False),
                "estado": user.get("estado", "unknown"),
                "perfil_completo": user.get("perfil_completo", False)
            },
            "puede_usar_app": (
                terms_result.get("acepto_terminos", False) and
                user.get("activo", False) and
                user.get("estado") == "activo"
            ),
            "acciones_requeridas": [
                action for action, required in [
                    ("Aceptar términos y condiciones", not terms_result.get("acepto_terminos", False)),
                    ("Activar cuenta", not user.get("activo", False)),
                    ("Aprobar cuenta", user.get("estado") != "activo"),
                    ("Completar perfil", not user.get("perfil_completo", False))
                ] if required
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error verificando cumplimiento: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

# ===== EJECUTOR PRINCIPAL =====
if __name__ == "__main__":
    import uvicorn
    from app.config import HOST, PORT
    logger.info("Iniciando RioCaja Smart API con soporte para términos y condiciones")
    uvicorn.run(app, host=HOST, port=PORT)