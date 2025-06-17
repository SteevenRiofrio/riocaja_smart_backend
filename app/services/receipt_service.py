# app/services/receipt_service.py - MEJORADO con validación global
from datetime import datetime
from typing import List, Optional
import logging
from pymongo import MongoClient, ASCENDING
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
            
            # ������ MEJORA: Crear índice único compuesto para optimizar las consultas
            self._ensure_indexes()
            
            logger.info(f"Conexión exitosa a la base de datos: {DATABASE_NAME}")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise
    
    def _ensure_indexes(self):
        """Crear índices para optimizar las consultas y garantizar unicidad"""
        try:
            # Índice único en número de transacción para prevenir duplicados globalmente
            self.receipts.create_index(
                "nro_transaccion", 
                unique=True, 
                name="unique_transaction_number"
            )
            
            # Índice compuesto para consultas por usuario y fecha
            self.receipts.create_index(
                [("user_id", ASCENDING), ("fecha", ASCENDING)], 
                name="user_date_index"
            )
            
            # Índice simple en fecha para reportes globales
            self.receipts.create_index("fecha", name="date_index")
            
            # Índice simple en user_id para consultas por usuario
            self.receipts.create_index("user_id", name="user_index")
            
            logger.info("Índices creados/verificados exitosamente")
        except Exception as e:
            logger.warning(f"Error al crear índices (puede ser normal si ya existen): {e}")
    
    async def get_all_receipts(self, user_id: Optional[str] = None) -> List[dict]:
        """
        Obtiene todos los comprobantes, opcionalmente filtrados por usuario.
        
        Args:
            user_id: ID del usuario para filtrar los comprobantes (None = todos)
            
        Returns:
            Lista de comprobantes encontrados
        """
        try:
            # Crear filtro basado en user_id si se proporciona
            filter_query = {}
            if user_id:
                filter_query["user_id"] = user_id
                logger.info(f"Filtrando comprobantes para el usuario: {user_id}")
            else:
                logger.info("Obteniendo TODOS los comprobantes del sistema")
            
            receipts = list(self.receipts.find(filter_query).sort("created_at", -1))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
            
            logger.info(f"Se encontraron {len(receipts)} comprobantes{' para el usuario: ' + user_id if user_id else ' en total'}")
            return receipts
        except Exception as e:
            logger.error(f"Error al obtener comprobantes: {e}")
            return []
    
    async def get_receipts_by_date(self, date_str: str, user_id: Optional[str] = None) -> List[dict]:
        """
        Obtiene comprobantes por fecha, opcionalmente filtrados por usuario.
        
        Args:
            date_str: Fecha en formato dd/mm/yyyy
            user_id: ID del usuario para filtrar los comprobantes (None = todos)
            
        Returns:
            Lista de comprobantes encontrados
        """
        try:
            logger.info(f"Buscando comprobantes para la fecha: {date_str}{' y usuario: ' + user_id if user_id else ' (todos los usuarios)'}")
            
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
            
        Raises:
            Exception: Si hay un error de duplicado o cualquier otro error
        """
        try:
            receipt_dict = receipt.dict(by_alias=True)
            receipt_dict["created_at"] = datetime.now()
            
            # Asignar user_id si se proporciona
            if user_id:
                receipt_dict["user_id"] = user_id
                logger.info(f"Asignando comprobante al usuario: {user_id}")
            
            logger.info(f"Intentando guardar comprobante: {receipt_dict.get('nro_transaccion')}")
            
            # ������ La unicidad se garantiza por el índice único en la base de datos
            # Si hay duplicado, MongoDB lanzará una excepción automáticamente
            result = self.receipts.insert_one(receipt_dict)
            created_receipt = self.receipts.find_one({"_id": result.inserted_id})
            
            if created_receipt:
                created_receipt["_id"] = str(created_receipt["_id"])
                logger.info(f"Comprobante guardado exitosamente con ID: {created_receipt['_id']}")
                return created_receipt
            else:
                logger.error("No se pudo recuperar el comprobante guardado")
                return receipt_dict
                
        except Exception as e:
            # Detectar errores de duplicado de MongoDB
            if "duplicate key error" in str(e) or "E11000" in str(e):
                logger.warning(f"Intento de crear comprobante duplicado: {receipt.nroTransaccion}")
                raise Exception(f"El número de transacción {receipt.nroTransaccion} ya existe en el sistema")
            else:
                logger.error(f"Error al crear comprobante: {e}")
                raise
    
    async def get_receipt_by_transaction(self, transaction_number: str, user_id: Optional[str] = None) -> Optional[dict]:
        """
        Busca un comprobante por número de transacción, opcionalmente filtrado por usuario.
        
        Args:
            transaction_number: Número de transacción a buscar
            user_id: ID del usuario para filtrar los comprobantes (None = buscar globalmente)
            
        Returns:
            Comprobante encontrado o None
        """
        try:
            logger.info(f"Buscando comprobante con número de transacción: '{transaction_number}'{' para usuario: ' + user_id if user_id else ' (búsqueda global)'}")
            
            # Crear filtro con nro_transaccion y, opcionalmente, user_id
            filter_query = {"nro_transaccion": transaction_number}
            if user_id:
                filter_query["user_id"] = user_id
            
            receipt = self.receipts.find_one(filter_query)
            
            if receipt:
                logger.info(f"Comprobante encontrado: {receipt.get('_id')} (usuario: {receipt.get('user_id', 'N/A')})")
                receipt["_id"] = str(receipt["_id"])
                return receipt
            else:
                logger.info(f"No se encontró comprobante con transacción: {transaction_number}{' para usuario: ' + user_id if user_id else ' en el sistema'}")
                return None
        except Exception as e:
            logger.error(f"Error al buscar comprobante: {e}")
            return None
    
    async def delete_receipt(self, transaction_number: str, user_id: Optional[str] = None) -> bool:
        """
        Elimina un comprobante por número de transacción, opcionalmente filtrado por usuario.
        
        Args:
            transaction_number: Número de transacción a eliminar
            user_id: ID del usuario para filtrar los comprobantes (None = eliminar globalmente)
            
        Returns:
            True si se eliminó correctamente, False en caso contrario
        """
        try:
            logger.info(f"Intentando eliminar comprobante con transacción: '{transaction_number}'{' para usuario: ' + user_id if user_id else ' (eliminación global)'}")
            
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
            date_str: Fecha en formato dd/mm/yyyy
            user_id: ID del usuario para filtrar los comprobantes (None = reporte global)
            
        Returns:
            Diccionario con el reporte generado
        """
        try:
            logger.info(f"Generando reporte para la fecha: {date_str}{' y usuario: ' + user_id if user_id else ' (reporte global)'}")
            
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
    
    # ������ NUEVO: Método para obtener estadísticas del sistema
    async def get_system_stats(self) -> dict:
        """
        Obtiene estadísticas generales del sistema.
        
        Returns:
            Diccionario con estadísticas del sistema
        """
        try:
            # Conteo total de comprobantes
            total_receipts = self.receipts.count_documents({})
            
            # Conteo por usuario
            pipeline = [
                {"$group": {"_id": "$user_id", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            user_stats = list(self.receipts.aggregate(pipeline))
            
            # Conteo por tipo
            pipeline = [
                {"$group": {"_id": "$tipo", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}}
            ]
            type_stats = list(self.receipts.aggregate(pipeline))
            
            return {
                "total_receipts": total_receipts,
                "users_with_receipts": len(user_stats),
                "user_stats": user_stats,
                "type_stats": type_stats
            }
        except Exception as e:
            logger.error(f"Error al obtener estadísticas del sistema: {e}")
            return {
                "total_receipts": 0,
                "users_with_receipts": 0,
                "user_stats": [],
                "type_stats": [],
                "error": str(e)
            }