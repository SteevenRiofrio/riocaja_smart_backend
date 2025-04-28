# app/services/receipt_service.py
from datetime import datetime
from typing import List, Optional
import logging
from pymongo import MongoClient
from pymongo.collection import Collection
from app.config import MONGO_URI, DATABASE_NAME
from app.models.receipt import ReceiptModel

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.receipts = self.db["receipts"]
            logger.info(f"Conexión exitosa a la base de datos: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise
    
    async def get_all_receipts(self) -> List[dict]:
        try:
            receipts = list(self.receipts.find().sort("created_at", -1))
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
            return receipts
        except Exception as e:
            logger.error(f"Error al obtener comprobantes: {e}")
            return []
    
    async def get_receipts_by_date(self, date_str: str) -> List[dict]:
        try:
            receipts = list(self.receipts.find({"fecha": date_str}).sort("created_at", -1))
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
            return receipts
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por fecha: {e}")
            return []
    
    async def create_receipt(self, receipt: ReceiptModel) -> dict:
        try:
            receipt_dict = receipt.dict(by_alias=True)
            receipt_dict["created_at"] = datetime.now()
            
            logger.info(f"Guardando comprobante: {receipt_dict.get('nro_transaccion')}")
            
            result = self.receipts.insert_one(receipt_dict)
            created_receipt = self.receipts.find_one({"_id": result.inserted_id})
            
            if created_receipt:
                created_receipt["_id"] = str(created_receipt["_id"])
                logger.info(f"Comprobante guardado con ID: {created_receipt['_id']}")
                return created_receipt
            else:
                logger.error("No se pudo recuperar el comprobante guardado")
                return receipt_dict
        except Exception as e:
            logger.error(f"Error al crear comprobante: {e}")
            raise
    
    # Método para buscar recibo por número de transacción
    async def get_receipt_by_transaction(self, transaction_number: str) -> Optional[dict]:
        try:
            logger.info(f"Buscando comprobante con número de transacción: '{transaction_number}'")
            
            # Buscar por el campo nro_transaccion
            receipt = self.receipts.find_one({"nro_transaccion": transaction_number})
            
            if receipt:
                logger.info(f"Comprobante encontrado: {receipt.get('_id')}")
                receipt["_id"] = str(receipt["_id"])
                return receipt
            else:
                logger.info(f"No se encontró ningún comprobante con transacción: {transaction_number}")
                return None
        except Exception as e:
            logger.error(f"Error al buscar comprobante: {e}")
            return None
    
    # Método para eliminar recibo
    async def delete_receipt(self, transaction_number: str) -> bool:
        try:
            logger.info(f"Intentando eliminar comprobante con transacción: '{transaction_number}'")
            
            # Buscar y eliminar por número de transacción
            result = self.receipts.delete_one({"nro_transaccion": transaction_number})
            
            success = result.deleted_count > 0
            logger.info(f"Resultado de eliminación: {success} (deleted_count: {result.deleted_count})")
            return success
        except Exception as e:
            logger.error(f"Error al eliminar comprobante: {e}")
            return False
    
    async def generate_closing_report(self, date_str: str) -> dict:
        try:
            receipts = await self.get_receipts_by_date(date_str)
            
            if not receipts:
                logger.info(f"No hay comprobantes para la fecha {date_str}")
                return {
                    "summary": {},
                    "total": 0.0,
                    "date": date_str,
                    "count": 0,
                }
            
            # Calcular total
            total = sum(receipt.get("valor_total", 0) for receipt in receipts)
            
            # Agrupar por tipo de transacción
            summary = {}
            for receipt in receipts:
                tipo = receipt.get("tipo", "Desconocido")
                if tipo in summary:
                    summary[tipo] += receipt.get("valor_total", 0)
                else:
                    summary[tipo] = receipt.get("valor_total", 0)
            
            logger.info(f"Reporte generado para {date_str}: {len(receipts)} comprobantes, total: {total}")
            return {
                "summary": summary,
                "total": total,
                "date": date_str,
                "count": len(receipts),
            }
        except Exception as e:
            logger.error(f"Error al generar reporte de cierre: {e}")
            return {
                "summary": {},
                "total": 0.0,
                "date": date_str,
                "count": 0,
                "error": str(e)
            }