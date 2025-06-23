# app/routes/receipts.py - ACTUALIZADO CON INFORMACIÓN DEL CORRESPONSAL

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from datetime import datetime
from bson import ObjectId
from app.services.receipt_service import ReceiptService
from app.services.user_service import UserService
from app.middlewares.auth_middleware import get_current_user, role_required
from app.models.receipt import ReceiptModel

router = APIRouter()

# Inicializar servicios
receipt_service = ReceiptService()
user_service = UserService()

@router.post("/", response_model=dict)
async def create_receipt(receipt: ReceiptModel, current_user=Depends(get_current_user)):
    """
    Crear un nuevo comprobante - ACTUALIZADO CON INFORMACIÓN DEL CORRESPONSAL
    """
    try:
        user_id = current_user.get("sub")
        
        # OBTENER INFORMACIÓN COMPLETA DEL USUARIO ACTUAL
        user_info = user_service.get_user_info(user_id)
        if not user_info:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # CREAR EL COMPROBANTE CON INFORMACIÓN DEL CORRESPONSAL
        receipt_data = {
            "fecha": receipt.fecha,
            "hora": receipt.hora,
            "tipo": receipt.tipo,
            "nro_transaccion": receipt.nroTransaccion,
            "valor_total": receipt.valorTotal,
            "full_text": receipt.fullText,
            
            # ✅ INFORMACIÓN DEL USUARIO/CORRESPONSAL (NUEVOS CAMPOS)
            "user_id": user_id,
            "codigo_corresponsal": user_info.get("codigo_corresponsal"),
            "nombre_corresponsal": user_info.get("nombre"),
            "nombre_local": user_info.get("nombre_local"),
            "email_usuario": user_info.get("email"),
            
            # Metadatos
            "created_at": datetime.utcnow(),
            "rol_usuario": user_info.get("rol", "lector")
        }
        
        # Validar que el usuario tenga código de corresponsal (para lectores)
        if (user_info.get("rol") == "lector" and 
            not user_info.get("codigo_corresponsal")):
            raise HTTPException(
                status_code=400, 
                detail="Usuario sin código de corresponsal asignado"
            )
        
        result = receipt_service.create_receipt(receipt_data)
        
        if result:
            return {
                "message": "Comprobante creado exitosamente",
                "receipt_id": str(result),
                "codigo_corresponsal": user_info.get("codigo_corresponsal"),
                "nombre_corresponsal": user_info.get("nombre")
            }
        else:
            raise HTTPException(status_code=400, detail="Error al crear comprobante")
            
    except Exception as e:
        print(f"Error al crear comprobante: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=dict)
async def get_all_receipts(current_user=Depends(get_current_user)):
    """
    Obtener comprobantes según el rol del usuario
    - Admin/Operador: Ve todos los comprobantes con información del corresponsal
    - Lector: Ve solo sus propios comprobantes
    """
    try:
        user_role = current_user.get("rol")
        user_id = current_user.get("sub")
        
        if user_role in ["admin", "operador"]:
            # Admin/Operador ve TODOS los comprobantes con información del corresponsal
            receipts = receipt_service.get_all_receipts_with_corresponsal_info()
        else:
            # Lectores ven solo sus propios comprobantes
            receipts = receipt_service.get_receipts_by_user(user_id)
        
        return {
            "data": receipts,
            "count": len(receipts),
            "user_role": user_role
        }
        
    except Exception as e:
        print(f"Error al obtener comprobantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Endpoint específico para filtrar por corresponsal (solo admin/operador)
@router.get("/corresponsal/{codigo_corresponsal}", response_model=dict)
async def get_receipts_by_corresponsal(
    codigo_corresponsal: str, 
    current_user=Depends(role_required(["admin", "operador"]))
):
    """
    Obtener comprobantes filtrados por código de corresponsal (solo admin/operador)
    """
    try:
        receipts = receipt_service.get_receipts_by_corresponsal(codigo_corresponsal)
        
        return {
            "data": receipts,
            "count": len(receipts),
            "codigo_corresponsal": codigo_corresponsal
        }
        
    except Exception as e:
        print(f"Error al obtener comprobantes por corresponsal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Obtener lista de corresponsales disponibles (solo admin/operador)
@router.get("/corresponsales", response_model=dict)
async def get_available_corresponsales(current_user=Depends(role_required(["admin", "operador"]))):
    """
    Obtener lista de corresponsales que tienen comprobantes
    """
    try:
        corresponsales = receipt_service.get_available_corresponsales()
        
        return {
            "corresponsales": corresponsales,
            "count": len(corresponsales)
        }
        
    except Exception as e:
        print(f"Error al obtener corresponsales: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/date/{date}", response_model=dict)
async def get_receipts_by_date(date: str, current_user=Depends(get_current_user)):
    """
    Obtener comprobantes por fecha - ACTUALIZADO para considerar permisos
    """
    try:
        user_role = current_user.get("rol")
        user_id = current_user.get("sub")
        
        if user_role in ["admin", "operador"]:
            # Admin/Operador ve todos los comprobantes de la fecha
            receipts = receipt_service.get_receipts_by_date_with_corresponsal(date)
        else:
            # Lectores ven solo sus comprobantes de la fecha
            receipts = receipt_service.get_receipts_by_date_and_user(date, user_id)
        
        return {
            "data": receipts,
            "count": len(receipts),
            "date": date,
            "user_role": user_role
        }
        
    except Exception as e:
        print(f"Error al obtener comprobantes por fecha: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Reportes filtrados por corresponsal (solo admin/operador)
@router.get("/report/{date}/corresponsal/{codigo_corresponsal}", response_model=dict)
async def get_closing_report_by_corresponsal(
    date: str, 
    codigo_corresponsal: str,
    current_user=Depends(role_required(["admin", "operador"]))
):
    """
    Generar reporte de cierre filtrado por corresponsal específico
    """
    try:
        report_data = receipt_service.generate_closing_report_by_corresponsal(date, codigo_corresponsal)
        
        return {
            **report_data,
            "codigo_corresponsal": codigo_corresponsal,
            "date": date
        }
        
    except Exception as e:
        print(f"Error al generar reporte por corresponsal: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/report/{date}", response_model=dict)
async def get_closing_report(date: str, current_user=Depends(get_current_user)):
    """
    Generar reporte de cierre - ACTUALIZADO para considerar permisos
    """
    try:
        user_role = current_user.get("rol")
        user_id = current_user.get("sub")
        
        if user_role in ["admin", "operador"]:
            # Admin/Operador ve reporte completo
            report_data = receipt_service.generate_closing_report(date)
        else:
            # Lectores ven solo reporte de sus comprobantes
            report_data = receipt_service.generate_closing_report_by_user(date, user_id)
        
        return {
            **report_data,
            "date": date,
            "user_role": user_role
        }
        
    except Exception as e:
        print(f"Error al generar reporte: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{transaction_number}")
async def delete_receipt(transaction_number: str, current_user=Depends(get_current_user)):
    """
    Eliminar comprobante - ACTUALIZADO con verificación de permisos
    """
    try:
        user_role = current_user.get("rol")
        user_id = current_user.get("sub")
        
        # Verificar si el usuario puede eliminar este comprobante
        if user_role in ["admin", "operador"]:
            # Admin/Operador puede eliminar cualquier comprobante
            success = receipt_service.delete_receipt(transaction_number)
        else:
            # Lectores solo pueden eliminar sus propios comprobantes
            success = receipt_service.delete_receipt_by_user(transaction_number, user_id)
        
        if success:
            return {"message": "Comprobante eliminado exitosamente"}
        else:
            raise HTTPException(status_code=404, detail="Comprobante no encontrado o sin permisos")
            
    except Exception as e:
        print(f"Error al eliminar comprobante: {e}")
        raise HTTPException(status_code=500, detail=str(e))