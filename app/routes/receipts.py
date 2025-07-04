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
    """Crear nuevo comprobante - CORREGIDO con debug"""
    try:
        user_id = current_user.get("sub")
        user_info = user_service.get_user_info(user_id)
        
        if not user_info:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        # ✅ CORRECCIÓN CRÍTICA: Usar .dict(by_alias=True) para convertir correctamente
        receipt_dict = receipt.dict(by_alias=True)
        
        # 🔍 DEBUG: Mostrar qué datos llegan
        print(f"🔍 Datos del receipt recibidos: {receipt_dict.keys()}")
        print(f"🔍 nro_transaccion en datos: {receipt_dict.get('nro_transaccion', 'NO ENCONTRADO')}")
        print(f"🔍 nroTransaccion en datos: {receipt_dict.get('nroTransaccion', 'NO ENCONTRADO')}")
        
        receipt_data = {
            **receipt_dict,  # ✅ USAR EL DICT CONVERTIDO
            "user_id": ObjectId(user_id),
            "created_at": datetime.utcnow(),
            "codigo_corresponsal": user_info.get("codigo_corresponsal", "SIN_CODIGO"),
            "nombre_corresponsal": user_info.get("nombre", "Sin nombre"),
            "nombre_local": user_info.get("nombre_local", "Sin local"),
            "rol_usuario": user_info.get("rol", "cnb")  
        }
        
        # 🔍 DEBUG: Mostrar datos finales que van al servicio
        print(f"🔍 Datos finales para crear comprobante:")
        print(f"   nro_transaccion: {receipt_data.get('nro_transaccion', 'NO ENCONTRADO')}")
        print(f"   user_id: {receipt_data.get('user_id')}")
        print(f"   codigo_corresponsal: {receipt_data.get('codigo_corresponsal')}")
        
        # Validar que el usuario tenga código de corresponsal (para CNB)
        if (user_info.get("rol") == "cnb" and 
            not user_info.get("codigo_corresponsal")):
            raise HTTPException(
                status_code=400, 
                detail="Usuario CNB sin código de corresponsal asignado"
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
    - Admin/Asesor: Ve todos los comprobantes con información del corresponsal
    - Lector: Ve solo sus propios comprobantes
    """
    try:
        user_role = current_user.get("rol")
        user_id = current_user.get("sub")
        
        if user_role in ["admin", "asesor"]:  
              # Admin/Asesor ve TODOS los comprobantes
            receipts = receipt_service.get_all_receipts_with_corresponsal_info()
        else:
            # CNB ven solo sus propios comprobantes
            receipts = receipt_service.get_receipts_by_user(user_id)
        
        return {
            "data": receipts,
            "count": len(receipts),
            "user_role": user_role
        }
        
    except Exception as e:
        print(f"Error al obtener comprobantes: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# NUEVO: Endpoint específico para filtrar por corresponsal 
@router.get("/corresponsal/{codigo_corresponsal}", response_model=dict)
async def get_receipts_by_corresponsal(
    codigo_corresponsal: str, 
    current_user=Depends(role_required(["admin", "asesor"]))  
):
    """
    Obtener comprobantes filtrados por código de corresponsal (solo admin/asesor)
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

# NUEVO: Obtener lista de corresponsales disponibles 
@router.get("/corresponsales", response_model=dict)
async def get_available_corresponsales(current_user=Depends(role_required(["admin", "asesor"]))):  # Cambiado  # Cambiado
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
        
        if user_role in ["admin", "asesor"]:
            # Admin/asesor ve todos los comprobantes de la fecha
            receipts = receipt_service.get_receipts_by_date_with_corresponsal(date)
        else:
            # cnbs ven solo sus comprobantes de la fecha
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

# NUEVO: Reportes filtrados por corresponsal (solo admin/asesor)
@router.get("/report/{date}/corresponsal/{codigo_corresponsal}", response_model=dict)
async def get_closing_report_by_corresponsal(
    date: str, 
    codigo_corresponsal: str,
    current_user=Depends(role_required(["admin", "asesor"]))
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
        
        if user_role in ["admin", "asesor"]:
            # Admin/asesor ve reporte completo
            report_data = receipt_service.generate_closing_report(date)
        else:
            # cnbs ven solo reporte de sus comprobantes
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
        if user_role in ["admin", "asesor"]:
            # Admin/asesor puede eliminar cualquier comprobante
            success = receipt_service.delete_receipt(transaction_number)
        else:
            # cnbs solo pueden eliminar sus propios comprobantes
            success = receipt_service.delete_receipt_by_user(transaction_number, user_id)
        
        if success:
            return {"message": "Comprobante eliminado exitosamente"}
        else:
            raise HTTPException(status_code=404, detail="Comprobante no encontrado o sin permisos")
            
    except Exception as e:
        print(f"Error al eliminar comprobante: {e}")
        raise HTTPException(status_code=500, detail=str(e))