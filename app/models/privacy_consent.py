from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base

class PrivacyConsent(Base):
    __tablename__ = "privacy_consents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    consent_version = Column(String(50), nullable=False)  # ej: "LOPDP_CNB_v1.0_2025"
    essential_consent = Column(Boolean, nullable=False, default=False)
    marketing_consent = Column(Boolean, nullable=False, default=False)
    consent_details = Column(Text)  # JSON con detalles técnicos
    consent_hash = Column(String(64), nullable=False)  # SHA256 para verificación
    ip_address = Column(String(45))  # IPv4 o IPv6
    user_agent = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
    
    # Relación con usuario
    user = relationship("User", back_populates="privacy_consents")

class DataRightRequest(Base):
    __tablename__ = "data_right_requests"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    right_type = Column(String(20), nullable=False)  # ACCESO, RECTIFICACION, etc.
    description = Column(Text)
    status = Column(String(20), default="PENDING")  # PENDING, PROCESSING, COMPLETED, REJECTED
    requested_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    response_details = Column(Text)  # Detalles de la respuesta
    processed_by = Column(String, nullable=True)  # ID del DPD que procesó
    
    # Relación con usuario
    user = relationship("User", back_populates="data_right_requests")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    event_details = Column(Text)  # JSON con detalles del evento
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    session_id = Column(String(100), nullable=True)
    
    # Relación con usuario (opcional, algunos eventos pueden ser del sistema)
    user = relationship("User", back_populates="audit_logs")