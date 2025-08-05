# app/routes/pdf_reports.py - NUEVO ARCHIVO
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

router = APIRouter()
logger = logging.getLogger(__name__)

class PdfReportRequest(BaseModel):
    recipient_email: str
    recipient_name: str
    report_date: str
    pdf_filename: str
    pdf_base64: str
    report_summary: dict

@router.post("/send-pdf-report")
async def send_pdf_report(request: PdfReportRequest, user=Depends(get_current_user)):
    """Enviar reporte PDF por correo"""
    try:
        logger.info(f"📧 Solicitud de envío de PDF a: {request.recipient_email}")
        
        email_service = EmailService()
        
        # Verificar que el servicio de email esté habilitado
        if not email_service.email_enabled:
            logger.warning("⚠️ Servicio de email deshabilitado")
            raise HTTPException(status_code=503, detail="Servicio de email no disponible")
        
        # Decodificar el PDF
        try:
            pdf_bytes = base64.b64decode(request.pdf_base64)
            logger.info(f"📄 PDF decodificado correctamente: {len(pdf_bytes)} bytes")
        except Exception as e:
            logger.error(f"❌ Error decodificando PDF: {e}")
            raise HTTPException(status_code=400, detail="Error en el formato del PDF")
        
        # Preparar el contenido del email
        subject = f"📊 Reporte de Cierre - {request.report_date} - RíoCaja Smart"
        
        # Crear contenido HTML del email
        summary = request.report_summary
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #1976d2; text-align: center;">📊 Reporte de Cierre Diario</h2>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #333; margin-top: 0;">Resumen del Reporte</h3>
                <p><strong>📅 Fecha:</strong> {request.report_date}</p>
                <p><strong>👤 Usuario:</strong> {request.recipient_name}</p>
                <p><strong>📧 Email:</strong> {request.recipient_email}</p>
            </div>
            
            <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #2e7d32; margin-top: 0;">📈 Resumen Financiero</h3>
                <div style="display: flex; justify-content: space-between; flex-wrap: wrap;">
                    <div style="margin: 10px 0;">
                        <strong>💰 Total Ingresos:</strong><br>
                        <span style="color: #2e7d32; font-size: 18px;">${summary.get('total_ingresos', 0):.2f}</span>
                    </div>
                    <div style="margin: 10px 0;">
                        <strong>💸 Total Egresos:</strong><br>
                        <span style="color: #d32f2f; font-size: 18px;">${summary.get('total_egresos', 0):.2f}</span>
                    </div>
                    <div style="margin: 10px 0;">
                        <strong>🏦 Saldo en Caja:</strong><br>
                        <span style="color: {'#2e7d32' if summary.get('saldo_en_caja', 0) >= 0 else '#d32f2f'}; font-size: 18px; font-weight: bold;">
                            ${summary.get('saldo_en_caja', 0):.2f}
                        </span>
                    </div>
                </div>
                <p><strong>📊 Total Transacciones:</strong> {summary.get('total_transacciones', 0)}</p>
                <p><strong>📋 Estado de Caja:</strong> 
                    <span style="color: {'#2e7d32' if summary.get('estado_caja') == 'POSITIVO' else '#d32f2f'}; font-weight: bold;">
                        {summary.get('estado_caja', 'N/A')}
                    </span>
                </p>
            </div>
            
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #e65100;">
                    <strong>📎 Adjunto:</strong> Encontrarás el reporte completo en formato PDF adjunto a este correo.
                </p>
            </div>
            
            <div style="text-align: center; margin: 30px 0; color: #666;">
                <p>Generado automáticamente por RíoCaja Smart</p>
                <p style="font-size: 12px;">📅 {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            </div>
        </div>
        """
        
        # Enviar email con PDF adjunto usando el método especializado
        success = await send_pdf_email(
            email_service=email_service,
            to_email=request.recipient_email,
            subject=subject,
            html_content=html_content,
            pdf_filename=request.pdf_filename,
            pdf_bytes=pdf_bytes
        )
        
        if success:
            logger.info(f"✅ PDF enviado exitosamente a: {request.recipient_email}")
            return {
                "success": True, 
                "message": f"Reporte PDF enviado correctamente a {request.recipient_email}"
            }
        else:
            logger.error(f"❌ Falló el envío de PDF a: {request.recipient_email}")
            raise HTTPException(status_code=500, detail="Error al enviar el PDF por correo")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error inesperado enviando PDF: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

async def send_pdf_email(email_service: EmailService, to_email: str, subject: str, 
                        html_content: str, pdf_filename: str, pdf_bytes: bytes) -> bool:
    """Función auxiliar para enviar email con PDF adjunto"""
    try:
        import smtplib
        import ssl
        from app.config import (
            MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME,
            MAIL_SERVER, MAIL_PORT, MAIL_STARTTLS
        )
        
        # Crear mensaje
        message = MIMEMultipart()
        message["Subject"] = subject
        message["From"] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>"
        message["To"] = to_email
        
        # Agregar contenido HTML
        html_part = MIMEText(html_content, "html", "utf-8")
        message.attach(html_part)
        
        # Agregar PDF como adjunto
        pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
        pdf_attachment.add_header(
            'Content-Disposition', 
            f'attachment; filename="{pdf_filename}"'
        )
        message.attach(pdf_attachment)
        
        # Enviar email
        context = ssl.create_default_context()
        
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT) as server:
            if MAIL_STARTTLS:
                server.starttls(context=context)
            
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(message)
            
        logger.info(f"✅ Email con PDF enviado exitosamente a: {to_email}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error enviando email con PDF a {to_email}: {e}")
        return False