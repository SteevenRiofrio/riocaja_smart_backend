# app/routes/pdf_reports.py - VERSIÓN CORREGIDA SIN PROBLEMAS DE ENCRIPTACIÓN

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.services.email_service import EmailService
from app.middlewares.auth_middleware import get_current_user
import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime
import smtplib
import ssl

router = APIRouter()
logger = logging.getLogger(__name__)

class PdfReportRequest(BaseModel):
    recipient_email: str
    recipient_name: str
    report_date: str
    pdf_filename: str
    pdf_base64: str
    excel_filename: str = None
    excel_base64: str = None
    report_summary: dict

@router.post("/send-pdf-report")
async def send_pdf_report(request: PdfReportRequest, user=Depends(get_current_user)):
    """Enviar reporte PDF por correo - VERSIÓN CORREGIDA"""
    try:
        logger.info(f"📧 Solicitud de envío de PDF a: {request.recipient_email}")
        
        # Verificar configuración de email
        from app.config import (
            MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME,
            MAIL_SERVER, MAIL_PORT, MAIL_STARTTLS
        )
        
        if not MAIL_USERNAME or not MAIL_PASSWORD:
            logger.error("❌ Configuración de email incompleta")
            raise HTTPException(status_code=503, detail="Servicio de email no configurado")
        
        # Decodificar archivos
        try:
            pdf_bytes = base64.b64decode(request.pdf_base64)
            logger.info(f"📄 PDF decodificado: {len(pdf_bytes)} bytes")
        except Exception as e:
            logger.error(f"❌ Error decodificando PDF: {e}")
            raise HTTPException(status_code=400, detail="Error en formato del PDF")
        
        excel_bytes = None
        if request.excel_base64 and request.excel_filename:
            try:
                excel_bytes = base64.b64decode(request.excel_base64)
                logger.info(f"📊 Excel decodificado: {len(excel_bytes)} bytes")
            except Exception as e:
                logger.warning(f"⚠️ Error decodificando Excel: {e}")
                excel_bytes = None
        
        # Crear contenido HTML del email
        summary = request.report_summary
        subject = f"📊 Reporte de Cierre - {request.report_date} - RíoCaja Smart"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Reporte de Cierre - RíoCaja Smart</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto;">
            
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #1976d2 0%, #2196f3 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">📊 Reporte de Cierre Diario</h1>
                <p style="color: #e3f2fd; margin: 10px 0 0 0;">RíoCaja Smart - Sistema de Gestión CNB</p>
            </div>
            
            <!-- Content -->
            <div style="background: white; padding: 30px; border: 1px solid #e0e0e0;">
                
                <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #333; margin-top: 0;">📋 Información del Reporte</h3>
                    <p><strong>📅 Fecha:</strong> {request.report_date}</p>
                    <p><strong>👤 Usuario:</strong> {request.recipient_name}</p>
                    <p><strong>📧 Email:</strong> {request.recipient_email}</p>
                    <p><strong>🕐 Generado:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                </div>
                
                <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin-bottom: 20px;">
                    <h3 style="color: #2e7d32; margin-top: 0;">📈 Resumen Financiero</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>💰 Total Ingresos:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd; text-align: right; color: #2e7d32; font-weight: bold;">${summary.get('total_ingresos', 0):.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>💸 Total Egresos:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd; text-align: right; color: #d32f2f; font-weight: bold;">${summary.get('total_egresos', 0):.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd;"><strong>🏦 Saldo en Caja:</strong></td>
                            <td style="padding: 8px 0; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold; color: {'#2e7d32' if summary.get('saldo_en_caja', 0) >= 0 else '#d32f2f'};">${summary.get('saldo_en_caja', 0):.2f}</td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0;"><strong>📊 Total Transacciones:</strong></td>
                            <td style="padding: 8px 0; text-align: right; font-weight: bold;">{summary.get('total_transacciones', 0)}</td>
                        </tr>
                    </table>
                    
                    <div style="margin-top: 15px; padding: 10px; background: {'#c8e6c9' if summary.get('estado_caja') == 'POSITIVO' else '#ffcdd2'}; border-radius: 5px; text-align: center;">
                        <strong>Estado de Caja: {summary.get('estado_caja', 'N/A')}</strong>
                    </div>
                </div>
                
                <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h4 style="margin-top: 0; color: #e65100;">📎 Archivos Adjuntos</h4>
                    <ul style="margin: 0; padding-left: 20px;">
                        <li>📄 <strong>Reporte PDF:</strong> {request.pdf_filename}</li>
                        {f'<li>📊 <strong>Reporte Excel:</strong> {request.excel_filename}</li>' if request.excel_filename else ''}
                    </ul>
                    <p style="margin: 10px 0 0 0; font-size: 14px; color: #666;">
                        Puedes descargar y abrir estos archivos con los programas correspondientes.
                    </p>
                </div>
                
            </div>
            
            <!-- Footer -->
            <div style="background-color: #f5f5f5; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; border: 1px solid #e0e0e0; border-top: none;">
                <p style="margin: 0; color: #666; font-size: 14px;">
                    © 2025 RíoCaja Smart - Sistema de Gestión CNB
                </p>
                <p style="margin: 5px 0 0 0; color: #999; font-size: 12px;">
                    Este es un mensaje automático, por favor no responder.
                </p>
            </div>
            
        </body>
        </html>
        """
        
        # ✅ ENVIAR EMAIL DIRECTAMENTE (sin usar EmailService para evitar problemas)
        success = await send_email_with_attachments(
            to_email=request.recipient_email,
            subject=subject,
            html_content=html_content,
            pdf_filename=request.pdf_filename,
            pdf_bytes=pdf_bytes,
            excel_filename=request.excel_filename,
            excel_bytes=excel_bytes
        )
        
        if success:
            logger.info(f"✅ PDF enviado exitosamente a: {request.recipient_email}")
            return {
                "success": True, 
                "message": f"Reporte enviado correctamente a {request.recipient_email}"
            }
        else:
            logger.error(f"❌ Falló el envío de PDF a: {request.recipient_email}")
            raise HTTPException(status_code=500, detail="Error al enviar el correo")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado enviando PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

async def send_email_with_attachments(to_email: str, subject: str, html_content: str, 
                                    pdf_filename: str, pdf_bytes: bytes,
                                    excel_filename: str = None, excel_bytes: bytes = None) -> bool:
    """Función para enviar email con adjuntos - VERSIÓN CORREGIDA"""
    try:
        from app.config import (
            MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME,
            MAIL_SERVER, MAIL_PORT, MAIL_STARTTLS
        )
        
        # ✅ CREAR MENSAJE CORRECTAMENTE
        message = MIMEMultipart('mixed')
        message["Subject"] = subject
        message["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        message["To"] = to_email
        message["Date"] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
        
        # ✅ AGREGAR CONTENIDO HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)
        
        # ✅ AGREGAR PDF CORRECTAMENTE
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf", name=pdf_filename)
        pdf_attachment.add_header(
            'Content-Disposition', 
            f'attachment; filename="{pdf_filename}"'
        )
        pdf_attachment.add_header('Content-ID', f'<{pdf_filename}>')
        message.attach(pdf_attachment)
        logger.info(f"📄 PDF adjuntado: {pdf_filename}")
        
        # ✅ AGREGAR EXCEL SI EXISTE
        if excel_bytes and excel_filename:
            # Determinar el tipo MIME correcto
            if excel_filename.endswith('.xlsx'):
                subtype = "vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif excel_filename.endswith('.csv'):
                subtype = "csv"
            else:
                subtype = "octet-stream"
            
            excel_attachment = MIMEApplication(excel_bytes, _subtype=subtype, name=excel_filename)
            excel_attachment.add_header(
                'Content-Disposition', 
                f'attachment; filename="{excel_filename}"'
            )
            excel_attachment.add_header('Content-ID', f'<{excel_filename}>')
            message.attach(excel_attachment)
            logger.info(f"📊 Excel adjuntado: {excel_filename}")
        
        # ✅ ENVIAR EMAIL
        context = ssl.create_default_context()
        
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            server.set_debuglevel(0)  # Desactivar debug para producción
            
            if MAIL_STARTTLS:
                server.starttls(context=context)
            
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            
            # Enviar el mensaje
            text = message.as_string()
            server.sendmail(MAIL_FROM, [to_email], text)
            
        attachments_info = f"PDF: {pdf_filename}"
        if excel_filename:
            attachments_info += f", Excel: {excel_filename}"
        
        logger.info(f"✅ Email enviado correctamente a: {to_email} con adjuntos: {attachments_info}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email con adjuntos a {to_email}: {e}")
        logger.error(f"   Detalles del error: {type(e).__name__}: {str(e)}")
        return False