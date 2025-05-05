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
    
    async def get_all_receipts(self, user_id: Optional[str] = None) -> List[dict]:
        """
        Obtiene todos los comprobantes, opcionalmente filtrados por usuario.
        
        Args:
            user_id: ID del usuario para filtrar los comprobantes
            
        Returns:
            Lista de comprobantes encontrados
        """
        try:
            # Crear filtro basado en user_id si se proporciona
            filter_query = {}
            if user_id:
                filter_query["user_id"] = user_id
                logger.info(f"Filtrando comprobantes para el usuario: {user_id}")
            
            receipts = list(self.receipts.find(filter_query).sort("created_at", -1))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
            
            logger.info(f"Se encontraron {len(receipts)} comprobantes{' para el usuario: ' + user_id if user_id else ''}")
            return receipts
        except Exception as e:
            logger.error(f"Error al obtener comprobantes: {e}")
            return []
    
    async def get_receipts_by_date(self, date_str: str, user_id: Optional[str] = None) -> List[dict]:
        """
        Obtiene comprobantes por fecha, opcionalmente filtrados por usuario.
        
        Args:
            date_str: Fecha en formato dd/mm/aaaa
            user_id: ID del usuario para filtrar los comprobantes
            
        Returns:
            Lista de comprobantes encontrados
        """
        try:
            logger.info(f"Buscando comprobantes para la fecha: {date_str}{' y usuario: ' + user_id if user_id else ''}")
            
            # Crear filtro con fecha y, opcionalmente, user_id
            filter_query = {"fecha": date_str}
            if user_id:
                filter_query["user_id"] = user_id
            
            receipts = list(self.receipts.find(filter_query).sort("created_at", -1))
            
            logger.info(f"Se encontraron {len(receipts)} comprobantes para la fecha {date_str}{' y usuario: ' + user_id if user_id else ''}")
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
            return receipts
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por fecha: {e}")
            return []
    
    async def create_receipt(self, receipt: ReceiptModel, user_id: Optional[str] = None) -> dict:
        """
        Crea un nuevo comprobante, asociándolo a un usuario si se proporciona.
        
        Args:
            receipt: Modelo del comprobante a crear
            user_id: ID del usuario que crea el comprobante
            
        Returns:
            Comprobante creado
        """
        try:
            receipt_dict = receipt.dict(by_alias=True)
            receipt_dict["created_at"] = datetime.now()
            
            # Asignar user_id si se proporciona
            if user_id:
                receipt_dict["user_id"] = user_id
                logger.info(f"Asignando comprobante al usuario: {user_id}")
            
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
    async def get_receipt_by_transaction(self, transaction_number: str, user_id: Optional[str] = None) -> Optional[dict]:
        """
        Busca un comprobante por número de transacción, opcionalmente filtrado por usuario.
        
        Args:
            transaction_number: Número de transacción a buscar
            user_id: ID del usuario para filtrar los comprobantes
            
        Returns:
            Comprobante encontrado o None
        """
        try:
            logger.info(f"Buscando comprobante con número de transacción: '{transaction_number}'{' para usuario: ' + user_id if user_id else ''}")
            
            # Crear filtro con nro_transaccion y, opcionalmente, user_id
            filter_query = {"nro_transaccion": transaction_number}
            if user_id:
                filter_query["user_id"] = user_id
            
            receipt = self.receipts.find_one(filter_query)
            
            if receipt:
                logger.info(f"Comprobante encontrado: {receipt.get('_id')}")
                receipt["_id"] = str(receipt["_id"])
                return receipt
            else:
                logger.info(f"No se encontró ningún comprobante con transacción: {transaction_number}{' para usuario: ' + user_id if user_id else ''}")
                return None
        except Exception as e:
            logger.error(f"Error al buscar comprobante: {e}")
            return None
    
    # Método para eliminar recibo
    async def delete_receipt(self, transaction_number: str, user_id: Optional[str] = None) -> bool:
        """
        Elimina un comprobante por número de transacción, opcionalmente filtrado por usuario.
        
        Args:
            transaction_number: Número de transacción a eliminar
            user_id: ID del usuario para filtrar los comprobantes
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Intentando eliminar comprobante con transacción: '{transaction_number}'{' para usuario: ' + user_id if user_id else ''}")
            
            # Crear filtro con nro_transaccion y, opcionalmente, user_id
            filter_query = {"nro_transaccion": transaction_number}
            if user_id:
                filter_query["user_id"] = user_id
            
            result = self.receipts.delete_one(filter_query)
            
            success = result.deleted_count > 0
            logger.info(f"Resultado de eliminación: {success} (deleted_count: {result.deleted_count})")
            return success
        except Exception as e:
            logger.error(f"Error al eliminar comprobante: {e}")
            return False
    
    async def generate_closing_report(self, date_str: str, user_id: Optional[str] = None) -> dict:
        """
        Genera un reporte de cierre para una fecha específica, opcionalmente filtrado por usuario.
        
        Args:
            date_str: Fecha en formato dd/mm/aaaa
            user_id: ID del usuario para filtrar los comprobantes
            
        Returns:
            Diccionario con el reporte generado
        """
        try:
            logger.info(f"Generando reporte para la fecha: {date_str}{' y usuario: ' + user_id if user_id else ''}")
            
            receipts = await self.get_receipts_by_date(date_str, user_id)
            
            if not receipts:
                logger.info(f"No hay comprobantes para la fecha {date_str}{' y usuario: ' + user_id if user_id else ''}")
                return {
                    "summary": {},
                    "total": 0.0,
                    "date": date_str,
                    "count": 0,
                    "user_id": user_id if user_id else None
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
            
            logger.info(f"Reporte generado para {date_str}{' y usuario: ' + user_id if user_id else ''}: {len(receipts)} comprobantes, total: {total}")
            return {
                "summary": summary,
                "total": total,
                "date": date_str,
                "count": len(receipts),
                "user_id": user_id if user_id else None
            }
        except Exception as e:
            logger.error(f"Error al generar reporte de cierre: {e}")
            return {
                "summary": {},
                "total": 0.0,
                "date": date_str,
                "count": 0,
                "error": str(e),
                "user_id": user_id if user_id else None
            }