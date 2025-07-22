from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from enum import Enum

from app.database import Base

# Enums para tipos válidos
class EstadoEnum(str, Enum):
    pendiente = "pendiente"
    activo = "activo"
    inactivo = "inactivo"

class RolEnum(str, Enum):
    admin = "admin"
    asesor = "asesor"      # Asesor de Corresponsalía
    cnb = "cnb"           # Corresponsal No Bancario

class User(Base):
    """
    Modelo SQLAlchemy para usuarios en base de datos
    """
    __tablename__ = "users"
    
    # Campos principales
    id = Column(String(255), primary_key=True, index=True)
    nombre = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    
    # Rol y estado
    rol = Column(SQLEnum(RolEnum), nullable=False, default=RolEnum.cnb)
    estado = Column(SQLEnum(EstadoEnum), nullable=False, default=EstadoEnum.pendiente)
    
    # Fechas importantes
    fecha_registro = Column(DateTime(timezone=True), nullable=False, 
                           server_default=func.now())
    fecha_aprobacion = Column(DateTime(timezone=True), nullable=True)
    fecha_perfil_completado = Column(DateTime(timezone=True), nullable=True)
    
    # Estados y configuración
    perfil_completo = Column(Boolean, nullable=False, default=False)
    activo = Column(Boolean, nullable=False, default=True)  # Para filtros
    intentos_fallidos = Column(Integer, nullable=False, default=0)
    
    # Campos específicos de CNB
    nombre_local = Column(String(255), nullable=True)
    codigo_corresponsal = Column(String(50), nullable=True, unique=True, index=True)
    aprobado_por = Column(String(255), nullable=True)
    
    # Campos adicionales para auditoría
    created_at = Column(DateTime(timezone=True), nullable=False, 
                       server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, 
                       server_default=func.now(), onupdate=func.now())
    
    # 🔐 NUEVAS RELACIONES PARA PRIVACIDAD
    privacy_consents = relationship(
        "PrivacyConsent", 
        back_populates="user",
        cascade="all, delete-orphan",  # Eliminar consentimientos si se elimina usuario
        lazy="select"  # Cargar cuando se acceda
    )
    
    data_right_requests = relationship(
        "DataRightRequest", 
        back_populates="user",
        cascade="all, delete-orphan",  # Eliminar solicitudes si se elimina usuario
        lazy="select"
    )
    
    audit_logs = relationship(
        "AuditLog", 
        back_populates="user",
        cascade="all, delete-orphan",  # Eliminar logs si se elimina usuario
        lazy="select"
    )
    
    def __repr__(self):
        return f"<User(id='{self.id}', email='{self.email}', rol='{self.rol}')>"
    
    # Métodos útiles para privacidad
    def get_active_consent(self):
        """Obtener consentimiento activo más reciente"""
        return next(
            (consent for consent in self.privacy_consents 
             if consent.is_active), 
            None
        )
    
    def has_valid_privacy_consent(self):
        """Verificar si tiene consentimiento de privacidad válido"""
        active_consent = self.get_active_consent()
        if not active_consent:
            return False
        
        # Verificar vigencia (1 año)
        from datetime import datetime, timedelta
        expiry_date = active_consent.created_at + timedelta(days=365)
        return datetime.utcnow() < expiry_date
    
    def get_pending_right_requests(self):
        """Obtener solicitudes de derechos pendientes"""
        return [req for req in self.data_right_requests 
                if req.status == "PENDING"]