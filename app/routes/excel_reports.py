# app/routes/excel_reports.py
from fastapi import APIRouter, HTTPException, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import io
import logging
from app.services.excel_report_service import ExcelReportService
from app.middlewares.auth_middleware import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter()

# Modelos para las peticiones
class ExcelReportRequest(BaseModel):
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    report_type: str = "general"  # general, daily, weekly, monthly
    codigo_corresponsal: Optional[str] = None  # Solo para admin/operador

class DateRangeOption(BaseModel):
    key: str
    start: str
    end: str
    label: str

class ReportStatistics(BaseModel):
    total_registros: int
    valor_total: float
    tipos_unicos: int
    promedio_transaccion: float
    fecha_primera: Optional[str]
    fecha_ultima: Optional[str]

# Inicializar servicio
excel_service = ExcelReportService()

@router.get("/date-options", response_model=List[DateRangeOption])
async def get_date_range_options(current_user=Depends(get_current_user)):
    """
    Obtiene opciones predefinidas de rangos de fechas
    """
    try:
        options = excel_service.get_date_range_options()
        
        return [
            DateRangeOption(
                key=key,
                start=data["start"],
                end=data["end"],
                label=data["label"]
            )
            for key, data in options.items()
        ]
        
    except Exception as e:
        logger.error(f"Error obteniendo opciones de fecha: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/corresponsales", response_model=List[dict])
async def get_available_corresponsales(current_user=Depends(get_current_user)):
    """
    Obtiene lista de corresponsales disponibles para filtros
    Solo disponible para admin y operador
    """
    try:
        user_role = current_user.get("rol", "cnb")
        
        if user_role not in ["admin", "asesor"]:
            raise HTTPException(
                status_code=403, 
                detail="No tiene permisos para ver esta informacion"
            )
        
        corresponsales = excel_service.get_available_corresponsales_for_reports()
        
        return {
            "corresponsales": corresponsales,
            "total": len(corresponsales)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo corresponsales: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/statistics", response_model=ReportStatistics)
async def get_report_statistics(
    request: ExcelReportRequest,
    current_user=Depends(get_current_user)
):
    """
    Obtiene estadisticas rapidas del reporte antes de generarlo
    """
    try:
        user_id = current_user.get("sub")
        user_role = current_user.get("rol", "cnb")
        
        # Validar fechas
        is_valid, error_msg = excel_service.validate_date_range(
            request.start_date, 
            request.end_date
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validar permisos para filtro por corresponsal
        if request.codigo_corresponsal and user_role not in ["admin", "asesor"]:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para filtrar por corresponsal"
            )
        
        # Obtener estadisticas
        stats = excel_service.get_report_statistics(
            start_date=request.start_date,
            end_date=request.end_date,
            user_id=user_id if user_role == "lector" else None,
            user_role=user_role
        )
        
        return ReportStatistics(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo estadisticas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/generate")
async def generate_excel_report(
    request: ExcelReportRequest,
    current_user=Depends(get_current_user)
):
    """
    Genera y descarga un reporte Excel completo
    """
    try:
        user_id = current_user.get("sub")
        user_role = current_user.get("rol", "lector")
        user_name = current_user.get("email", "usuario")
        
        logger.info(f"Generando reporte Excel para usuario {user_name} ({user_role})")
        
        # Validar fechas
        is_valid, error_msg = excel_service.validate_date_range(
            request.start_date, 
            request.end_date
        )
        
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)
        
        # Validar permisos para filtro por corresponsal
        if request.codigo_corresponsal and user_role not in ["admin", "operador"]:
            raise HTTPException(
                status_code=403,
                detail="No tiene permisos para filtrar por corresponsal"
            )
        
        # Validar tipo de reporte
        valid_types = ["general", "daily", "weekly", "monthly"]
        if request.report_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de reporte invalido. Tipos validos: {', '.join(valid_types)}"
            )
        
        # Generar el archivo Excel
        excel_data = excel_service.generate_excel_report(
            start_date=request.start_date,
            end_date=request.end_date,
            report_type=request.report_type,
            user_id=user_id if user_role == "lector" else None,
            user_role=user_role,
            codigo_corresponsal=request.codigo_corresponsal
        )
        
        # Crear nombre del archivo
        fecha_inicio = request.start_date.replace("-", "")
        fecha_fin = request.end_date.replace("-", "")
        
        if request.codigo_corresponsal:
            filename = f"reporte_riocaja_{request.report_type}_{fecha_inicio}_{fecha_fin}_{request.codigo_corresponsal}.xlsx"
        else:
            filename = f"reporte_riocaja_{request.report_type}_{fecha_inicio}_{fecha_fin}.xlsx"
        
        # Crear respuesta con el archivo
        excel_stream = io.BytesIO(excel_data)
        
        return StreamingResponse(
            io.BytesIO(excel_data),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(excel_data))
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando reporte Excel: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Error interno al generar el reporte"
        )

@router.get("/quick-download")
async def quick_download_report(
    start_date: str = Query(..., description="Fecha inicio YYYY-MM-DD"),
    end_date: str = Query(..., description="Fecha fin YYYY-MM-DD"),
    report_type: str = Query("general", description="Tipo de reporte"),
    codigo_corresponsal: Optional[str] = Query(None, description="Codigo de corresponsal"),
    current_user=Depends(get_current_user)
):
    """
    Descarga rapida de reporte Excel mediante GET (para enlaces directos)
    """
    try:
        # Convertir a request model para reutilizar la logica
        request = ExcelReportRequest(
            start_date=start_date,
            end_date=end_date,
            report_type=report_type,
            codigo_corresponsal=codigo_corresponsal
        )
        
        return await generate_excel_report(request, current_user)
        
    except Exception as e:
        logger.error(f"Error en descarga rapida: {e}")
        raise HTTPException(status_code=500, detail="Error en descarga rapida")

@router.get("/templates")
async def get_report_templates(current_user=Depends(get_current_user)):
    """
    Obtiene plantillas predefinidas de reportes
    """
    try:
        user_role = current_user.get("rol", "lector")
        
        templates = [
            {
                "id": "diario_hoy",
                "name": "Reporte Diario - Hoy",
                "description": "Transacciones del dia actual",
                "type": "daily",
                "date_range": "hoy",
                "icon": "today"
            },
            {
                "id": "semanal_actual",
                "name": "Reporte Semanal - Esta Semana",
                "description": "Transacciones de la semana actual",
                "type": "weekly",
                "date_range": "esta_semana",
                "icon": "calendar_view_week"
            },
            {
                "id": "mensual_actual",
                "name": "Reporte Mensual - Este Mes",
                "description": "Transacciones del mes actual",
                "type": "monthly",
                "date_range": "este_mes",
                "icon": "calendar_view_month"
            },
            {
                "id": "ultimos_30_dias",
                "name": "Reporte Ultimos 30 Dias",
                "description": "Analisis de los ultimos 30 dias",
                "type": "general",
                "date_range": "ultimos_30_dias",
                "icon": "trending_up"
            }
        ]
        
        # Templates adicionales para admin/operador
        if user_role in ["admin", "operador"]:
            templates.extend([
                {
                    "id": "trimestral",
                    "name": "Reporte Trimestral",
                    "description": "Analisis completo del ultimo trimestre",
                    "type": "monthly",
                    "date_range": "ultimo_trimestre",
                    "icon": "bar_chart"
                },
                {
                    "id": "comparativo_semanal",
                    "name": "Comparativo Semanal",
                    "description": "Comparacion semana actual vs anterior",
                    "type": "weekly",
                    "date_range": "custom",
                    "icon": "compare_arrows"
                }
            ])
        
        return {
            "templates": templates,
            "user_role": user_role
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo templates: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo plantillas")

@router.post("/template/{template_id}")
async def generate_from_template(
    template_id: str,
    codigo_corresponsal: Optional[str] = None,
    current_user=Depends(get_current_user)
):
    """
    Genera reporte usando una plantilla predefinida
    """
    try:
        # Obtener opciones de fecha
        date_options = excel_service.get_date_range_options()
        
        # Mapear template a configuracion
        template_configs = {
            "diario_hoy": {
                "date_range": "hoy",
                "report_type": "daily"
            },
            "semanal_actual": {
                "date_range": "esta_semana",
                "report_type": "weekly"
            },
            "mensual_actual": {
                "date_range": "este_mes",
                "report_type": "monthly"
            },
            "ultimos_30_dias": {
                "date_range": "ultimos_30_dias",
                "report_type": "general"
            },
            "trimestral": {
                "date_range": "ultimo_trimestre",
                "report_type": "monthly"
            }
        }
        
        if template_id not in template_configs:
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        
        config = template_configs[template_id]
        date_range = date_options[config["date_range"]]
        
        # Crear request
        request = ExcelReportRequest(
            start_date=date_range["start"],
            end_date=date_range["end"],
            report_type=config["report_type"],
            codigo_corresponsal=codigo_corresponsal
        )
        
        return await generate_excel_report(request, current_user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando desde template: {e}")
        raise HTTPException(status_code=500, detail="Error generando reporte desde plantilla")

@router.get("/export-formats")
async def get_export_formats(current_user=Depends(get_current_user)):
    """
    Obtiene formatos de exportacion disponibles
    """
    try:
        formats = [
            {
                "format": "xlsx",
                "name": "Excel Avanzado",
                "description": "Archivo Excel con multiples hojas, graficos y analisis",
                "icon": "table_chart",
                "features": [
                    "Multiples hojas de analisis",
                    "Graficos automaticos",
                    "Formato profesional",
                    "Filtros y ordenamiento"
                ]
            },
            {
                "format": "csv",
                "name": "CSV Simple",
                "description": "Archivo CSV para importar en otras aplicaciones",
                "icon": "description",
                "features": [
                    "Compatible con cualquier aplicacion",
                    "Datos en formato plano",
                    "Facil importacion"
                ]
            }
        ]
        
        return {
            "formats": formats,
            "default": "xlsx"
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo formatos: {e}")
        raise HTTPException(status_code=500, detail="Error obteniendo formatos")

# Endpoint para testing (solo en desarrollo)
@router.get("/test")
async def test_excel_service(current_user=Depends(get_current_user)):
    """
    Endpoint de prueba para verificar el funcionamiento del servicio
    """
    try:
        user_role = current_user.get("rol", "lector")
        
        # Solo permitir en desarrollo
        if not __debug__:
            raise HTTPException(status_code=404, detail="Not found")
        
        # Obtener estadisticas basicas
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        
        stats = excel_service.get_report_statistics(
            start_date=yesterday,
            end_date=today,
            user_id=current_user.get("sub") if user_role == "lector" else None,
            user_role=user_role
        )
        
        date_options = excel_service.get_date_range_options()
        
        return {
            "service_status": "OK",
            "user_role": user_role,
            "test_stats": stats,
            "available_date_options": len(date_options),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en test: {e}")
        raise HTTPException(status_code=500, detail=f"Error en test: {str(e)}")