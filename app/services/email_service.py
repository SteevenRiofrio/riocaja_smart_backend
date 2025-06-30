# app/services/email_service.py
import random
import string
from datetime import datetime, timedelta
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Template
from app.config import (
    MAIL_USERNAME, MAIL_PASSWORD, MAIL_FROM, MAIL_FROM_NAME,
    MAIL_PORT, MAIL_SERVER, MAIL_STARTTLS, MAIL_SSL_TLS,
    RESET_CODE_EXPIRE_MINUTES, RESET_CODE_LENGTH
)
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        # Configuracion de conexion SMTP
        self.conf = ConnectionConfig(
            MAIL_USERNAME=MAIL_USERNAME,
            MAIL_PASSWORD=MAIL_PASSWORD,
            MAIL_FROM=MAIL_FROM,
            MAIL_PORT=MAIL_PORT,
            MAIL_SERVER=MAIL_SERVER,
            MAIL_STARTTLS=MAIL_STARTTLS,
            MAIL_SSL_TLS=MAIL_SSL_TLS,
            USE_CREDENTIALS=True,
            VALIDATE_CERTS=True
        )
        self.fastmail = FastMail(self.conf)
    
    def generate_reset_code(self) -> str:
        """Genera un codigo de recuperacion de 6 digitos"""
        return ''.join(random.choices(string.digits, k=RESET_CODE_LENGTH))
    
    def get_reset_code_expiry(self) -> datetime:
        """Obtiene la fecha de expiracion del codigo"""
        return datetime.utcnow() + timedelta(minutes=RESET_CODE_EXPIRE_MINUTES)
    
    async def send_password_reset_email(self, email: str, name: str, reset_code: str) -> bool:
        """
        Envia email de recuperacion de contraseña
        
        Args:
            email: Email del usuario
            name: Nombre del usuario
            reset_code: Codigo de recuperacion generado
            
        Returns:
            bool: True si se envio correctamente, False en caso contrario
        """
        try:
            # Template HTML para el email
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Recuperacion de Contraseña - RioCaja Smart</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        border-radius: 10px;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }
                    .header {
                        background: linear-gradient(135deg, #4CAF50, #45a049);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }
                    .header h1 {
                        margin: 0;
                        font-size: 28px;
                        font-weight: 300;
                    }
                    .content {
                        padding: 40px 30px;
                    }
                    .greeting {
                        font-size: 18px;
                        margin-bottom: 20px;
                        color: #555;
                    }
                    .code-container {
                        background: linear-gradient(135deg, #e8f5e8, #f0f8f0);
                        border: 2px solid #4CAF50;
                        border-radius: 10px;
                        padding: 30px;
                        text-align: center;
                        margin: 30px 0;
                    }
                    .code {
                        font-size: 36px;
                        font-weight: bold;
                        color: #2E7D32;
                        letter-spacing: 8px;
                        margin: 10px 0;
                        font-family: 'Courier New', monospace;
                    }
                    .code-label {
                        font-size: 14px;
                        color: #666;
                        margin-bottom: 10px;
                    }
                    .instructions {
                        background-color: #f9f9f9;
                        border-left: 4px solid #4CAF50;
                        padding: 20px;
                        margin: 20px 0;
                    }
                    .warning {
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 5px;
                        padding: 15px;
                        margin: 20px 0;
                        color: #856404;
                    }
                    .footer {
                        background-color: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 12px;
                        color: #666;
                        border-top: 1px solid #dee2e6;
                    }
                    .expiry {
                        color: #e74c3c;
                        font-weight: bold;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>RioCaja Smart</h1>
                        <p>Recuperacion de Contraseña</p>
                    </div>
                    
                    <div class="content">
                        <div class="greeting">
                            Hola {{ name }}!
                        </div>
                        
                        <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta en <strong>RioCaja Smart</strong>.</p>
                        
                        <div class="code-container">
                            <div class="code-label">Tu codigo de verificacion es:</div>
                            <div class="code">{{ reset_code }}</div>
                            <div style="font-size: 12px; color: #666; margin-top: 10px;">
                                Este codigo <span class="expiry">expira en 10 minutos</span>
                            </div>
                        </div>
                        
                        <div class="instructions">
                            <h3>Instrucciones:</h3>
                            <ol>
                                <li>Abre la aplicacion RioCaja Smart</li>
                                <li>Ingresa este codigo en la pantalla de verificacion</li>
                                <li>Crea tu nueva contraseña</li>
                                <li>Listo! Ya puedes acceder con tu nueva contraseña</li>
                            </ol>
                        </div>
                        
                        <div class="warning">
                            <strong>Importante:</strong><br>
                            Si no solicitaste este cambio, ignora este mensaje<br>
                            No compartas este codigo con nadie<br>
                            El codigo expira automaticamente en 10 minutos<br>
                            Solo puedes usar este codigo una vez
                        </div>
                        
                        <p>Si tienes problemas, contacta al administrador de tu sistema.</p>
                        
                        <p style="margin-top: 30px; color: #666;">
                            Saludos,<br>
                            <strong>El equipo de RioCaja Smart</strong>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>Este es un mensaje automatico, por favor no respondas a este correo.</p>
                        <p>2025 RioCaja Smart - Sistema de Gestion de Comprobantes CNB</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Renderizar template con los datos
            template = Template(html_template)
            html_content = template.render(
                name=name,
                reset_code=reset_code
            )
            
            # Crear mensaje
            message = MessageSchema(
                subject="Recuperacion de Contraseña - RioCaja Smart",
                recipients=[email],
                body=html_content,
                subtype="html"
            )
            
            # Enviar email
            await self.fastmail.send_message(message)
            
            logger.info(f"Email de recuperacion enviado exitosamente a: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando email de recuperacion a {email}: {str(e)}")
            return False
    
    async def send_password_changed_notification(self, email: str, name: str) -> bool:
        """
        Envia notificacion de que la contraseña fue cambiada exitosamente
        
        Args:
            email: Email del usuario
            name: Nombre del usuario
            
        Returns:
            bool: True si se envio correctamente, False en caso contrario
        """
        try:
            html_template = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Contraseña Actualizada - RioCaja Smart</title>
                <style>
                    body {
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                        line-height: 1.6;
                        color: #333;
                        background-color: #f5f5f5;
                        margin: 0;
                        padding: 20px;
                    }
                    .container {
                        max-width: 600px;
                        margin: 0 auto;
                        background-color: white;
                        border-radius: 10px;
                        box-shadow: 0 0 20px rgba(0,0,0,0.1);
                        overflow: hidden;
                    }
                    .header {
                        background: linear-gradient(135deg, #4CAF50, #45a049);
                        color: white;
                        padding: 30px;
                        text-align: center;
                    }
                    .content {
                        padding: 40px 30px;
                    }
                    .success-icon {
                        text-align: center;
                        font-size: 60px;
                        margin: 20px 0;
                    }
                    .footer {
                        background-color: #f8f9fa;
                        padding: 20px 30px;
                        text-align: center;
                        font-size: 12px;
                        color: #666;
                    }
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>RioCaja Smart</h1>
                        <p>Contraseña Actualizada</p>
                    </div>
                    
                    <div class="content">
                        <div class="success-icon">✓</div>
                        
                        <h2 style="text-align: center; color: #4CAF50;">Contraseña Actualizada Exitosamente!</h2>
                        
                        <p>Hola <strong>{{ name }}</strong>,</p>
                        
                        <p>Te confirmamos que tu contraseña ha sido actualizada correctamente en <strong>RioCaja Smart</strong>.</p>
                        
                        <div style="background-color: #e8f5e8; border: 1px solid #4CAF50; border-radius: 5px; padding: 15px; margin: 20px 0;">
                            <strong>Cambio realizado el:</strong> {{ timestamp }}<br>
                            <strong>Cuenta:</strong> {{ email }}
                        </div>
                        
                        <p>Ya puedes iniciar sesion con tu nueva contraseña.</p>
                        
                        <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; border-radius: 5px; padding: 15px; margin: 20px 0;">
                            <strong>Si no realizaste este cambio:</strong><br>
                            Contacta inmediatamente al administrador de tu sistema, ya que alguien mas podria haber accedido a tu cuenta.
                        </div>
                        
                        <p style="margin-top: 30px;">
                            Saludos,<br>
                            <strong>El equipo de RioCaja Smart</strong>
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p>2025 RioCaja Smart - Sistema de Gestion de Comprobantes CNB</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            template = Template(html_template)
            html_content = template.render(
                name=name,
                email=email,
                timestamp=datetime.now().strftime("%d/%m/%Y a las %H:%M")
            )
            
            message = MessageSchema(
                subject="Contraseña actualizada - RioCaja Smart",
                recipients=[email],
                body=html_content,
                subtype="html"
            )
            
            await self.fastmail.send_message(message)
            
            logger.info(f"Notificacion de cambio de contraseña enviada a: {email}")
            return True
            
        except Exception as e:
            logger.error(f"Error enviando notificacion a {email}: {str(e)}")
            return False