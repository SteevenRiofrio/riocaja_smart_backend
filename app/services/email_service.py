# app/services/email_service.py - CORRECCIÓN DE CONFIGURACIÓN
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, Any, Optional
import logging

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
        subject = f"📢 Nuevo Mensaje - {self.company_name}"
        
        message_type_icons = {
            'informativo': '📋',
            'importante': '⚠️',
            'urgente': '🚨',
            'aviso': '📣'
        }
        
        tipo = message_data.get('tipo', 'informativo')
        icon = message_type_icons.get(tipo, '📋')
        
        content = f"""
        <h2 style="color: #1976d2; margin-bottom: 20px;">{icon} Nuevo Mensaje</h2>
        
        <p>Hola <strong>{user_name}</strong>,</p>
        <p>Tienes un nuevo mensaje en <strong>{self.company_name}</strong>:</p>
        
        <div style="background-color: #e3f2fd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #1976d2;">
            <h3 style="margin: 0 0 10px 0; color: #1976d2;">{message_data.get('titulo', 'Sin título')}</h3>
            <p style="margin: 10px 0; color: #333; line-height: 1.6;">{message_data.get('contenido', '')}</p>
            
            <hr style="border: 0; height: 1px; background: #1976d2; margin: 15px 0;">
            
            <p style="margin: 0; color: #666; font-size: 12px;">
                Este es un mensaje automático, por favor no respondas.
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Nuevo Mensaje")
        return self._send_email(user_email, subject, html_body)