# app/models/user.py - VERSIÓN CORREGIDA E INTEGRADA
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime, timedelta
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
    
    # 🆕 NUEVOS CAMPOS PARA TÉRMINOS Y CONDICIONES
    acepto_terminos = Column(Boolean, nullable=False, default=False)
    fecha_acepta_terminos = Column(DateTime(timezone=True), nullable=True)
    
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
    
    # 🔐 RELACIONES PARA PRIVACIDAD (existentes)
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
    
    # ✅ NUEVOS MÉTODOS PARA TÉRMINOS Y CONDICIONES
    def has_accepted_terms(self):
        """Verificar si el usuario ha aceptado términos y condiciones"""
        return self.acepto_terminos == True
    
    def accept_terms(self):
        """Marcar términos como aceptados"""
        self.acepto_terminos = True
        self.fecha_acepta_terminos = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def reject_terms(self):
        """Marcar términos como rechazados"""
        self.acepto_terminos = False
        self.fecha_acepta_terminos = None
        self.updated_at = datetime.utcnow()
    
    def needs_terms_acceptance(self):
        """Verificar si necesita aceptar términos"""
        return not self.acepto_terminos
    
    def get_terms_acceptance_date(self):
        """Obtener fecha de aceptación de términos"""
        return self.fecha_acepta_terminos
    
    # Métodos existentes para privacidad
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
        expiry_date = active_consent.created_at + timedelta(days=365)
        return datetime.utcnow() < expiry_date
    
    def get_pending_right_requests(self):
        """Obtener solicitudes de derechos pendientes"""
        return [req for req in self.data_right_requests 
                if req.status == "PENDING"]
    
    # ✅ MÉTODO COMBINADO: Verificar cumplimiento total
    def is_compliant_user(self):
        """
        Verificar si el usuario cumple con todos los requisitos:
        - Ha aceptado términos y condiciones
        - Tiene consentimiento de privacidad válido
        - Está activo y aprobado
        """
        return (
            self.has_accepted_terms() and
            self.has_valid_privacy_consent() and
            self.activo and
            self.estado == EstadoEnum.activo
        )