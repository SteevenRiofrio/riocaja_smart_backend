# app/routes/password_reset.py
from fastapi import APIRouter, HTTPException, Depends
from app.models.password_reset import (
    PasswordResetRequest, 
    VerifyResetCodeRequest, 
    ResetPasswordRequest,
    PasswordResetResponse,
    ResetStatsResponse
)
from app.services.password_reset_service import PasswordResetService
from app.middlewares.auth_middleware import get_current_user
import logging

logger = logging.getLogger(__name__)
router = APIRouter()
password_reset_service = PasswordResetService()

@router.post("/forgot-password", response_model=PasswordResetResponse)
async def request_password_reset(request: PasswordResetRequest):
    """
    Solicita un codigo de recuperacion de contrasena
    
    - **email**: Email del usuario registrado
    
    Envia un codigo de 6 digitos al email si esta registrado.
    El codigo expira en 10 minutos.
    """
    try:
        logger.info(f"Solicitud de recuperacion de contrasena para: {request.email}")
        
        result = await password_reset_service.request_password_reset(request.email)
        
        return PasswordResetResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except Exception as e:
        logger.error(f"Error en forgot-password: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )

@router.post("/verify-reset-code", response_model=PasswordResetResponse)
async def verify_reset_code(request: VerifyResetCodeRequest):
    """
    Verifica si el codigo de recuperacion es valido
    
    - **email**: Email del usuario
    - **code**: Codigo de 6 digitos recibido por email
    
    Valida el codigo antes de permitir el cambio de contrasena.
    """
    try:
        logger.info(f"Verificacion de codigo para: {request.email}")
        
        # Validar formato del codigo
        if not request.code.isdigit():
            raise HTTPException(
                status_code=400,
                detail="El codigo debe contener solo numeros"
            )
        
        result = password_reset_service.verify_reset_code(request.email, request.code)
        
        if result["success"]:
            return PasswordResetResponse(
                success=True,
                message=result["message"],
                reset_id=result.get("reset_id")
            )
        else:
            return PasswordResetResponse(
                success=False,
                message=result["message"]
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en verify-reset-code: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )

@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(request: ResetPasswordRequest):
    """
    Cambia la contrasena usando el codigo de verificacion
    
    - **email**: Email del usuario
    - **code**: Codigo de verificacion valido
    - **new_password**: Nueva contrasena (minimo 8 caracteres)
    
    Cambia la contrasena y envia confirmacion por email.
    """
    try:
        logger.info(f"Cambio de contrasena para: {request.email}")
        
        # Validaciones basicas
        if not request.code.isdigit():
            raise HTTPException(
                status_code=400,
                detail="El codigo debe contener solo numeros"
            )
        
        if len(request.new_password) < 8:
            raise HTTPException(
                status_code=400,
                detail="La contrasena debe tener al menos 8 caracteres"
            )
        
        # Validar complejidad de contrasena
        if not any(c.isalpha() for c in request.new_password):
            raise HTTPException(
                status_code=400,
                detail="La contrasena debe contener al menos una letra"
            )
        
        if not any(c.isdigit() for c in request.new_password):
            raise HTTPException(
                status_code=400,
                detail="La contrasena debe contener al menos un numero"
            )
        
        result = await password_reset_service.reset_password(
            request.email, 
            request.code, 
            request.new_password
        )
        
        return PasswordResetResponse(
            success=result["success"],
            message=result["message"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reset-password: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )

@router.get("/reset-stats/{email}", response_model=ResetStatsResponse)
async def get_reset_stats(email: str):
    """
    Obtiene estadisticas de intentos de reset para un email
    
    - **email**: Email del usuario
    
    Retorna informacion sobre solicitudes activas y intentos restantes.
    """
    try:
        logger.info(f"Consultando estadisticas de reset para: {email}")
        
        # Validar formato de email basico
        if "@" not in email or "." not in email:
            raise HTTPException(
                status_code=400,
                detail="Formato de email invalido"
            )
        
        stats = password_reset_service.get_reset_stats(email)
        
        return ResetStatsResponse(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en reset-stats: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )

@router.delete("/cleanup-expired", dependencies=[Depends(get_current_user)])
async def cleanup_expired_codes():
    """
    Limpia codigos de recuperacion expirados (solo para usuarios autenticados)
    
    Elimina automaticamente codigos que ya expiraron.
    """
    try:
        logger.info("Ejecutando limpieza de codigos expirados")
        
        password_reset_service.cleanup_expired_codes()
        
        return {
            "success": True,
            "message": "Codigos expirados eliminados correctamente"
        }
        
    except Exception as e:
        logger.error(f"Error en cleanup-expired: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno del servidor"
        )