import logging
from datetime import datetime
from typing import List, Dict
from pymongo import MongoClient, DESCENDING
from bson import ObjectId
from app.config import MONGO_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

class ReceiptService:
    def __init__(self):
        try:
            # CONFIGURACIÓN ROBUSTA SIMILAR A user_service.py
            logger.info("Conectando a MongoDB para receipts...")
            self.client = MongoClient(
                MONGO_URI,
                connect=False,  # No conectar inmediatamente
                serverSelectionTimeoutMS=30000,  # 30 segundos
                connectTimeoutMS=30000,
                socketTimeoutMS=30000,
                maxPoolSize=10,
                retryWrites=True,
                retryReads=True,
                maxIdleTimeMS=45000,
                waitQueueTimeoutMS=10000
            )
            
            self.db = self.client[DATABASE_NAME]
            self.receipts = self.db["receipts"]
            
            # Probar conexión
            try:
                self.client.admin.command('ping')
                logger.info("✅ Conexión exitosa a la base de datos para receipts")
            except Exception as ping_error:
                logger.warning(f"⚠️ No se pudo hacer ping a MongoDB (receipts): {ping_error}")
                # Continuar sin fallar, la conexión se probará en la primera operación
                
        except Exception as e:
            logger.error(f"❌ Error al inicializar conexión MongoDB (receipts): {e}")
            # No hacer raise aquí, permitir que el servicio se inicialice
            self.client = None
            self.db = None
            self.receipts = None

    def _ensure_connection(self):
        """Asegurar que la conexión esté disponible antes de usar"""
        if self.client is None or self.db is None or self.receipts is None:
            logger.error("Conexión a MongoDB no está inicializada")
            raise Exception("Error de conexión a la base de datos")

    def create_receipt(self, receipt_data: dict):
        """Crear comprobante - CORREGIDO para evitar números AUTO"""
        try:
            self._ensure_connection()
            
            # ✅ CORRECCIÓN CRÍTICA: NO generar números automáticos
            nro_transaccion = receipt_data.get('nro_transaccion', '').strip()
            
            if not nro_transaccion or nro_transaccion == '':
                # ❌ CAMBIO CRÍTICO: En lugar de generar AUTO, RECHAZAR
                logger.error("❌ Número de transacción vacío - rechazando comprobante")
                raise ValueError("Número de transacción es requerido y no puede estar vacío")
            
            # Actualizar el campo en receipt_data (por si acaso)
            receipt_data['nro_transaccion'] = nro_transaccion
            
            # ✅ MANTENER: Verificación de duplicados (esto está bien)
            existing = self.receipts.find_one({"nro_transaccion": nro_transaccion})
            if existing:
                logger.warning(f"⚠️ Número de transacción duplicado: {nro_transaccion}")
                raise ValueError(f"El número de transacción {nro_transaccion} ya existe")
            
            # ✅ MANTENER: Insertar comprobante
            result = self.receipts.insert_one(receipt_data)
            
            if result.inserted_id:
                logger.info(f"✅ Comprobante creado exitosamente: {result.inserted_id} - Nro: {nro_transaccion}")
                return result.inserted_id
            else:
                logger.error("❌ No se pudo insertar el comprobante")
                return None
                
        except Exception as e:
            logger.error(f"❌ Error al crear comprobante: {e}")
            return None

    def get_receipts_by_user(self, user_id: str) -> List[dict]:
        """Obtener comprobantes de un usuario específico (para cnb)"""
        try:
            self._ensure_connection()
            
            # ✅ CORRECCIÓN: user_id como STRING, no ObjectId
            receipts = list(self.receipts.find({
                "user_id": user_id  # ← CAMBIO: Sin ObjectId()
            }).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                # user_id ya es string, no necesita conversión
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes del usuario {user_id}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes del usuario: {e}")
            return []

    def get_all_receipts_with_corresponsal_info(self):
        """Obtener todos los comprobantes con información del corresponsal (admin/asesor)"""
        try:
            self._ensure_connection()
            
            receipts = list(self.receipts.find({}).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
                    
            logger.info(f"Todos los comprobantes obtenidos: {len(receipts)}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener todos los comprobantes: {e}")
            return []

    def delete_receipt(self, transaction_number: str) -> bool:
        """Eliminar comprobante por número de transacción (admin/asesor)"""
        try:
            self._ensure_connection()
            
            result = self.receipts.delete_one({"nro_transaccion": transaction_number})
            success = result.deleted_count > 0
            
            if success:
                logger.info(f"Comprobante eliminado: {transaction_number}")
            else:
                logger.warning(f"No se encontró comprobante para eliminar: {transaction_number}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar comprobante {transaction_number}: {e}")
            return False

    def delete_receipt_by_user(self, transaction_number: str, user_id: str) -> bool:
        """Eliminar comprobante solo si pertenece al usuario (cnb)"""
        try:
            self._ensure_connection()
            
            # ✅ CORRECCIÓN: user_id como STRING, no ObjectId
            result = self.receipts.delete_one({
                "nro_transaccion": transaction_number,
                "user_id": user_id  # ← CAMBIO: Sin ObjectId()
            })
            
            success = result.deleted_count > 0
            
            if success:
                logger.info(f"Comprobante eliminado por usuario {user_id}: {transaction_number}")
            else:
                logger.warning(f"Comprobante no encontrado o sin permisos: {transaction_number}")
            
            return success
            
        except Exception as e:
            logger.error(f"Error al eliminar comprobante por usuario: {e}")
            return False

    def get_receipts_by_date_and_user(self, date: str, user_id: str) -> List[dict]:
        """Obtener comprobantes por fecha Y usuario específico (cnb)"""
        try:
            self._ensure_connection()
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            query = {
                "fecha": {"$in": date_variations},
                "user_id": user_id  # ← CAMBIO: Sin ObjectId()
            }
            
            receipts = list(self.receipts.find(query).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                # user_id ya es string, no necesita conversión
            
            logger.info(f"Se obtuvieron {len(receipts)} comprobantes del usuario {user_id} para la fecha {date}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por fecha y usuario: {e}")
            return []

    def get_receipts_by_date_with_corresponsal(self, date: str) -> List[dict]:
        """Obtener comprobantes por fecha CON información del corresponsal (admin/asesor)"""
        try:
            self._ensure_connection()
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

    def generate_closing_report_by_user(self, date: str, user_id: str) -> dict:
        """Generar reporte de cierre solo para un usuario específico (cnb)"""
        try:
            self._ensure_connection()
            date_variations = [date, date.replace("-", "/"), date.replace("/", "-")]
            
            receipts = list(self.receipts.find({
                "fecha": {"$in": date_variations},
                "user_id": user_id  # ← CAMBIO: Sin ObjectId()
            }))
            
            return self._process_receipts_for_report(receipts, f"Usuario {user_id}")
            
        except Exception as e:
            logger.error(f"Error al generar reporte por usuario: {e}")
            return self._empty_report()

    def generate_closing_report(self, date: str) -> dict:
        """Generar reporte de cierre completo (admin/asesor)"""
        try:
            self._ensure_connection()
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

    # MANTENER ESTOS MÉTODOS (son útiles)
    def get_receipts_by_corresponsal(self, codigo_corresponsal: str) -> List[dict]:
        """Obtener comprobantes filtrados por código de corresponsal"""
        try:
            self._ensure_connection()
            
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

    def get_available_corresponsales(self) -> List[dict]:
        """Obtener lista de corresponsales que tienen comprobantes"""
        try:
            self._ensure_connection()
            
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

    def count_receipts_by_user(self, user_id: str):
        """Contar comprobantes de un usuario"""
        try:
            self._ensure_connection()
            
            count = self.receipts.count_documents({"user_id": user_id})  # ← CAMBIO: Sin ObjectId()
            logger.info(f"Usuario {user_id} tiene {count} comprobantes")
            return count
            
        except Exception as e:
            logger.error(f"Error al contar comprobantes del usuario {user_id}: {e}")
            return 0

    def get_receipts_by_date_range(self, start_date: str, end_date: str, user_id: str = None):
        """Obtener comprobantes por rango de fechas"""
        try:
            self._ensure_connection()
            
            query = {
                "fecha": {
                    "$gte": start_date,
                    "$lte": end_date
                }
            }
            
            if user_id:
                query["user_id"] = user_id  # ← CAMBIO: Sin ObjectId()
            
            receipts = list(self.receipts.find(query).sort("created_at", DESCENDING))
            
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                # user_id ya es string, no necesita conversión
            
            logger.info(f"Comprobantes obtenidos para rango {start_date}-{end_date}: {len(receipts)}")
            return receipts
            
        except Exception as e:
            logger.error(f"Error al obtener comprobantes por rango de fechas: {e}")
            return []