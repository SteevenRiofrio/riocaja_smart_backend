# app/services/email_service.py - CORRECCIÓN DE CONFIGURACIÓN
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import base64
import tempfile
import os

# ✅ CORRECCIÓN: Importar la configuración del archivo config.py
from app.config import (
    MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME, 
    MAIL_SERVER, MAIL_PORT, MAIL_STARTTLS
)

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # ✅ CORRECCIÓN: Usar la configuración del config.py en lugar de variables de entorno
        self.smtp_server = MAIL_SERVER
        self.smtp_port = MAIL_PORT
        self.email_user = MAIL_USERNAME
        self.email_password = MAIL_PASSWORD
        self.mail_from = MAIL_FROM
        self.mail_from_name = MAIL_FROM_NAME
        self.company_name = "RíoCaja Smart"
        
        # Validación de configuración
        if not self.email_user or not self.email_password:
            logger.warning("⚠️  Configuración de email incompleta - Los emails no se enviarán")
            self.email_enabled = False
        else:
            self.email_enabled = True
            logger.info(f"✅ EmailService configurado para: {self.email_user}")
    
    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Enviar email con manejo robusto de errores"""
        if not self.email_enabled:
            logger.warning(f"📧 Email deshabilitado - No se envió a {to_email}")
            return False
            
        try:
            logger.info(f"📧 Intentando enviar email a: {to_email}")
            
            # Crear mensaje
            message = MIMEMultipart("alternative")
            message["Subject"] = subject
            message["From"] = f"{self.mail_from_name} <{self.mail_from}"
            message["To"] = to_email
            
            # Agregar contenido HTML
            html_part = MIMEText(html_body, "html", "utf-8")
            message.attach(html_part)
            
            # Crear contexto SSL seguro
            context = ssl.create_default_context()
            
            # Conectar y enviar
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if MAIL_STARTTLS:
                    server.starttls(context=context)
                
                server.login(self.email_user, self.email_password)
                server.send_message(message)
                
            logger.info(f"✅ Email enviado exitosamente a: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error al enviar email a {to_email}: {str(e)}")
            return False
    
    def _get_base_template(self, content: str, title: str) -> str:
        """Template base para todos los emails"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title} - {self.company_name}</title>
        </head>
        <body style="margin: 0; padding: 0; font-family: Arial, sans-serif; background-color: #f5f5f5;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="background: linear-gradient(135deg, #1976d2 0%, #2196f3 100%); padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0; font-size: 28px; font-weight: bold;">{self.company_name}</h1>
                </div>
                
                <!-- Content -->
                <div style="padding: 30px;">
                    {content}
                </div>
                
                <!-- Footer -->
                <div style="background-color: #f8f9fa; padding: 20px; text-align: center; border-top: 1px solid #e9ecef;">
                    <p style="margin: 0; color: #6c757d; font-size: 14px;">
                        © 2025 {self.company_name} - Todos los derechos reservados
                    </p>
                    <p style="margin: 5px 0 0 0; color: #6c757d; font-size: 12px;">
                        🔒 Email seguro y confidencial
                    </p>
                </div>
                
            </div>
        </body>
        </html>
        """
    
    def send_registration_confirmation(self, user_email: str, user_name: str) -> bool:
        """Email de confirmación de registro"""
        subject = f"✅ Registro Recibido - {self.company_name}"
        
        content = f"""
        <h2 style="color: #2e7d32; margin-bottom: 20px;">🎉 ¡Registro Exitoso!</h2>
        
        <p>Estimado/a <strong>{user_name}</strong>,</p>
        <p>Tu registro en <strong>{self.company_name}</strong> ha sido recibido exitosamente.</p>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>📧 Email registrado:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha registro:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p style="margin: 5px 0;"><strong>⏳ Estado:</strong> Pendiente de aprobación</p>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>📋 Próximos pasos:</strong></p>
            <ol style="margin: 10px 0;">
                <li>Tu solicitud será revisada por nuestro equipo</li>
                <li>Recibirás un email cuando sea aprobada</li>
                <li>Podrás acceder al sistema una vez aprobado</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #1976d2; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                ⏰ Tiempo estimado de aprobación: 24-48 horas
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Registro Exitoso")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_approved_notification(self, user_email: str, user_name: str, codigo_corresponsal: str) -> bool:
        """Email de cuenta aprobada con código de corresponsal"""
        subject = f"🎉 Cuenta Aprobada - {self.company_name}"
        
        content = f"""
        <h2 style="color: #2e7d32; margin-bottom: 20px;">🎉 ¡Cuenta Aprobada!</h2>
        
        <p>¡Excelentes noticias, <strong>{user_name}</strong>!</p>
        <p>Tu cuenta en <strong>{self.company_name}</strong> ha sido <strong>aprobada exitosamente</strong>.</p>
        
        <div style="background-color: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {user_name}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>🆔 Código Corresponsal:</strong> <span style="background-color: #2e7d32; color: white; padding: 4px 8px; border-radius: 4px; font-family: monospace;">{codigo_corresponsal}</span></p>
            <p style="margin: 5px 0;"><strong>📅 Fecha aprobación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>🚀 ¿Qué sigue?</strong></p>
            <ol style="margin: 10px 0;">
                <li><strong>Inicia sesión</strong> en la aplicación</li>
                <li><strong>Completa tu perfil</strong> con tu información local</li>
                <li><strong>Usa tu código de corresponsal</strong> para validar tu perfil</li>
                <li><strong>¡Comienza a usar el sistema!</strong></li>
            </ol>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #2e7d32; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                🔑 ¡Ya puedes acceder al sistema!
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Cuenta Aprobada")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_rejected_notification(self, user_email: str, user_name: str, reason: Optional[str] = None) -> bool:
        """Email de cuenta rechazada"""
        subject = f"❌ Registro Rechazado - {self.company_name}"
        
        reason_text = ""
        if reason:
            reason_text = f'<p style="margin: 5px 0;"><strong>📝 Motivo:</strong> {reason}</p>'
        
        content = f"""
        <h2 style="color: #d32f2f; margin-bottom: 20px;">❌ Registro Rechazado</h2>
        
        <p>Estimado/a <strong>{user_name}</strong>,</p>
        <p>Lamentamos informarte que tu solicitud de registro en <strong>{self.company_name}</strong> ha sido rechazada.</p>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d32f2f;">
            <p style="margin: 5px 0;"><strong>📧 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha rechazo:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            {reason_text}
        </div>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>💡 ¿Qué puedes hacer?</strong></p>
            <ul style="margin: 10px 0;">
                <li>Contactar al administrador para más información</li>
                <li>Revisar si cumples con los requisitos</li>
                <li>Solicitar una nueva evaluación si es posible</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #d32f2f; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                📞 Contacta al administrador para más detalles
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Registro Rechazado")
        return self._send_email(user_email, subject, html_body)
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Email de bienvenida mejorado"""
        return self.send_account_approved_notification(user_email, user_name, "Por asignar")
    
    def send_login_notification(self, user_email: str, user_name: str, login_info: Dict[str, Any]) -> bool:
        """Notificación de inicio de sesión (CORREGIDA)"""
        subject = f"🔐 Inicio de Sesión Detectado - {self.company_name}"
        
        content = f"""
        <h2 style="color: #1976d2; margin-bottom: 20px;">🔐 Inicio de Sesión Detectado</h2>
        
        <p>Hola {user_name},</p>
        <p>Se ha detectado un nuevo inicio de sesión en tu cuenta de <strong>{self.company_name}</strong>.</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {user_name}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>🏷️ Rol:</strong> {login_info.get('rol', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>🔑 Sesión:</strong> {login_info.get('session_id', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>🔒 Si no fuiste tú:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Cambia tu contraseña inmediatamente</li>
                <li>Contacta al administrador</li>
                <li>Revisa la actividad de tu cuenta</li>
            </ul>
        </div>
        """
        
        html_body = self._get_base_template(content, "Inicio de Sesión")
        return self._send_email(user_email, subject, html_body)
    
    def send_password_reset_code(self, user_email: str, user_name: str, reset_code: str) -> bool:
        """Email con código de recuperación de contraseña"""
        subject = f"🔑 Código de Recuperación - {self.company_name}"
        
        content = f"""
        <h2 style="color: #ff9800; margin-bottom: 20px;">🔑 Recuperación de Contraseña</h2>
        
        <p>Hola <strong>{user_name}</strong>,</p>
        <p>Has solicitado recuperar tu contraseña en <strong>{self.company_name}</strong>.</p>
        
        <div style="background-color: #fff3e0; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800; text-align: center;">
            <p style="margin: 0 0 15px 0;"><strong>🔢 Tu código de recuperación es:</strong></p>
            <p style="font-size: 32px; font-weight: bold; color: #ff9800; font-family: monospace; background-color: white; padding: 15px; border-radius: 8px; border: 2px dashed #ff9800; margin: 0;">
                {reset_code}
            </p>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>⚠️ Importante:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Este código <strong>expira en 10 minutos</strong></li>
                <li>Solo úsalo si solicitaste el cambio</li>
                <li>No compartas este código con nadie</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #ff9800; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                ⏰ Válido por 10 minutos únicamente
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Código de Recuperación")
        return self._send_email(user_email, subject, html_body)
    
    def send_password_changed_notification(self, user_email: str, user_name: str) -> bool:
        """Notificación de contraseña cambiada"""
        subject = f"✅ Contraseña Actualizada - {self.company_name}"
        
        content = f"""
        <h2 style="color: #2e7d32; margin-bottom: 20px;">✅ Contraseña Actualizada</h2>
        
        <p>Hola <strong>{user_name}</strong>,</p>
        <p>Tu contraseña en <strong>{self.company_name}</strong> ha sido cambiada exitosamente.</p>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>📧 Cuenta:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha cambio:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p style="margin: 5px 0;"><strong>🔒 Estado:</strong> Contraseña actualizada</p>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>🚨 Si no cambiaste tu contraseña:</strong></p>
            <ul style="margin: 10px 0;">
                <li><strong>Contacta al administrador inmediatamente</strong></li>
                <li>Cambia tu contraseña desde otro dispositivo</li>
                <li>Revisa la seguridad de tu cuenta</li>
            </ul>
        </div>
        """
        
        html_body = self._get_base_template(content, "Contraseña Actualizada")
        return self._send_email(user_email, subject, html_body)
    
    def send_admin_new_user_notification(self, admin_email: str, user_data: Dict[str, Any]) -> bool:
        """Notificar a admin sobre nuevo registro"""
        subject = f"👤 Nuevo Usuario Registrado - {self.company_name}"
        
        content = f"""
        <h2 style="color: #1976d2; margin-bottom: 20px;">👤 Nuevo Usuario Registrado</h2>
        
        <p>Se ha registrado un nuevo usuario en el sistema y requiere aprobación.</p>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1976d2;">
            <p style="margin: 5px 0;"><strong>👤 Nombre:</strong> {user_data.get('nombre', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {user_data.get('email', 'N/A')}</p>
            <p style="margin: 5px 0;"><strong>🏷️ Rol:</strong> {user_data.get('rol', 'cnb')}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha registro:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #1976d2; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                📋 Accede al panel admin para aprobar/rechazar
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Nuevo Usuario")
        return self._send_email(admin_email, subject, html_body)
    
    def send_new_message_notification(self, user_email: str, user_name: str, message_data: Dict[str, Any]) -> bool:
        """Notificación de nuevo mensaje para CNB"""
        
        # Mapeo correcto de tipos de mensaje con íconos y colores
        message_type_config = {
            'informativo': {
                'icon': '📋',
                'color': '#1976d2',
                'bg_color': '#e3f2fd',
                'label': 'INFORMATIVO'
            },
            'advertencia': {
                'icon': '⚠️',
                'color': '#f57c00',
                'bg_color': '#fff3e0',
                'label': 'ADVERTENCIA'
            },
            'urgente': {
                'icon': '🚨',
                'color': '#d32f2f',
                'bg_color': '#ffebee',
                'label': 'URGENTE'
            }
        }
        
        tipo = message_data.get('tipo', 'informativo').lower()
        config = message_type_config.get(tipo, message_type_config['informativo'])
        
        # Título del email con tipo de mensaje
        subject = f"{config['icon']} [{config['label']}] Nuevo Mensaje - {self.company_name}"
        
        content = f"""
        <h2 style="color: {config['color']}; margin-bottom: 20px;">
            {config['icon']} Nuevo Mensaje - {config['label']}
        </h2>
        
        <p>Hola <strong>{user_name}</strong>,</p>
        <p>Tienes un nuevo mensaje <strong>{config['label'].lower()}</strong> en <strong>{self.company_name}</strong>:</p>
        
        <div style="background-color: {config['bg_color']}; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid {config['color']};">
            <!-- Etiqueta del tipo de mensaje -->
            <div style="margin-bottom: 15px;">
                <span style="background-color: {config['color']}; color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: bold; text-transform: uppercase;">
                    {config['icon']} {config['label']}
                </span>
            </div>
            
            <!-- Título del mensaje -->
            <h3 style="margin: 0 0 10px 0; color: {config['color']};">
                {message_data.get('titulo', 'Sin título')}
            </h3>
            
            <!-- Contenido del mensaje -->
            <p style="margin: 10px 0; color: #333; line-height: 1.6;">
                {message_data.get('contenido', '')}
            </p>
            
            <!-- Información adicional -->
            <hr style="border: 0; height: 1px; background: {config['color']}; margin: 15px 0;">
            
            <!-- Fecha de vencimiento si existe -->
            {self._get_expiry_info(message_data, config['color'])}
            
            <p style="margin: 0; color: #666; font-size: 12px;">
                Este es un mensaje automático, por favor no respondas.
            </p>
        </div>
        
        <!-- Mensaje de acción según el tipo -->
        {self._get_action_message(tipo, config)}
        """
        
        html_body = self._get_base_template(content, f"Nuevo Mensaje {config['label']}")
        return self._send_email(user_email, subject, html_body)

    def _get_expiry_info(self, message_data: Dict[str, Any], color: str) -> str:
        """Genera información de fecha de vencimiento si existe"""
        visible_hasta = message_data.get('visible_hasta')
        if visible_hasta:
            return f"""
            <p style="margin: 10px 0; color: {color}; font-weight: bold;">
                📅 Visible hasta: {visible_hasta}
            </p>
            """
        return ""

    def _get_action_message(self, tipo: str, config: Dict[str, str]) -> str:
        """Genera mensaje de acción según el tipo de mensaje"""
        action_messages = {
            'informativo': """
            <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #333; font-size: 14px;">
                    Este es un mensaje informativo. No se requiere acción inmediata.
                </p>
            </div>
            """,
            'advertencia': """
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #333; font-size: 14px;">
                    Atención: Este es un mensaje de advertencia. Por favor revisa los detalles.
                </p>
            </div>
            """,
            'urgente': """
            <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #333; font-size: 14px;">
                    Urgente: Se requiere tu atención inmediata a este mensaje.
                </p>
            </div>
            """
        }
        
        return action_messages.get(tipo, action_messages['informativo'])
    
    def send_pdf_report_backup(self, recipient_email: str, recipient_name: str, 
                          report_date: str, pdf_base64: str, pdf_filename: str,
                          report_summary: Dict[str, Any]) -> bool:
        """Envío de reporte PDF como respaldo por correo"""
        try:
            # Decodificar el PDF de base64
            pdf_data = base64.b64decode(pdf_base64)
            # Crear archivo temporal
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
                temp_file.write(pdf_data)
                temp_file_path = temp_file.name

            subject = f"📊 Respaldo Reporte de Cierre - {report_date} - {self.company_name}"

            # Extraer información del resumen
            total_ingresos = report_summary.get('total_ingresos', 0)
            total_egresos = report_summary.get('total_egresos', 0)
            saldo_en_caja = report_summary.get('saldo_en_caja', 0)
            total_transacciones = report_summary.get('total_transacciones', 0)
            estado_caja = report_summary.get('estado_caja', 'POSITIVO')

            estado_config = {
                'POSITIVO': {'color': '#2e7d32', 'bg': '#e8f5e8', 'emoji': '✅'},
                'NEGATIVO': {'color': '#d32f2f', 'bg': '#ffebee', 'emoji': '⚠️'},
            }
            config = estado_config.get(estado_caja, estado_config['POSITIVO'])

            content = f"""
            <h2 style="color: #1976d2; margin-bottom: 20px;">📊 Respaldo Automático - Reporte de Cierre</h2>
            <p>Hola <strong>{recipient_name}</strong>,</p>
            <p>Se ha generado automáticamente el respaldo de tu reporte de cierre correspondiente al <strong>{report_date}</strong>.</p>
            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0 0 15px 0; color: #1976d2;">📋 Resumen del Día</h3>
                <table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>💰 Total Ingresos:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right; color: #2e7d32;">
                            <strong>${total_ingresos:,.2f}</strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>💸 Total Egresos:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right; color: #d32f2f;">
                            <strong>${total_egresos:,.2f}</strong>
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd;"><strong>📊 Total Transacciones:</strong></td>
                        <td style="padding: 8px; border-bottom: 1px solid #ddd; text-align: right;">
                            <strong>{total_transacciones}</strong>
                        </td>
                    </tr>
                    <tr style="background-color: {config['bg']};">
                        <td style="padding: 12px; border: 2px solid {config['color']}; font-size: 16px;">
                            <strong>{config['emoji']} Saldo en Caja:</strong>
                        </td>
                        <td style="padding: 12px; border: 2px solid {config['color']}; text-align: right; color: {config['color']}; font-size: 18px;">
                            <strong>${saldo_en_caja:,.2f}</strong>
                        </td>
                    </tr>
                </table>
            </div>
            <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1976d2;">
                <p style="margin: 0 0 10px 0;"><strong>📎 Archivo Adjunto:</strong></p>
                <ul style="margin: 0; padding-left: 20px;">
                    <li><strong>Nombre:</strong> {pdf_filename}</li>
                    <li><strong>Formato:</strong> PDF</li>
                    <li><strong>Fecha de generación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</li>
                </ul>
            </div>
            <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800;">
                <p style="margin: 0; color: #f57c00;"><strong>📝 Notas Importantes:</strong></p>
                <ul style="margin: 10px 0; padding-left: 20px; color: #666;">
                    <li>Este respaldo se genera automáticamente cuando generas un reporte desde la aplicación</li>
                    <li>Conserva este correo para tus registros contables</li>
                    <li>El archivo PDF contiene el detalle completo de todas las transacciones</li>
                    <li>Si necesitas soporte, contacta al administrador del sistema</li>
                </ul>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <p style="background-color: #1976d2; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                    📱 Respaldo generado desde RioCaja Smart
                </p>
            </div>
            <hr style="border: 0; height: 1px; background: #ddd; margin: 30px 0;">
            <p style="margin: 0; color: #666; font-size: 12px; text-align: center;">
                Este es un mensaje automático generado por el sistema RioCaja Smart.<br>
                Por favor no respondas a este correo.
            </p>
            """

            html_body = self._get_base_template(content, "Respaldo Reporte de Cierre")
            result = self._send_email_with_attachment(
                recipient_email, 
                subject, 
                html_body, 
                temp_file_path, 
                pdf_filename
            )
            try:
                os.unlink(temp_file_path)
            except Exception:
                pass
            return result
        except Exception as e:
            logger.error(f"Error al enviar PDF por correo: {e}")
            return False

    def _send_email_with_attachment(self, to_email: str, subject: str, html_body: str, 
                                   attachment_path: str, attachment_name: str) -> bool:
        """Enviar email con archivo adjunto"""
        try:
            from email.mime.multipart import MIMEMultipart
            from email.mime.text import MIMEText
            from email.mime.base import MIMEBase
            from email import encoders

            message = MIMEMultipart()
            message["Subject"] = subject
            message["From"] = f"{self.mail_from_name} <{self.mail_from}>"
            message["To"] = to_email

            # Cuerpo HTML
            message.attach(MIMEText(html_body, "html", "utf-8"))

            # Adjuntar archivo
            with open(attachment_path, "rb") as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{attachment_name}"',
            )
            message.attach(part)

            import smtplib
            import ssl
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if MAIL_STARTTLS:
                    server.starttls(context=context)
                server.login(self.email_user, self.email_password)
                server.send_message(message)
            logger.info(f"✅ Email con PDF enviado a: {to_email}")
            return True
        except Exception as e:
            logger.error(f"Error al enviar email con adjunto: {e}")
            return False