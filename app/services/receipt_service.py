# app/services/receipt_service.py - ACTUALIZADO CON MÉTODOS PARA CORRESPONSALES

import logging
from datetime import datetime
from typing import List, Optional, Dict
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para receipts...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.receipts = self.db["receipts"]
            self.users = self.db["users"]  # Para hacer joins/lookups
            logger.info("Conexión exitosa a la base de datos")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def create_receipt(self, receipt_data: dict) -> Optional[str]:
        """Crear un nuevo comprobante CON información del corresponsal"""
        try:
            # Validar que no exista el mismo número de transacción
            existing_receipt = self.receipts.find_one({
                "nro_transaccion": receipt_data["nro_transaccion"]
            })
            
            if existing_receipt:
                raise ValueError("Ya existe un comprobante con este número de transacción")
            
            result = self.receipts.insert_one(receipt_data)
            
            logger.info(f"Comprobante creado por corresponsal {receipt_data.get('codigo_corresponsal', 'N/A')}: {receipt_data['nro_transaccion']}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Error al crear comprobante: {e}")
            raise

    def get_all_receipts_with_corresponsal_info(self) -> List[dict]:
        """Obtener TODOS los comprobantes con información del corresponsal (solo admin/asesor)"""
        try:
            receipts = list(self.receipts.find({}).sort("created_at", DESCENDING))
            
            # Convertir ObjectId a string
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes con información de corresponsal")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes: {e}")
            return []

    def get_receipts_by_user(self, user_id: str) -> List[dict]:
        """Obtener comprobantes de un usuario específico (para cnbes)"""
        try:
            receipts = list(self.receipts.find({
                "user_id": user_id
            }).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes del usuario {user_id}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes del usuario: {e}")
            return []

    def get_receipts_by_corresponsal(self, codigo_corresponsal: str) -> List[dict]:
        """Obtener comprobantes filtrados por código de corresponsal"""
        try:
            receipts = list(self.receipts.find({
                "codigo_corresponsal": codigo_corresponsal
            }).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes del corresponsal {codigo_corresponsal}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por corresponsal: {e}")
            return []

    def get_available_corresponsales(self) -> List[str]:
        """Obtener lista de corresponsales que tienen comprobantes"""
        try:
            pipeline = [
                {
                    "$match": {
                        "codigo_corresponsal": {"$exists": True, "$ne": None}
                    }
                },
                {
                    "$group": {
                        "_id": "$codigo_corresponsal",
                        "count": {"$sum": 1},
                        "nombre_corresponsal": {"$first": "$nombre_corresponsal"},
                        "nombre_local": {"$first": "$nombre_local"}
                    }
                },
                {
                    "$sort": {"_id": 1}
                }
            ]
            
            result = list(self.receipts.aggregate(pipeline))
            
            # Formatear resultado
            corresponsales = []
            for item in result:
                corresponsales.append({
                    "codigo": item["_id"],
                    "nombre": item.get("nombre_corresponsal", "Sin nombre"),
                    "nombre_local": item.get("nombre_local", "Sin local"),
                    "total_comprobantes": item["count"]
                })
            
            logger.info(f"Se encontraron {len(corresponsales)} corresponsales con comprobantes")
            return corresponsales
            
        except Exception as e:
            logger.error(f"Error al obtener corresponsales: {e}")
            return []

    def get_receipts_by_date_with_corresponsal(self, date: str) -> List[dict]:
        """Obtener comprobantes por fecha CON información del corresponsal (admin/asesor)"""
        try:
            # Normalizar formatos de fecha
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {"fecha": {"$in": date_variations}}
            receipts = list(self.receipts.find(query).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes para la fecha {date}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por fecha: {e}")
            return []

    def get_receipts_by_date_and_user(self, date: str, user_id: str) -> List[dict]:
        """Obtener comprobantes por fecha Y usuario específico (cnbes)"""
        try:
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {
                "fecha": {"$in": date_variations},
                "user_id": user_id
            }
            
            receipts = list(self.receipts.find(query).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes del usuario {user_id} para la fecha {date}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por fecha y usuario: {e}")
            return []

    def generate_closing_report_by_corresponsal(self, date: str, codigo_corresponsal: str) -> dict:
        """Generar reporte de cierre filtrado por corresponsal"""
        try:
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {
                "fecha": {"$in": date_variations},
                "codigo_corresponsal": codigo_corresponsal
            }
            
            receipts = list(self.receipts.find(query))
            
            return self._process_receipts_for_report(receipts, f"Corresponsal {codigo_corresponsal}")
            
        except Exception as e:
            logger.error(f"Error al generar reporte por corresponsal: {e}")
            return self._empty_report()

    def generate_closing_report_by_user(self, date: str, user_id: str) -> dict:
        """Generar reporte de cierre para un usuario específico (cnbes)"""
        try:
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {
                "fecha": {"$in": date_variations},
                "user_id": user_id
            }
            
            receipts = list(self.receipts.find(query))
            
            return self._process_receipts_for_report(receipts, f"Usuario {user_id}")
            
        except Exception as e:
            logger.error(f"Error al generar reporte por usuario: {e}")
            return self._empty_report()

    def generate_closing_report(self, date: str) -> dict:
        """Generar reporte de cierre completo (admin/asesor)"""
        try:
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {"fecha": {"$in": date_variations}}
            receipts = list(self.receipts.find(query))
            
            return self._process_receipts_for_report(receipts, "Todos")
            
        except Exception as e:
            logger.error(f"Error al generar reporte completo: {e}")
            return self._empty_report()

    def _process_receipts_for_report(self, receipts: List[dict], scope: str) -> dict:
        """Procesar lista de comprobantes para generar reporte"""
        if not receipts:
            return self._empty_report()

        # Clasificar en ingresos y egresos
        income_types = {'DEPOSITO', 'PAGO DE SERVICIO', 'RECARGA CLARO', 'ENVIO GIRO'}
        expense_types = {'RETIRO', 'EFECTIVO MOVIL', 'PAGO GIRO'}

        incomes = {}
        income_count = {}
        expenses = {}
        expense_count = {}

        total_incomes = 0.0
        total_expenses = 0.0
        total_income_count = 0
        total_expense_count = 0

        for receipt in receipts:
            tipo = receipt.get('tipo', '').upper()
            valor = float(receipt.get('valor_total', 0))

            if tipo in income_types:
                incomes[tipo] = incomes.get(tipo, 0) + valor
                income_count[tipo] = income_count.get(tipo, 0) + 1
                total_incomes += valor
                total_income_count += 1
            elif tipo in expense_types:
                expenses[tipo] = expenses.get(tipo, 0) + valor
                expense_count[tipo] = expense_count.get(tipo, 0) + 1
                total_expenses += valor
                total_expense_count += 1

        return {
            'incomes': incomes,
            'incomeCount': income_count,
            'expenses': expenses,
            'expenseCount': expense_count,
            'totalIncomes': total_incomes,
            'totalExpenses': total_expenses,
            'totalIncomeCount': total_income_count,
            'totalExpenseCount': total_expense_count,
            'saldoEnCaja': total_incomes - total_expenses,
            'count': len(receipts),
            'scope': scope
        }

    def _empty_report(self) -> dict:
        """Retornar reporte vacío"""
        return {
            'incomes': {},
            'incomeCount': {},
            'expenses': {},
            'expenseCount': {},
            'totalIncomes': 0.0,
            'totalExpenses': 0.0,
            'totalIncomeCount': 0,
            'totalExpenseCount': 0,
            'saldoEnCaja': 0.0,
            'count': 0,
            'scope': 'Ninguno'
        }

    def delete_receipt(self, transaction_number: str) -> bool:
        """Eliminar comprobante (admin/asesor)"""
        try:
            result = self.receipts.delete_one({"nro_transaccion": transaction_number})
            
            success = result.deleted_count > 0
            if success:
                logger.info(f"Comprobante eliminado: {transaction_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar comprobante: {e}")
            return False

    def delete_receipt_by_user(self, transaction_number: str, user_id: str) -> bool:
        """Eliminar comprobante solo si pertenece al usuario (cnbes)"""
        try:
            result = self.receipts.delete_one({
                "nro_transaccion": transaction_number,
                "user_id": user_id
            })
            
            success = result.deleted_count > 0
            if success:
                logger.info(f"Comprobante eliminado por usuario {user_id}: {transaction_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar comprobante por usuario: {e}")
            return False

    def get_receipts_stats_by_corresponsal(self) -> List[dict]:
        """Obtener estadísticas de comprobantes agrupadas por corresponsal (admin/asesor)"""
        try:
            pipeline = [
                {
                    "$match": {
                        "codigo_corresponsal": {"$exists": True, "$ne": None}
                    }
                },
                {
                    "$group": {
                        "_id": "$codigo_corresponsal",
                        "total_comprobantes": {"$sum": 1},
                        "valor_total": {"$sum": "$valor_total"},
                        "nombre_corresponsal": {"$first": "$nombre_corresponsal"},
                        "nombre_local": {"$first": "$nombre_local"},
                        "ultimo_comprobante": {"$max": "$created_at"}
                    }
                },
                {
                    "$sort": {"total_comprobantes": -1}
                }
            ]
            
            result = list(self.receipts.aggregate(pipeline))
            
            # Formatear resultado
            stats = []
            for item in result:
                stats.append({
                    "codigo_corresponsal": item["_id"],
                    "nombre_corresponsal": item.get("nombre_corresponsal", "Sin nombre"),
                    "nombre_local": item.get("nombre_local", "Sin local"),
                    "total_comprobantes": item["total_comprobantes"],
                    "valor_total": round(item["valor_total"], 2),
                    "ultimo_comprobante": item.get("ultimo_comprobante")
                })
            
            logger.info(f"Estadísticas generadas para {len(stats)} corresponsales")
            return stats
            
        except Exception as e:
            logger.error(f"Error al obtener estadísticas por corresponsal: {e}")
            return []

    # MÉTODOS EXISTENTES (mantenidos para compatibilidad)
    def get_all_receipts(self) -> List[dict]:
        """Método legacy - usar get_all_receipts_with_corresponsal_info"""
        return self.get_all_receipts_with_corresponsal_info()

    def get_receipts_by_date(self, date: str) -> List[dict]:
        """Método legacy - usar get_receipts_by_date_with_corresponsal"""
        return self.get_receipts_by_date_with_corresponsal(date)