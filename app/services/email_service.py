import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.from_email = os.getenv('FROM_EMAIL', self.smtp_user)
        self.company_name = "RioCaja Smart"

        # Validar configuración
        if not all([self.smtp_user, self.smtp_password]):
            logger.warning("Configuración de email incompleta. Emails no se enviarán.")

    def send_password_reset_email(self, user_email: str, reset_code: str):
        """Enviar email con codigo de recuperacion de contraseña"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = user_email
            msg['Subject'] = "🔑 Recuperacion de contraseña - RioCaja Smart"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #2e7d32; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🔑 RioCaja Smart</h2>
                    <p style="margin: 5px 0 0 0;">Recuperacion de Contraseña</p>
                </div>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px;">
                    <h3 style="color: #2e7d32;">Codigo de Recuperacion</h3>
                    
                    <p>Hola,</p>
                    
                    <p>Has solicitado recuperar tu contraseña. Usa el siguiente codigo en la aplicacion:</p>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0; text-align: center; border: 2px dashed #2e7d32;">
                        <h2 style="margin: 0; color: #2e7d32; font-size: 36px; letter-spacing: 8px;">{reset_code}</h2>
                    </div>
                    
                    <div style="background-color: #fff3e0; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>⏰ Importante:</strong> Este codigo expira en 15 minutos por seguridad.</p>
                    </div>
                    
                    <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>⚠️ Si no solicitaste esto:</strong> Ignora este mensaje. Tu cuenta sigue segura.</p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: 1px solid #ddd;">
                    
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        © 2025 RioCaja Smart - Sistema de Gestion de Comprobantes CNB
                    </p>
                </div>
            </body>
            </html>
            """
            
            msg.attach(MIMEText(body, 'html'))
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email de recuperacion enviado a: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de recuperacion a {user_email}: {e}")
            return False

    def _send_email(self, to_email: str, subject: str, html_body: str) -> bool:
        """Método base para envío de emails"""
        try:
            if not all([self.smtp_user, self.smtp_password]):
                logger.warning(f"Email no enviado a {to_email}: Configuración incompleta")
                return False
            
            # Crear mensaje
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.company_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Adjuntar HTML
            html_part = MIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Crear conexión SMTP segura
            context = ssl.create_default_context()
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls(context=context)
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email enviado exitosamente a: {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email a {to_email}: {e}")
            return False
    
    def _get_base_template(self, content: str, title: str = "Notificación") -> str:
        """Template base para todos los emails"""
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{title}</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 0; padding: 20px; background-color: #f4f4f4;">
            <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                
                <!-- Header -->
                <div style="text-align: center; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #2e7d32;">
                    <h1 style="color: #2e7d32; margin: 0; font-size: 28px;">🏦 {self.company_name}</h1>
                    <p style="color: #666; margin: 5px 0 0 0; font-size: 14px;">Sistema de Gestión de Comprobantes CNB</p>
                </div>
                
                <!-- Content -->
                {content}
                
                <!-- Footer -->
                <hr style="margin: 30px 0; border: 1px solid #ddd;">
                <p style="font-size: 12px; color: #666; text-align: center; margin: 0;">
                    © 2025 {self.company_name} - Sistema de Gestión de Comprobantes CNB<br>
                    Este es un mensaje automático, no responder a este correo.<br>
                    Si tienes dudas, contacta al administrador del sistema.
                </p>
            </div>
        </body>
        </html>
        """
    
    # ================================
    # NOTIFICACIONES DE REGISTRO
    # ================================
    
    def send_registration_confirmation(self, user_email: str, user_name: str) -> bool:
        """Email al usuario cuando se registra (cuenta pendiente)"""
        subject = f"🔔 Registro Exitoso en {self.company_name}"
        
        content = f"""
        <h2 style="color: #2e7d32; margin-bottom: 20px;">¡Bienvenido {user_name}!</h2>
        
        <p>Tu registro en <strong>{self.company_name}</strong> ha sido exitoso.</p>
        
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
            <p style="margin: 0;"><strong>📋 Estado de tu cuenta:</strong> PENDIENTE DE ACTIVACIÓN</p>
        </div>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0 0 10px 0;"><strong>📧 Detalles de registro:</strong></p>
            <ul style="margin: 0; padding-left: 20px;">
                <li><strong>Email:</strong> {user_email}</li>
                <li><strong>Fecha:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</li>
                <li><strong>Sistema:</strong> Gestión de Comprobantes CNB</li>
            </ul>
        </div>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>⏳ Próximos pasos:</strong></p>
            <ol style="margin: 10px 0;">
                <li>Tu cuenta está en <strong>espera de activación</strong></li>
                <li>Un asesor revisará y activará tu cuenta</li>
                <li>Recibirás un email cuando tu cuenta sea aprobada</li>
                <li>Podrás iniciar sesión una vez activada</li>
            </ol>
        </div>
        
        <p style="text-align: center; margin-top: 30px;">
            <strong>¡Gracias por unirte a {self.company_name}!</strong>
        </p>
        """
        
        html_body = self._get_base_template(content, "Registro Exitoso")
        return self._send_email(user_email, subject, html_body)
    
    def send_new_user_notification_to_advisors(self, user_data: Dict[str, Any], advisor_emails: List[str]) -> bool:
        """Notificación a asesores sobre nuevo usuario pendiente"""
        subject = f"🔔 Nuevo Usuario Pendiente - {self.company_name}"
        
        content = f"""
        <h2 style="color: #d32f2f; margin-bottom: 20px;">⚠️ Nuevo Usuario Pendiente</h2>
        
        <p>Se ha registrado un nuevo usuario que requiere <strong>revisión y activación</strong>.</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d32f2f;">
            <p style="margin: 5px 0;"><strong>👤 Nombre:</strong> {user_data.get('nombre', 'No especificado')}</p>
            <p style="margin: 5px 0;"><strong>📧 Email:</strong> {user_data.get('email', 'No especificado')}</p>
            <p style="margin: 5px 0;"><strong>🏷️ Rol solicitado:</strong> {user_data.get('rol', 'CNB').upper()}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha registro:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>📋 Acciones requeridas:</strong></p>
            <ol style="margin: 10px 0;">
                <li>Revisar los datos del usuario</li>
                <li>Asignar código de corresponsal</li>
                <li>Asignar rol apropiado</li>
                <li>Activar o rechazar la cuenta</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #2e7d32; color: white; padding: 12px 24px; border-radius: 6px; display: inline-block; margin: 0;">
                💻 Accede al panel de administración para gestionar este usuario
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Nuevo Usuario Pendiente")
        
        # Enviar a todos los asesores
        success_count = 0
        for advisor_email in advisor_emails:
            if self._send_email(advisor_email, subject, html_body):
                success_count += 1
        
        return success_count > 0
    
    # ================================
    # NOTIFICACIONES DE CAMBIO DE ESTADO
    # ================================
    
    def send_account_approved_notification(self, user_email: str, user_name: str, codigo_corresponsal: str) -> bool:
        """Email cuando la cuenta es activada/aprobada"""
        subject = f"✅ Cuenta Aprobada - {self.company_name}"
        
        content = f"""
        <h2 style="color: #2e7d32; margin-bottom: 20px;">🎉 ¡Cuenta Aprobada!</h2>
        
        <p>¡Excelentes noticias {user_name}!</p>
        <p>Tu cuenta de <strong>{self.company_name}</strong> ha sido <strong>APROBADA</strong> y ya está lista para usar.</p>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>📧 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>🆔 Código Corresponsal:</strong> <span style="background-color: #c8e6c9; padding: 2px 8px; border-radius: 4px; font-family: monospace; font-weight: bold;">{codigo_corresponsal}</span></p>
            <p style="margin: 5px 0;"><strong>📱 Acceso:</strong> Aplicación Móvil {self.company_name}</p>
            <p style="margin: 5px 0;"><strong>🏢 Sistema:</strong> Gestión de Comprobantes CNB</p>
        </div>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>📋 Próximos pasos:</strong></p>
            <ol style="margin: 10px 0;">
                <li>Inicia sesión en la aplicación</li>
                <li>Completa tu perfil con el código de corresponsal</li>
                <li>Comienza a gestionar comprobantes</li>
            </ol>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #2e7d32; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0; font-size: 16px;">
                🚀 ¡Tu cuenta está lista para usar!
            </p>
        </div>
        
        <p style="text-align: center;">
            <strong>¡Bienvenido al equipo de {self.company_name}!</strong>
        </p>
        """
        
        html_body = self._get_base_template(content, "Cuenta Aprobada")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_suspended_notification(self, user_email: str, user_name: str, reason: str = None) -> bool:
        """Email cuando la cuenta es suspendida"""
        subject = f"⚠️ Cuenta Suspendida - {self.company_name}"
        
        reason_text = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        content = f"""
        <h2 style="color: #ff9800; margin-bottom: 20px;">⚠️ Cuenta Suspendida</h2>
        
        <p>Estimado/a {user_name},</p>
        <p>Te informamos que tu cuenta en <strong>{self.company_name}</strong> ha sido <strong>SUSPENDIDA</strong>.</p>
        
        <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ff9800;">
            <p style="margin: 5px 0;"><strong>📧 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha suspensión:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            {reason_text}
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>🚫 Restricciones:</strong></p>
            <ul style="margin: 10px 0;">
                <li>No podrás acceder al sistema</li>
                <li>Todas las funciones están deshabilitadas</li>
                <li>Debes contactar al administrador</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #ff9800; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                📞 Contacta al administrador para resolver esta situación
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Cuenta Suspendida")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_deactivated_notification(self, user_email: str, user_name: str, reason: str = None) -> bool:
        """Email cuando la cuenta es inactivada"""
        subject = f"🔒 Cuenta Inactiva - {self.company_name}"
        
        reason_text = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        content = f"""
        <h2 style="color: #607d8b; margin-bottom: 20px;">🔒 Cuenta Inactiva</h2>
        
        <p>Estimado/a {user_name},</p>
        <p>Tu cuenta en <strong>{self.company_name}</strong> ha sido marcada como <strong>INACTIVA</strong>.</p>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #607d8b;">
            <p style="margin: 5px 0;"><strong>📧 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha inactivación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            {reason_text}
        </div>
        
        <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>ℹ️ ¿Qué significa esto?</strong></p>
            <ul style="margin: 10px 0;">
                <li>Tu cuenta está temporalmente deshabilitada</li>
                <li>No puedes acceder al sistema</li>
                <li>Puedes solicitar reactivación al administrador</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #607d8b; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                📧 Contacta al administrador para reactivar tu cuenta
            </p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Cuenta Inactiva")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_deleted_notification(self, user_email: str, user_name: str, reason: str = None) -> bool:
        """Email cuando la cuenta es eliminada"""
        subject = f"🗑️ Cuenta Eliminada - {self.company_name}"
        
        reason_text = f"<p><strong>Motivo:</strong> {reason}</p>" if reason else ""
        
        content = f"""
        <h2 style="color: #d32f2f; margin-bottom: 20px;">🗑️ Cuenta Eliminada</h2>
        
        <p>Estimado/a {user_name},</p>
        <p>Te informamos que tu cuenta en <strong>{self.company_name}</strong> ha sido <strong>ELIMINADA</strong> del sistema.</p>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #d32f2f;">
            <p style="margin: 5px 0;"><strong>📧 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>📅 Fecha eliminación:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            {reason_text}
        </div>
        
        <div style="background-color: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>⚠️ Información importante:</strong></p>
            <ul style="margin: 10px 0;">
                <li>Tu cuenta ha sido eliminada permanentemente</li>
                <li>Ya no tienes acceso al sistema</li>
                <li>Todos tus datos han sido removidos</li>
                <li>Si necesitas acceso nuevamente, debes registrarte otra vez</li>
            </ul>
        </div>
        
        <div style="text-align: center; margin: 30px 0;">
            <p style="background-color: #d32f2f; color: white; padding: 15px 30px; border-radius: 6px; display: inline-block; margin: 0;">
                🔍 Contacta al administrador si tienes dudas sobre esta acción
            </p>
        </div>
        
        <p style="text-align: center;">
            Gracias por haber usado <strong>{self.company_name}</strong>
        </p>
        """
        
        html_body = self._get_base_template(content, "Cuenta Eliminada")
        return self._send_email(user_email, subject, html_body)
    
    def send_account_rejected_notification(self, user_email: str, user_name: str, reason: str = None) -> bool:
        """Email cuando la cuenta es rechazada"""
        subject = f"❌ Registro Rechazado - {self.company_name}"
        
        reason_text = f"<p><strong>Motivo del rechazo:</strong> {reason}</p>" if reason else ""
        
        content = f"""
        <h2 style="color: #d32f2f; margin-bottom: 20px;">❌ Registro Rechazado</h2>
        
        <p>Estimado/a {user_name},</p>
        <p>Lamentamos informarte que tu solicitud de registro en <strong>{self.company_name}</strong> ha sido <strong>RECHAZADA</strong>.</p>
        
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
    
    # ================================
    # NOTIFICACIONES mejoradas
    # ================================
    
    def send_welcome_email(self, user_email: str, user_name: str) -> bool:
        """Email de bienvenida mejorado"""
        return self.send_account_approved_notification(user_email, user_name, "Por asignar")
    
    def send_login_notification(self, user_email: str, user_name: str, login_info: Dict[str, Any]) -> bool:
        """Notificación de inicio de sesión (existente, mejorada)"""
        subject = f"🔐 Inicio de Sesión Detectado - {self.company_name}"
        
        content = f"""
        <h2 style="color: #1976d2; margin-bottom: 20px;">🔐 Inicio de Sesión Detectado</h2>
        
        <p>Hola {user_name},</p>
        <p>Se ha detectado un nuevo inicio de sesión en tu cuenta de <strong>{self.company_name}</strong>.</p>
        
        <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
            <p style="margin: 5px 0;"><strong>📅 Fecha y Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
            <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {user_email}</p>
            <p style="margin: 5px 0;"><strong>🏢 Rol:</strong> {login_info.get('rol', 'Usuario').title()}</p>
            <p style="margin: 5px 0;"><strong>📱 Dispositivo:</strong> Aplicación Móvil</p>
        </div>
        
        <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>✅ Si fuiste tú:</strong> Puedes ignorar este mensaje.</p>
        </div>
        
        <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
            <p style="margin: 0;"><strong>⚠️ Si NO fuiste tú:</strong> Contacta inmediatamente al administrador del sistema.</p>
        </div>
        """
        
        html_body = self._get_base_template(content, "Inicio de Sesión")
        return self._send_email(user_email, subject, html_body)
    
    # ================================
    # MÉTODOS AUXILIARES
    # ================================
    
    def get_advisor_emails(self) -> List[str]:
        """Obtener emails de asesores desde la base de datos"""
        try:
            from app.services.user_service import UserService
            user_service = UserService()
            advisors = user_service.get_users_by_role("asesor")
            return [advisor.get("email") for advisor in advisors if advisor.get("email")]
        except Exception as e:
            logger.error(f"Error obteniendo emails de asesores: {e}")
            return []
    
    def send_bulk_notification(self, recipient_emails: List[str], subject: str, content: str) -> Dict[str, int]:
        """Enviar notificación a múltiples destinatarios"""
        html_body = self._get_base_template(content, subject)
        
        success_count = 0
        failed_count = 0
        
        for email in recipient_emails:
            if self._send_email(email, subject, html_body):
                success_count += 1
            else:
                failed_count += 1
        
        return {
            "success": success_count,
            "failed": failed_count,
            "total": len(recipient_emails)
        }