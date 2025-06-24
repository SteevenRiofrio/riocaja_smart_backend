# app/services/excel_report_service.py
import logging
import io
import base64
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pymongo import MongoClient
from bson import ObjectId
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import BarChart, PieChart, Reference
from openpyxl.drawing.image import Image
from app.config import MONGO_URI, DATABASE_NAME

logger = logging.getLogger(__name__)

class ExcelReportService:
    def __init__(self):
        try:
            logger.info("Conectando a MongoDB para reportes Excel...")
            self.client = MongoClient(MONGO_URI)
            self.db = self.client[DATABASE_NAME]
            self.receipts = self.db["receipts"]
            self.users = self.db["users"]
            logger.info("Conexión exitosa a la base de datos para reportes")
        except Exception as e:
            logger.error(f"Error al conectar a MongoDB: {e}")
            raise

    def generate_excel_report(self, 
                            start_date: str, 
                            end_date: str, 
                            report_type: str = "general",
                            user_id: Optional[str] = None,
                            user_role: str = "lector",
                            codigo_corresponsal: Optional[str] = None) -> bytes:
        """
        Genera reporte Excel completo
        
        Args:
            start_date: Fecha inicio (YYYY-MM-DD)
            end_date: Fecha fin (YYYY-MM-DD)
            report_type: general, daily, weekly, monthly
            user_id: ID del usuario (para lectores)
            user_role: Rol del usuario (admin, operador, lector)
            codigo_corresponsal: Filtro por corresponsal específico (admin/operador)
        """
        try:
            logger.info(f"Generando reporte Excel: {report_type} del {start_date} al {end_date}")
            
            # Obtener datos según permisos
            receipts_data = self._get_receipts_data(start_date, end_date, user_id, user_role, codigo_corresponsal)
            
            if not receipts_data:
                return self._generate_empty_report(start_date, end_date, report_type)
            
            # Crear workbook
            wb = Workbook()
            
            # Crear hojas según el tipo de reporte
            self._create_summary_sheet(wb, receipts_data, start_date, end_date, report_type, user_role)
            self._create_details_sheet(wb, receipts_data, user_role)
            self._create_analysis_sheet(wb, receipts_data, start_date, end_date, user_role)
            
            if report_type in ["weekly", "monthly"]:
                self._create_temporal_analysis_sheet(wb, receipts_data, report_type)
            
            if user_role in ["admin", "operador"]:
                self._create_corresponsal_sheet(wb, receipts_data)
            
            # Aplicar formato general
            self._apply_general_formatting(wb)
            
            # Convertir a bytes
            excel_buffer = io.BytesIO()
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            logger.info(f"Reporte Excel generado exitosamente: {len(receipts_data)} registros")
            return excel_buffer.getvalue()
            
        except Exception as e:
            logger.error(f"Error generando reporte Excel: {e}")
            raise

    def _get_receipts_data(self, start_date: str, end_date: str, 
                          user_id: Optional[str], user_role: str,
                          codigo_corresponsal: Optional[str]) -> List[Dict]:
        """Obtiene datos de comprobantes según filtros y permisos"""
        try:
            # Convertir fechas
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            # Construir query base
            query = {}
            
            # Filtro por fechas (buscar en múltiples formatos)
            date_variations = []
            current_date = start_dt
            while current_date <= end_dt:
                date_variations.extend([
                    current_date.strftime("%d/%m/%Y"),
                    current_date.strftime("%d-%m-%Y"),
                    current_date.strftime("%Y-%m-%d")
                ])
                current_date += timedelta(days=1)
            
            query["fecha"] = {"$in": date_variations}
            
            # Aplicar filtros según rol
            if user_role == "lector" and user_id:
                query["user_id"] = user_id
            elif codigo_corresponsal and user_role in ["admin", "operador"]:
                query["codigo_corresponsal"] = codigo_corresponsal
            
            # Obtener datos
            receipts = list(self.receipts.find(query).sort("created_at", -1))
            
            # Enriquecer datos
            for receipt in receipts:
                receipt["_id"] = str(receipt["_id"])
                if receipt.get("user_id"):
                    receipt["user_id"] = str(receipt["user_id"])
                
                # Calcular día de la semana
                try:
                    fecha_str = receipt.get("fecha", "")
                    if "/" in fecha_str:
                        fecha_dt = datetime.strptime(fecha_str, "%d/%m/%Y")
                    elif "-" in fecha_str:
                        fecha_dt = datetime.strptime(fecha_str, "%d-%m-%Y")
                    else:
                        fecha_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    
                    receipt["dia_semana"] = fecha_dt.strftime("%A")
                    receipt["semana_num"] = fecha_dt.isocalendar()[1]
                    receipt["mes_num"] = fecha_dt.month
                    receipt["año"] = fecha_dt.year
                    receipt["fecha_ordenable"] = fecha_dt
                except:
                    receipt["dia_semana"] = "Unknown"
                    receipt["semana_num"] = 0
                    receipt["mes_num"] = 0
                    receipt["año"] = 0
                    receipt["fecha_ordenable"] = datetime.now()
            
            return receipts
            
        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            return []

    def _create_summary_sheet(self, wb: Workbook, data: List[Dict], 
                            start_date: str, end_date: str, 
                            report_type: str, user_role: str):
        """Crea hoja de resumen ejecutivo"""
        ws = wb.active
        ws.title = "Resumen Ejecutivo"
        
        # Título principal
        ws["A1"] = "RIOCAJA SMART - REPORTE DE COMPROBANTES"
        ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
        ws["A1"].fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        ws["A1"].alignment = Alignment(horizontal="center")
        ws.merge_cells("A1:F1")
        
        # Información del reporte
        ws["A3"] = "INFORMACIÓN DEL REPORTE"
        ws["A3"].font = Font(size=12, bold=True)
        
        ws["A4"] = "Período:"
        ws["B4"] = f"{start_date} al {end_date}"
        ws["A5"] = "Tipo de Reporte:"
        ws["B5"] = report_type.title()
        ws["A6"] = "Fecha de Generación:"
        ws["B6"] = datetime.now().strftime("%d/%m/%Y %H:%M")
        ws["A7"] = "Total de Registros:"
        ws["B7"] = len(data)
        
        # Estadísticas generales
        total_valor = sum(float(r.get("valor_total", 0)) for r in data)
        tipos_unicos = len(set(r.get("tipo", "") for r in data))
        
        ws["A9"] = "ESTADÍSTICAS GENERALES"
        ws["A9"].font = Font(size=12, bold=True)
        
        ws["A10"] = "Valor Total:"
        ws["B10"] = f"${total_valor:,.2f}"
        ws["B10"].font = Font(bold=True, color="2E7D32")
        
        ws["A11"] = "Tipos de Transacciones:"
        ws["B11"] = tipos_unicos
        
        ws["A12"] = "Promedio por Transacción:"
        ws["B12"] = f"${total_valor/len(data):,.2f}" if data else "$0.00"
        
        # Resumen por tipo
        tipo_stats = {}
        for receipt in data:
            tipo = receipt.get("tipo", "Sin Tipo")
            valor = float(receipt.get("valor_total", 0))
            if tipo not in tipo_stats:
                tipo_stats[tipo] = {"count": 0, "total": 0}
            tipo_stats[tipo]["count"] += 1
            tipo_stats[tipo]["total"] += valor
        
        ws["A14"] = "RESUMEN POR TIPO DE TRANSACCIÓN"
        ws["A14"].font = Font(size=12, bold=True)
        
        headers = ["Tipo", "Cantidad", "Valor Total", "Porcentaje"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=15, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E8F5E8", end_color="E8F5E8", fill_type="solid")
        
        row = 16
        for tipo, stats in sorted(tipo_stats.items(), key=lambda x: x[1]["total"], reverse=True):
            ws.cell(row=row, column=1, value=tipo)
            ws.cell(row=row, column=2, value=stats["count"])
            ws.cell(row=row, column=3, value=f"${stats['total']:,.2f}")
            percentage = (stats["total"] / total_valor * 100) if total_valor > 0 else 0
            ws.cell(row=row, column=4, value=f"{percentage:.1f}%")
            row += 1
        
        # Si es admin/operador, mostrar resumen por corresponsal
        if user_role in ["admin", "operador"]:
            corresponsal_stats = {}
            for receipt in data:
                codigo = receipt.get("codigo_corresponsal", "Sin Código")
                nombre = receipt.get("nombre_corresponsal", "Sin Nombre")
                valor = float(receipt.get("valor_total", 0))
                
                key = f"{codigo} - {nombre}"
                if key not in corresponsal_stats:
                    corresponsal_stats[key] = {"count": 0, "total": 0}
                corresponsal_stats[key]["count"] += 1
                corresponsal_stats[key]["total"] += valor
            
            if corresponsal_stats:
                ws[f"A{row + 2}"] = "RESUMEN POR CORRESPONSAL"
                ws[f"A{row + 2}"].font = Font(size=12, bold=True)
                
                for col, header in enumerate(["Corresponsal", "Cantidad", "Valor Total"], 1):
                    cell = ws.cell(row=row + 3, column=col, value=header)
                    cell.font = Font(bold=True)
                    cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
                
                cor_row = row + 4
                for corresponsal, stats in sorted(corresponsal_stats.items(), 
                                                key=lambda x: x[1]["total"], reverse=True):
                    ws.cell(row=cor_row, column=1, value=corresponsal)
                    ws.cell(row=cor_row, column=2, value=stats["count"])
                    ws.cell(row=cor_row, column=3, value=f"${stats['total']:,.2f}")
                    cor_row += 1
        
        # Ajustar ancho de columnas
        ws.column_dimensions["A"].width = 25
        ws.column_dimensions["B"].width = 20
        ws.column_dimensions["C"].width = 15
        ws.column_dimensions["D"].width = 15

    def _create_details_sheet(self, wb: Workbook, data: List[Dict], user_role: str):
        """Crea hoja con todos los detalles de transacciones"""
        ws = wb.create_sheet("Detalle de Transacciones")
        
        # Headers base
        headers = [
            "Fecha", "Hora", "Tipo", "Nro. Transacción", 
            "Valor Total", "Día Semana", "Semana", "Mes"
        ]
        
        # Headers adicionales para admin/operador
        if user_role in ["admin", "operador"]:
            headers.extend([
                "Código Corresponsal", "Nombre Corresponsal", 
                "Nombre Local", "Email Usuario"
            ])
        
        # Escribir headers
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1565C0", end_color="1565C0", fill_type="solid")
            cell.alignment = Alignment(horizontal="center")
        
        # Escribir datos
        for row, receipt in enumerate(data, 2):
            ws.cell(row=row, column=1, value=receipt.get("fecha", ""))
            ws.cell(row=row, column=2, value=receipt.get("hora", ""))
            ws.cell(row=row, column=3, value=receipt.get("tipo", ""))
            ws.cell(row=row, column=4, value=receipt.get("nro_transaccion", ""))
            ws.cell(row=row, column=5, value=float(receipt.get("valor_total", 0)))
            ws.cell(row=row, column=6, value=receipt.get("dia_semana", ""))
            ws.cell(row=row, column=7, value=receipt.get("semana_num", ""))
            ws.cell(row=row, column=8, value=receipt.get("mes_num", ""))
            
            if user_role in ["admin", "operador"]:
                ws.cell(row=row, column=9, value=receipt.get("codigo_corresponsal", ""))
                ws.cell(row=row, column=10, value=receipt.get("nombre_corresponsal", ""))
                ws.cell(row=row, column=11, value=receipt.get("nombre_local", ""))
                ws.cell(row=row, column=12, value=receipt.get("email_usuario", ""))
        
        # Formato de columna de valores
        for row in range(2, len(data) + 2):
            ws.cell(row=row, column=5).number_format = '"$"#,##0.00'
        
        # Ajustar anchos
        column_widths = [12, 10, 18, 15, 12, 12, 8, 8, 15, 20, 20, 25]
        for i, width in enumerate(column_widths[:len(headers)], 1):
            ws.column_dimensions[chr(64 + i)].width = width
        
        # Aplicar filtros
        ws.auto_filter.ref = f"A1:{chr(64 + len(headers))}{len(data) + 1}"

    def _create_analysis_sheet(self, wb: Workbook, data: List[Dict], 
                             start_date: str, end_date: str, user_role: str):
        """Crea hoja de análisis con gráficos"""
        ws = wb.create_sheet("Análisis y Gráficos")
        
        # Título
        ws["A1"] = "ANÁLISIS DE TRANSACCIONES"
        ws["A1"].font = Font(size=14, bold=True)
        ws.merge_cells("A1:D1")
        
        # Análisis por tipo de transacción
        tipo_analysis = {}
        for receipt in data:
            tipo = receipt.get("tipo", "Sin Tipo")
            valor = float(receipt.get("valor_total", 0))
            if tipo not in tipo_analysis:
                tipo_analysis[tipo] = []
            tipo_analysis[tipo].append(valor)
        
        # Crear tabla de análisis por tipo
        ws["A3"] = "ANÁLISIS POR TIPO"
        ws["A3"].font = Font(size=12, bold=True)
        
        headers = ["Tipo", "Cantidad", "Total", "Promedio", "Mínimo", "Máximo"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=4, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E3F2FD", end_color="E3F2FD", fill_type="solid")
        
        row = 5
        for tipo, valores in sorted(tipo_analysis.items(), key=lambda x: sum(x[1]), reverse=True):
            ws.cell(row=row, column=1, value=tipo)
            ws.cell(row=row, column=2, value=len(valores))
            ws.cell(row=row, column=3, value=sum(valores))
            ws.cell(row=row, column=4, value=sum(valores)/len(valores))
            ws.cell(row=row, column=5, value=min(valores))
            ws.cell(row=row, column=6, value=max(valores))
            
            # Formato de moneda
            for col in [3, 4, 5, 6]:
                ws.cell(row=row, column=col).number_format = '"$"#,##0.00'
            
            row += 1
        
        # Análisis temporal
        if len(data) > 1:
            # Análisis por día de la semana
            dia_analysis = {}
            for receipt in data:
                dia = receipt.get("dia_semana", "Unknown")
                valor = float(receipt.get("valor_total", 0))
                if dia not in dia_analysis:
                    dia_analysis[dia] = {"count": 0, "total": 0}
                dia_analysis[dia]["count"] += 1
                dia_analysis[dia]["total"] += valor
            
            ws[f"A{row + 2}"] = "ANÁLISIS POR DÍA DE LA SEMANA"
            ws[f"A{row + 2}"].font = Font(size=12, bold=True)
            
            dia_headers = ["Día", "Transacciones", "Valor Total", "Promedio"]
            for col, header in enumerate(dia_headers, 1):
                cell = ws.cell(row=row + 3, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="F3E5F5", end_color="F3E5F5", fill_type="solid")
            
            dias_orden = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            dia_row = row + 4
            for dia in dias_orden:
                if dia in dia_analysis:
                    stats = dia_analysis[dia]
                    dia_esp = {
                        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
                        "Thursday": "Jueves", "Friday": "Viernes", "Saturday": "Sábado", "Sunday": "Domingo"
                    }
                    
                    ws.cell(row=dia_row, column=1, value=dia_esp.get(dia, dia))
                    ws.cell(row=dia_row, column=2, value=stats["count"])
                    ws.cell(row=dia_row, column=3, value=stats["total"])
                    ws.cell(row=dia_row, column=4, value=stats["total"]/stats["count"])
                    
                    # Formato de moneda
                    ws.cell(row=dia_row, column=3).number_format = '"$"#,##0.00'
                    ws.cell(row=dia_row, column=4).number_format = '"$"#,##0.00'
                    
                    dia_row += 1
        
        # Ajustar anchos
        for col in ["A", "B", "C", "D", "E", "F"]:
            ws.column_dimensions[col].width = 15

    def _create_temporal_analysis_sheet(self, wb: Workbook, data: List[Dict], report_type: str):
        """Crea análisis temporal para reportes semanales/mensuales"""
        ws = wb.create_sheet(f"Análisis {report_type.title()}")
        
        if report_type == "weekly":
            # Análisis por semana
            week_analysis = {}
            for receipt in data:
                semana = receipt.get("semana_num", 0)
                año = receipt.get("año", 2024)
                key = f"Semana {semana}/{año}"
                valor = float(receipt.get("valor_total", 0))
                
                if key not in week_analysis:
                    week_analysis[key] = {"count": 0, "total": 0, "tipos": set()}
                week_analysis[key]["count"] += 1
                week_analysis[key]["total"] += valor
                week_analysis[key]["tipos"].add(receipt.get("tipo", ""))
            
            ws["A1"] = "ANÁLISIS SEMANAL"
            ws["A1"].font = Font(size=14, bold=True)
            
            headers = ["Semana", "Transacciones", "Valor Total", "Promedio", "Tipos Únicos"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="E8F5E8", end_color="E8F5E8", fill_type="solid")
            
            row = 4
            for semana, stats in sorted(week_analysis.items()):
                ws.cell(row=row, column=1, value=semana)
                ws.cell(row=row, column=2, value=stats["count"])
                ws.cell(row=row, column=3, value=stats["total"])
                ws.cell(row=row, column=4, value=stats["total"]/stats["count"])
                ws.cell(row=row, column=5, value=len(stats["tipos"]))
                
                # Formato
                ws.cell(row=row, column=3).number_format = '"$"#,##0.00'
                ws.cell(row=row, column=4).number_format = '"$"#,##0.00'
                row += 1
        
        elif report_type == "monthly":
            # Análisis por mes
            month_analysis = {}
            for receipt in data:
                mes = receipt.get("mes_num", 0)
                año = receipt.get("año", 2024)
                meses = ["", "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                        "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
                key = f"{meses[mes] if mes < len(meses) else 'Mes' + str(mes)} {año}"
                valor = float(receipt.get("valor_total", 0))
                
                if key not in month_analysis:
                    month_analysis[key] = {"count": 0, "total": 0, "tipos": set()}
                month_analysis[key]["count"] += 1
                month_analysis[key]["total"] += valor
                month_analysis[key]["tipos"].add(receipt.get("tipo", ""))
            
            ws["A1"] = "ANÁLISIS MENSUAL"
            ws["A1"].font = Font(size=14, bold=True)
            
            headers = ["Mes", "Transacciones", "Valor Total", "Promedio", "Tipos Únicos"]
            for col, header in enumerate(headers, 1):
                cell = ws.cell(row=3, column=col, value=header)
                cell.font = Font(bold=True)
                cell.fill = PatternFill(start_color="FFF3E0", end_color="FFF3E0", fill_type="solid")
            
            row = 4
            for mes, stats in sorted(month_analysis.items()):
                ws.cell(row=row, column=1, value=mes)
                ws.cell(row=row, column=2, value=stats["count"])
                ws.cell(row=row, column=3, value=stats["total"])
                ws.cell(row=row, column=4, value=stats["total"]/stats["count"])
                ws.cell(row=row, column=5, value=len(stats["tipos"]))
                
                # Formato
                ws.cell(row=row, column=3).number_format = '"$"#,##0.00'
                ws.cell(row=row, column=4).number_format = '"$"#,##0.00'
                row += 1

    def _create_corresponsal_sheet(self, wb: Workbook, data: List[Dict]):
        """Crea análisis detallado por corresponsal (solo admin/operador)"""
        ws = wb.create_sheet("Análisis por Corresponsal")
        
        ws["A1"] = "ANÁLISIS DETALLADO POR CORRESPONSAL"
        ws["A1"].font = Font(size=14, bold=True)
        ws.merge_cells("A1:G1")
        
        # Agrupar por corresponsal
        corresponsal_data = {}
        for receipt in data:
            codigo = receipt.get("codigo_corresponsal", "Sin Código")
            nombre = receipt.get("nombre_corresponsal", "Sin Nombre")
            local = receipt.get("nombre_local", "Sin Local")
            key = codigo
            
            if key not in corresponsal_data:
                corresponsal_data[key] = {
                    "codigo": codigo,
                    "nombre": nombre,
                    "local": local,
                    "transacciones": [],
                    "tipos": {}
                }
            
            valor = float(receipt.get("valor_total", 0))
            tipo = receipt.get("tipo", "Sin Tipo")
            
            corresponsal_data[key]["transacciones"].append({
                "valor": valor,
                "tipo": tipo,
                "fecha": receipt.get("fecha", "")
            })
            
            if tipo not in corresponsal_data[key]["tipos"]:
                corresponsal_data[key]["tipos"][tipo] = {"count": 0, "total": 0}
            corresponsal_data[key]["tipos"][tipo]["count"] += 1
            corresponsal_data[key]["tipos"][tipo]["total"] += valor
        
        # Headers
        headers = ["Código", "Nombre", "Local", "Total Trans.", "Valor Total", "Promedio", "Tipos Únicos"]
        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=3, column=col, value=header)
            cell.font = Font(bold=True)
            cell.fill = PatternFill(start_color="E1F5FE", end_color="E1F5FE", fill_type="solid")
        
        # Datos por corresponsal
        row = 4
        for codigo, info in sorted(corresponsal_data.items(), 
                                 key=lambda x: sum(t["valor"] for t in x[1]["transacciones"]), 
                                 reverse=True):
            total_valor = sum(t["valor"] for t in info["transacciones"])
            total_trans = len(info["transacciones"])
            
            ws.cell(row=row, column=1, value=info["codigo"])
            ws.cell(row=row, column=2, value=info["nombre"])
            ws.cell(row=row, column=3, value=info["local"])
            ws.cell(row=row, column=4, value=total_trans)
            ws.cell(row=row, column=5, value=total_valor)
            ws.cell(row=row, column=6, value=total_valor/total_trans if total_trans > 0 else 0)
            ws.cell(row=row, column=7, value=len(info["tipos"]))
            
            # Formato
            ws.cell(row=row, column=5).number_format = '"$"#,##0.00'
            ws.cell(row=row, column=6).number_format = '"$"#,##0.00'
            
            row += 1
        
        # Detalle por tipo para cada corresponsal
        detail_row = row + 3
        ws[f"A{detail_row}"] = "DETALLE POR TIPO DE TRANSACCIÓN"
        ws[f"A{detail_row}"].font = Font(size=12, bold=True)
        detail_row += 2
        
        for codigo, info in sorted(corresponsal_data.items()):
            if info["tipos"]:
                ws[f"A{detail_row}"] = f"Corresponsal: {info['codigo']} - {info['nombre']}"
                ws[f"A{detail_row}"].font = Font(bold=True, color="1565C0")
                detail_row += 1
                
                # Headers para detalle
                detail_headers = ["Tipo", "Cantidad", "Valor Total", "Porcentaje"]
                for col, header in enumerate(detail_headers, 1):
                    cell = ws.cell(row=detail_row, column=col, value=header)
                    cell.font = Font(bold=True, size=9)
                    cell.fill = PatternFill(start_color="F5F5F5", end_color="F5F5F5", fill_type="solid")
                detail_row += 1
                
                total_corresponsal = sum(tipo_info["total"] for tipo_info in info["tipos"].values())
                
                for tipo, tipo_info in sorted(info["tipos"].items(), 
                                            key=lambda x: x[1]["total"], reverse=True):
                    percentage = (tipo_info["total"] / total_corresponsal * 100) if total_corresponsal > 0 else 0
                    
                    ws.cell(row=detail_row, column=1, value=tipo)
                    ws.cell(row=detail_row, column=2, value=tipo_info["count"])
                    ws.cell(row=detail_row, column=3, value=tipo_info["total"])
                    ws.cell(row=detail_row, column=4, value=f"{percentage:.1f}%")
                    
                    ws.cell(row=detail_row, column=3).number_format = '"$"#,##0.00'
                    detail_row += 1
                
                detail_row += 1  # Espacio entre corresponsales
        
        # Ajustar anchos
        column_widths = [12, 20, 20, 12, 15, 12, 12]
        for i, width in enumerate(column_widths, 1):
            ws.column_dimensions[chr(64 + i)].width = width

    def _apply_general_formatting(self, wb: Workbook):
        """Aplica formato general a todo el workbook"""
        # Definir estilos de borde
        thin_border = Border(
            left=Side(style='thin'),
            right=Side(style='thin'),
            top=Side(style='thin'),
            bottom=Side(style='thin')
        )
        
        for ws in wb.worksheets:
            # Aplicar bordes a todas las celdas con datos
            for row in ws.iter_rows():
                for cell in row:
                    if cell.value is not None:
                        cell.border = thin_border
                        cell.alignment = Alignment(horizontal="center", vertical="center")
            
            # Congelar paneles en la primera fila
            ws.freeze_panes = "A2"

    def _generate_empty_report(self, start_date: str, end_date: str, report_type: str) -> bytes:
        """Genera un reporte vacío cuando no hay datos"""
        wb = Workbook()
        ws = wb.active
        ws.title = "Sin Datos"
        
        ws["A1"] = "RIOCAJA SMART - REPORTE SIN DATOS"
        ws["A1"].font = Font(size=16, bold=True, color="FFFFFF")
        ws["A1"].fill = PatternFill(start_color="F44336", end_color="F44336", fill_type="solid")
        ws["A1"].alignment = Alignment(horizontal="center")
        ws.merge_cells("A1:D1")
        
        ws["A3"] = f"No se encontraron transacciones para el período:"
        ws["A4"] = f"Desde: {start_date}"
        ws["A5"] = f"Hasta: {end_date}"
        ws["A6"] = f"Tipo de reporte: {report_type}"
        ws["A7"] = f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        
        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        
        return excel_buffer.getvalue()

    def get_date_range_options(self) -> Dict[str, Dict]:
        """Obtiene opciones predefinidas de rangos de fechas"""
        now = datetime.now()
        
        return {
            "hoy": {
                "start": now.strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Hoy"
            },
            "ayer": {
                "start": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
                "end": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": "Ayer"
            },
            "esta_semana": {
                "start": (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Esta Semana"
            },
            "semana_pasada": {
                "start": (now - timedelta(days=now.weekday() + 7)).strftime("%Y-%m-%d"),
                "end": (now - timedelta(days=now.weekday() + 1)).strftime("%Y-%m-%d"),
                "label": "Semana Pasada"
            },
            "este_mes": {
                "start": now.replace(day=1).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Este Mes"
            },
            "mes_pasado": {
                "start": (now.replace(day=1) - timedelta(days=1)).replace(day=1).strftime("%Y-%m-%d"),
                "end": (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d"),
                "label": "Mes Pasado"
            },
            "ultimos_7_dias": {
                "start": (now - timedelta(days=7)).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Últimos 7 Días"
            },
            "ultimos_30_dias": {
                "start": (now - timedelta(days=30)).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Últimos 30 Días"
            },
            "ultimo_trimestre": {
                "start": (now - timedelta(days=90)).strftime("%Y-%m-%d"),
                "end": now.strftime("%Y-%m-%d"),
                "label": "Último Trimestre"
            }
        }

    def validate_date_range(self, start_date: str, end_date: str) -> Tuple[bool, str]:
        """Valida el rango de fechas"""
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            if start_dt > end_dt:
                return False, "La fecha de inicio no puede ser mayor que la fecha de fin"
            
            if end_dt > datetime.now():
                return False, "La fecha de fin no puede ser mayor que la fecha actual"
            
            # Límite máximo de 1 año
            if (end_dt - start_dt).days > 365:
                return False, "El rango de fechas no puede ser mayor a 1 año"
            
            return True, ""
            
        except ValueError:
            return False, "Formato de fecha inválido. Use YYYY-MM-DD"

    def get_available_corresponsales_for_reports(self) -> List[Dict]:
        """Obtiene lista de corresponsales disponibles para filtros de reportes"""
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
                        "nombre_corresponsal": {"$first": "$nombre_corresponsal"},
                        "nombre_local": {"$first": "$nombre_local"},
                        "total_transacciones": {"$sum": 1},
                        "valor_total": {"$sum": "$valor_total"},
                        "ultima_transaccion": {"$max": "$created_at"}
                    }
                },
                {
                    "$sort": {"total_transacciones": -1}
                }
            ]
            
            result = list(self.receipts.aggregate(pipeline))
            
            corresponsales = []
            for item in result:
                corresponsales.append({
                    "codigo": item["_id"],
                    "nombre": item.get("nombre_corresponsal", "Sin Nombre"),
                    "local": item.get("nombre_local", "Sin Local"),
                    "total_transacciones": item["total_transacciones"],
                    "valor_total": round(item["valor_total"], 2),
                    "ultima_transaccion": item.get("ultima_transaccion")
                })
            
            return corresponsales
            
        except Exception as e:
            logger.error(f"Error obteniendo corresponsales para reportes: {e}")
            return []

    def get_report_statistics(self, start_date: str, end_date: str, 
                            user_id: Optional[str] = None, 
                            user_role: str = "lector") -> Dict:
        """Obtiene estadísticas rápidas del reporte antes de generarlo"""
        try:
            data = self._get_receipts_data(start_date, end_date, user_id, user_role, None)
            
            if not data:
                return {
                    "total_registros": 0,
                    "valor_total": 0,
                    "tipos_unicos": 0,
                    "promedio_transaccion": 0,
                    "fecha_primera": None,
                    "fecha_ultima": None
                }
            
            total_valor = sum(float(r.get("valor_total", 0)) for r in data)
            tipos_unicos = len(set(r.get("tipo", "") for r in data))
            
            fechas = [r.get("fecha_ordenable") for r in data if r.get("fecha_ordenable")]
            fechas.sort()
            
            return {
                "total_registros": len(data),
                "valor_total": round(total_valor, 2),
                "tipos_unicos": tipos_unicos,
                "promedio_transaccion": round(total_valor / len(data), 2) if data else 0,
                "fecha_primera": fechas[0].strftime("%d/%m/%Y") if fechas else None,
                "fecha_ultima": fechas[-1].strftime("%d/%m/%Y") if fechas else None
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas: {e}")
            return {
                "total_registros": 0,
                "valor_total": 0,
                "tipos_unicos": 0,
                "promedio_transaccion": 0,
                "fecha_primera": None,
                "fecha_ultima": None
            }