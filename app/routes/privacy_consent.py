from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import hashlib
import json
import logging
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.models.privacy_consent import PrivacyConsent  # Nuevo modelo
from app.auth.dependencies import get_current_user
from app.schemas.privacy import ConsentRequest, ConsentResponse, RightRequest

router = APIRouter(prefix="/api/privacy", tags=["privacy"])
logger = logging.getLogger(__name__)

@router.post("/consent", response_model=ConsentResponse)
async def save_consent(
    consent_request: ConsentRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Guardar consentimiento de protección de datos
    """
    try:
        user_id = current_user.get("sub")
        
        # Verificar si ya existe consentimiento para este usuario
        existing_consent = db.query(PrivacyConsent).filter(
            PrivacyConsent.user_id == user_id,
            PrivacyConsent.consent_version == consent_request.consent_version,
            PrivacyConsent.is_active == True
        ).first()
        
        if existing_consent:
            # Actualizar consentimiento existente
            existing_consent.essential_consent = consent_request.essential_consent
            existing_consent.marketing_consent = consent_request.marketing_consent
            existing_consent.consent_details = consent_request.consent_details
            existing_consent.updated_at = datetime.utcnow()
            existing_consent.consent_hash = _generate_consent_hash(consent_request)
            
            consent_record = existing_consent
        else:
            # Crear nuevo consentimiento
            consent_record = PrivacyConsent(
                user_id=user_id,
                consent_version=consent_request.consent_version,
                essential_consent=consent_request.essential_consent,
                marketing_consent=consent_request.marketing_consent,
                consent_details=consent_request.consent_details,
                consent_hash=_generate_consent_hash(consent_request),
                ip_address=consent_request.ip_address,
                user_agent=consent_request.user_agent
            )
            db.add(consent_record)
        
        # Registrar evento en logs de auditoría
        await _log_consent_event(
            user_id=user_id,
            event_type="CONSENT_GRANTED" if consent_request.essential_consent else "CONSENT_UPDATED",
            details=consent_request.consent_details,
            db=db
        )
        
        db.commit()
        
        return ConsentResponse(
            success=True,
            message="Consentimiento guardado exitosamente",
            consent_id=consent_record.id,
            valid_until=consent_record.created_at + timedelta(days=365)
        )
        
    except Exception as e:
        logger.error(f"Error guardando consentimiento: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

@router.get("/consent/status")
async def get_consent_status(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Obtener estado actual del consentimiento del usuario
    """
    try:
        user_id = current_user.get("sub")
        
        consent = db.query(PrivacyConsent).filter(
            PrivacyConsent.user_id == user_id,
            PrivacyConsent.is_active == True
        ).order_by(PrivacyConsent.created_at.desc()).first()
        
        if not consent:
            return {
                "has_valid_consent": False,
                "requires_consent": True,
                "message": "No se encontró consentimiento activo"
            }
        
        # Verificar vigencia (1 año)
        is_valid = (datetime.utcnow() - consent.created_at).days < 365
        
        return {
            "has_valid_consent": is_valid,
            "essential_consent": consent.essential_consent,
            "marketing_consent": consent.marketing_consent,
            "consent_version": consent.consent_version,
            "granted_at": consent.created_at.isoformat(),
            "valid_until": (consent.created_at + timedelta(days=365)).isoformat(),
            "requires_consent": not is_valid
        }
        
    except Exception as e:
        logger.error(f"Error verificando estado de consentimiento: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error verificando consentimiento"
        )

@router.post("/rights/request")
async def request_data_right(
    right_request: RightRequest,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Procesar solicitud de ejercicio de derechos ARCO
    """
    try:
        user_id = current_user.get("sub")
        
        # Validar tipo de derecho
        valid_rights = ["ACCESO", "RECTIFICACION", "ELIMINACION", "OPOSICION", "PORTABILIDAD"]
        if right_request.right_type not in valid_rights:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tipo de derecho no válido"
            )
        
        # Crear registro de solicitud
        right_record = DataRightRequest(
            user_id=user_id,
            right_type=right_request.right_type,
            description=right_request.description,
            status="PENDING",
            requested_at=datetime.utcnow()
        )
        db.add(right_record)
        
        # Notificar al DPD por email (implementar)
        await _notify_dpo_right_request(user_id, right_request.right_type, right_request.description)
        
        # Log del evento
        await _log_consent_event(
            user_id=user_id,
            event_type=f"RIGHT_REQUEST_{right_request.right_type}",
            details={"description": right_request.description},
            db=db
        )
        
        db.commit()
        
        return {
            "success": True,
            "request_id": right_record.id,
            "message": f"Solicitud de {right_request.right_type} recibida. Será procesada en máximo 15 días.",
            "estimated_response": (datetime.utcnow() + timedelta(days=15)).isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error procesando solicitud de derecho: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error procesando solicitud"
        )

@router.delete("/consent/revoke")
async def revoke_consent(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Revocar consentimiento (marca como inactivo)
    """
    try:
        user_id = current_user.get("sub")
        
        # Marcar todos los consentimientos como inactivos
        consents = db.query(PrivacyConsent).filter(
            PrivacyConsent.user_id == user_id,
            PrivacyConsent.is_active == True
        ).all()
        
        for consent in consents:
            consent.is_active = False
            consent.revoked_at = datetime.utcnow()
        
        # Log del evento
        await _log_consent_event(
            user_id=user_id,
            event_type="CONSENT_REVOKED",
            details={"reason": "user_request"},
            db=db
        )
        
        db.commit()
        
        return {
            "success": True,
            "message": "Consentimiento revocado exitosamente",
            "revoked_consents": len(consents)
        }
        
    except Exception as e:
        logger.error(f"Error revocando consentimiento: {e}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error revocando consentimiento"
        )

# Funciones auxiliares
def _generate_consent_hash(consent_request: ConsentRequest) -> str:
    """Generar hash único del consentimiento para verificación"""
    content = f"{consent_request.consent_version}{consent_request.essential_consent}{consent_request.marketing_consent}{consent_request.consent_details}"
    return hashlib.sha256(content.encode()).hexdigest()

async def _log_consent_event(user_id: str, event_type: str, details: dict, db: Session):
    """Registrar evento en logs de auditoría"""
    try:
        audit_log = AuditLog(
            user_id=user_id,
            event_type=event_type,
            event_details=json.dumps(details),
            timestamp=datetime.utcnow(),
            ip_address=details.get("ip_address"),
            user_agent=details.get("user_agent")
        )
        db.add(audit_log)
        logger.info(f"Evento de consentimiento registrado: {event_type} para usuario {user_id}")
    except Exception as e:
        logger.error(f"Error registrando evento de auditoría: {e}")

async def _notify_dpo_right_request(user_id: str, right_type: str, description: str):
    """Notificar al DPD sobre solicitud de derecho"""
    try:
        # TODO: Implementar envío de email al DPD
        logger.info(f"Notificación DPD: Solicitud {right_type} de usuario {user_id}")
    except Exception as e:
        logger.error(f"Error notificando al DPD: {e}")