# app/services/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = os.getenv("SMTP_EMAIL", "riocaja.smart09@gmail.com")
        self.password = os.getenv("SMTP_PASSWORD", "espe@050702")
    
    def send_login_notification(self, user_email: str, user_name: str, login_info: dict):
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = user_email
            msg['Subject'] = "🔐 Inicio de sesion - RioCaja Smart"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #2e7d32; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🔐 RioCaja Smart</h2>
                    <p style="margin: 5px 0 0 0;">Notificacion de Seguridad</p>
                </div>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px;">
                    <h3 style="color: #2e7d32;">Inicio de Sesion Detectado</h3>
                    
                    <p>Hola <strong>{user_name}</strong>,</p>
                    
                    <p>Se ha detectado un nuevo inicio de sesion en tu cuenta de RioCaja Smart:</p>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
                        <p style="margin: 5px 0;"><strong>📅 Fecha y Hora:</strong> {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
                        <p style="margin: 5px 0;"><strong>👤 Usuario:</strong> {user_email}</p>
                        <p style="margin: 5px 0;"><strong>🏢 Rol:</strong> {login_info.get('rol', 'Usuario').title()}</p>
                        <p style="margin: 5px 0;"><strong>📱 Dispositivo:</strong> Aplicacion Movil</p>
                    </div>
                    
                    <div style="background-color: #e8f5e8; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>✅ Si fuiste tu:</strong> Puedes ignorar este mensaje.</p>
                    </div>
                    
                    <div style="background-color: #ffebee; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>⚠️ Si NO fuiste tu:</strong> Contacta inmediatamente al administrador del sistema.</p>
                    </div>
                    
                    <hr style="margin: 30px 0; border: 1px solid #ddd;">
                    
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        Este es un mensaje automatico de seguridad de RioCaja Smart.<br>
                        No respondas a este correo.<br>
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
            
            logger.info(f"Email de login enviado exitosamente a: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de login a {user_email}: {e}")
            return False
    
    def send_welcome_email(self, user_email: str, user_name: str):
        """Enviar email de bienvenida cuando se aprueba un usuario"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email
            msg['To'] = user_email
            msg['Subject'] = "🎉 Bienvenido a RioCaja Smart"
            
            body = f"""
            <html>
            <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
                <div style="background-color: #2e7d32; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                    <h2 style="margin: 0;">🎉 ¡Bienvenido!</h2>
                    <p style="margin: 5px 0 0 0;">RioCaja Smart</p>
                </div>
                
                <div style="background-color: #f5f5f5; padding: 20px; border-radius: 0 0 8px 8px;">
                    <h3 style="color: #2e7d32;">Tu cuenta ha sido aprobada</h3>
                    
                    <p>Hola <strong>{user_name}</strong>,</p>
                    
                    <p>¡Excelentes noticias! Tu cuenta de RioCaja Smart ha sido aprobada y ya puedes acceder al sistema.</p>
                    
                    <div style="background-color: white; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #2e7d32;">
                        <p style="margin: 5px 0;"><strong>📧 Tu usuario:</strong> {user_email}</p>
                        <p style="margin: 5px 0;"><strong>📱 Acceso:</strong> Aplicacion Movil RioCaja Smart</p>
                        <p style="margin: 5px 0;"><strong>🏢 Sistema:</strong> Gestion de Comprobantes CNB</p>
                    </div>
                    
                    <div style="background-color: #e3f2fd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                        <p style="margin: 0;"><strong>📋 Proximos pasos:</strong></p>
                        <ol style="margin: 10px 0;">
                            <li>Inicia sesion en la aplicacion</li>
                            <li>Completa tu perfil con el codigo de corresponsal</li>
                            <li>Comienza a gestionar comprobantes</li>
                        </ol>
                    </div>
                    
                    <p style="text-align: center;">
                        <strong>¡Gracias por usar RioCaja Smart!</strong>
                    </p>
                    
                    <hr style="margin: 30px 0; border: 1px solid #ddd;">
                    
                    <p style="font-size: 12px; color: #666; text-align: center;">
                        © 2025 RioCaja Smart - Sistema de Gestion de Comprobantes CNB<br>
                        Si tienes dudas, contacta al administrador del sistema.
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
            
            logger.info(f"Email de bienvenida enviado a: {user_email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de bienvenida a {user_email}: {e}")
            return False
    
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