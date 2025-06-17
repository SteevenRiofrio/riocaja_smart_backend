# app/routes/receipts.py - MODIFICADO para validaci√≥n global
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.models.receipt import ReceiptModel
from app.services.receipt_service import ReceiptService
from app.middlewares.auth_middleware import get_current_user, role_required
import logging

# Configurar logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

router = APIRouter()
receipt_service = ReceiptService()

# Get all receipts
@router.get("/", response_description="List all receipts")
async def get_receipts(user=Depends(get_current_user)):
    # Filtrar por usuario si no es administrador
    user_id = None
    if user.get("rol") != "admin":
        user_id = user.get("sub")  # El ID del usuario est√° en el campo "sub" del token JWT
        logger.info(f"Filtrando comprobantes para usuario no-admin: {user_id}")
    
    receipts = await receipt_service.get_all_receipts(user_id)
    return {"data": receipts, "count": len(receipts)}

# Get receipts by date with dash format (dd-mm-aaaa)
@router.get("/date/{date}", response_description="Get receipts by date with dashes")
async def get_receipts_by_date(date: str, user=Depends(get_current_user)):
    """
    Obtiene comprobantes por fecha.
    Use formato dd-mm-aaaa con guiones (por ejemplo: 04-05-2025)
    """
    # Convertir formato de fecha de dd-mm-aaaa a dd/mm/aaaa
    fecha_normalizada = date.replace("-", "/")
    logger.info(f"Buscando comprobantes para fecha normalizada: {fecha_normalizada}")
    
    # Filtrar por usuario si no es administrador
    user_id = None
    if user.get("rol") != "admin":
        user_id = user.get("sub")
        logger.info(f"Filtrando comprobantes por fecha para usuario: {user_id}")
    
    receipts = await receipt_service.get_receipts_by_date(fecha_normalizada, user_id)
    
    if not receipts:
        return {
            "data": [],
            "count": 0,
            "message": f"No se encontraron comprobantes para la fecha: {fecha_normalizada}"
        }
    
    return {"data": receipts, "count": len(receipts)}

# Create a new receipt - MODIFICADO PARA VALIDACI√ìN GLOBAL
@router.post("/", response_description="Create a new receipt")
async def create_receipt(receipt: ReceiptModel, user=Depends(get_current_user)):
    try:
        # Obtener ID del usuario del token JWT
        user_id = user.get("sub")
        user_role = user.get("rol")
        logger.info(f"Usuario {user_id} (rol: {user_role}) creando nuevo comprobante")
        
        # Ì†ΩÌ¥• CAMBIO PRINCIPAL: VALIDACI√ìN GLOBAL PARA TODOS LOS USUARIOS
        # Ya no filtramos por usuario - buscamos en TODOS los comprobantes
        logger.info(f"Verificando duplicados globalmente para transacci√≥n: {receipt.nroTransaccion}")
        existing = await receipt_service.get_receipt_by_transaction(
            receipt.nroTransaccion, 
            user_id=None  # Ì†ΩÌ∫® CLAVE: None = buscar en todos los comprobantes
        )
        
        if existing:
            # Mejorar el mensaje de error para ser m√°s informativo
            existing_user = existing.get('user_id', 'usuario desconocido')
            
            # Si el comprobante ya existe y pertenece al mismo usuario
            if existing_user == user_id:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Ya tienes un comprobante registrado con el n√∫mero de transacci√≥n: {receipt.nroTransaccion}"
                )
            # Si el comprobante existe pero pertenece a otro usuario
            else:
                # Para administradores, mostrar m√°s detalles
                if user_role == "admin":
                    raise HTTPException(
                        status_code=400, 
                        detail=f"El n√∫mero de transacci√≥n {receipt.nroTransaccion} ya est√° registrado en el sistema por otro usuario (ID: {existing_user})"
                    )
                else:
                    # Para usuarios normales, mensaje m√°s gen√©rico por privacidad
                    raise HTTPException(
                        status_code=400, 
                        detail=f"El n√∫mero de transacci√≥n {receipt.nroTransaccion} ya est√° registrado en el sistema"
                    )
        
        # Crear comprobante asign√°ndolo al usuario actual
        created_receipt = await receipt_service.create_receipt(receipt, user_id)
        logger.info(f"Comprobante creado exitosamente: {receipt.nroTransaccion}")
        return {"success": True, "data": created_receipt}
        
    except HTTPException as http_exc:
        # Re-lanzar excepciones HTTP tal como est√°n
        raise http_exc
    except Exception as e:
        logger.error(f"Error inesperado al crear comprobante: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

# Generate closing report with dash format (dd-mm-aaaa)
@router.get("/report/{date}", response_description="Generate closing report")
async def get_closing_report(date: str, user=Depends(get_current_user)):
    """
    Genera un reporte de cierre para una fecha espec√≠fica.
    Use formato dd-mm-aaaa con guiones (por ejemplo: 04-05-2025)
    """
    # Convertir formato de fecha de dd-mm-aaaa a dd/mm/aaaa
    fecha_normalizada = date.replace("-", "/")
    logger.info(f"Generando reporte para fecha normalizada: {fecha_normalizada}")
    
    # Filtrar por usuario si no es administrador
    user_id = None
    if user.get("rol") != "admin":
        user_id = user.get("sub")
        logger.info(f"Filtrando reporte para usuario: {user_id}")
    
    report = await receipt_service.generate_closing_report(fecha_normalizada, user_id)
    return report

# Delete a receipt by transaction number - MODIFICADO PARA VALIDACI√ìN GLOBAL
@router.delete("/{transaction_number}", response_description="Delete a receipt by transaction number")
async def delete_receipt(transaction_number: str, user=Depends(get_current_user)):
    try:
        user_id = user.get("sub")
        user_role = user.get("rol")
        logger.info(f"Usuario {user_id} (rol: {user_role}) intentando eliminar transacci√≥n: {transaction_number}")
        
        # Ì†ΩÌ¥• PRIMERO: Verificar si el comprobante existe globalmente
        existing = await receipt_service.get_receipt_by_transaction(
            transaction_number, 
            user_id=None  # Buscar en todos los comprobantes
        )
        
        if not existing:
            raise HTTPException(
                status_code=404, 
                detail="Comprobante no encontrado en el sistema"
            )
        
        existing_user = existing.get('user_id')
        
        # Ì†ΩÌ¥• SEGUNDO: Verificar permisos de eliminaci√≥n
        if user_role == "admin":
            # Los administradores pueden eliminar cualquier comprobante
            logger.info(f"Administrador eliminando comprobante de usuario: {existing_user}")
            await receipt_service.delete_receipt(transaction_number, user_id=None)
        else:
            # Los usuarios normales solo pueden eliminar sus propios comprobantes
            if existing_user != user_id:
                raise HTTPException(
                    status_code=403, 
                    detail="No tienes permisos para eliminar este comprobante"
                )
            logger.info(f"Usuario eliminando su propio comprobante")
            await receipt_service.delete_receipt(transaction_number, user_id=user_id)
        
        logger.info(f"Comprobante {transaction_number} eliminado exitosamente")
        return {"success": True, "message": "Comprobante eliminado exitosamente"}
        
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error inesperado al eliminar comprobante: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")