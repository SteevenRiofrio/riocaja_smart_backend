# app/routes/receipts.py
from typing import List
from fastapi import APIRouter, HTTPException, Depends
from app.models.receipt import ReceiptModel
from app.services.receipt_service import ReceiptService

router = APIRouter()
receipt_service = ReceiptService()

# Get all receipts
@router.get("/", response_description="List all receipts")
async def get_receipts():
    receipts = await receipt_service.get_all_receipts()
    return {"data": receipts, "count": len(receipts)}

# Get receipts by date
@router.get("/date/{date}", response_description="Get receipts by date")
async def get_receipts_by_date(date: str):
    receipts = await receipt_service.get_receipts_by_date(date)
    return {"data": receipts, "count": len(receipts)}

# Create a new receipt
@router.post("/", response_description="Create a new receipt")
async def create_receipt(receipt: ReceiptModel):
    try:
        # Verificar si ya existe un comprobante con el mismo número de transacción
        existing = await receipt_service.get_receipt_by_transaction(receipt.nroTransaccion)
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe un comprobante con este número de transacción")
        
        created_receipt = await receipt_service.create_receipt(receipt)
        return {"success": True, "data": created_receipt}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Get closing report
@router.get("/report/{date}", response_description="Generate closing report")
async def get_closing_report(date: str):
    report = await receipt_service.generate_closing_report(date)
    return report

# Delete a receipt by transaction number
@router.delete("/{transaction_number}", response_description="Delete a receipt by transaction number")
async def delete_receipt(transaction_number: str):
    try:
        # Verificar si el comprobante existe
        existing = await receipt_service.get_receipt_by_transaction(transaction_number)
        if not existing:
            raise HTTPException(status_code=404, detail="Comprobante no encontrado")
        
        # Eliminar el comprobante
        await receipt_service.delete_receipt(transaction_number)
        return {"success": True, "message": "Comprobante eliminado exitosamente"}
    except HTTPException as http_exc:
        raise http_exc  # Asegúrate de no envolver errores HTTP en un error 500
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))