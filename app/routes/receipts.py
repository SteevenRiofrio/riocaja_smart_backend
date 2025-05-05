# app/routes/receipts.py
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
        user_id = user.get("sub")  # El ID del usuario está en el campo "sub" del token JWT
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

# Create a new receipt
@router.post("/", response_description="Create a new receipt")
async def create_receipt(receipt: ReceiptModel, user=Depends(get_current_user)):
    try:
        # Obtener ID del usuario del token JWT
        user_id = user.get("sub")
        logger.info(f"Usuario {user_id} creando nuevo comprobante")
        
        # Verificar si ya existe un comprobante con el mismo número de transacción
        # Solo administradores pueden ver todos los comprobantes, otros usuarios solo ven los suyos
        filter_user_id = None if user.get("rol") == "admin" else user_id
        existing = await receipt_service.get_receipt_by_transaction(receipt.nroTransaccion, filter_user_id)
        
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un comprobante con este número de transacción")
        
        # Crear comprobante asignándolo al usuario actual
        created_receipt = await receipt_service.create_receipt(receipt, user_id)
        return {"success": True, "data": created_receipt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Generate closing report with dash format (dd-mm-aaaa)
@router.get("/report/{date}", response_description="Generate closing report")
async def get_closing_report(date: str, user=Depends(get_current_user)):
    """
    Genera un reporte de cierre para una fecha específica.
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

# Delete a receipt by transaction number
@router.delete("/{transaction_number}", response_description="Delete a receipt by transaction number")
async def delete_receipt(transaction_number: str, user=Depends(get_current_user)):
    try:
        # Filtrar por usuario si no es administrador
        user_id = None
        if user.get("rol") != "admin":
            user_id = user.get("sub")
            logger.info(f"Filtrando eliminación para usuario: {user_id}")
        
        # Verificar si el comprobante existe
        existing = await receipt_service.get_receipt_by_transaction(transaction_number, user_id)
        
        if not existing:
            raise HTTPException(
                status_code=404, 
                detail="Comprobante no encontrado" if user.get("rol") == "admin" else "Comprobante no encontrado o no tienes permiso para eliminarlo"
            )
        
        # Eliminar el comprobante
        await receipt_service.delete_receipt(transaction_number, user_id)
        return {"success": True, "message": "Comprobante eliminado exitosamente"}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))