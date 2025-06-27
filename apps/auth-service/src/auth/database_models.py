"""Database models for Auth Service"""
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, ForeignKey, Index, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime

Base = declarative_base()

class Application(Base):
    """Applications that can be protected by auth service"""
    __tablename__ = 'auth_applications'
    
    id = Column(Integer, primary_key=True)
    app_name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=False)
    description = Column(Text)
    callback_urls = Column(Text)  # JSON array of allowed callback URLs
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    permissions = relationship("UserAppPermission", back_populates="application", cascade="all, delete-orphan")
    access_logs = relationship("AccessLog", back_populates="application")
    
    __table_args__ = (
        Index('idx_app_active', 'app_name', 'is_active'),
    )


class AuthorizedUser(Base):
    """Users authorized to access applications"""
    __tablename__ = 'auth_authorized_users'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)  # Can manage other users
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)  # Email of user who created this entry
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text)  # Admin notes about this user
    
    # Relationships
    permissions = relationship("UserAppPermission", back_populates="user", cascade="all, delete-orphan")
    granted_permissions = relationship("UserAppPermission", foreign_keys="UserAppPermission.granted_by_user_id")
    
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
    )


class UserAppPermission(Base):
    """Many-to-many relationship between users and applications"""
    __tablename__ = 'auth_user_app_permissions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('auth_authorized_users.id'), nullable=False)
    app_id = Column(Integer, ForeignKey('auth_applications.id'), nullable=False)
    granted_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    granted_by_user_id = Column(Integer, ForeignKey('auth_authorized_users.id'), nullable=False)
    expires_at = Column(DateTime)  # Optional expiration date
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text)  # Notes about why access was granted
    
    # Relationships
    user = relationship("AuthorizedUser", back_populates="permissions", foreign_keys=[user_id])
    application = relationship("Application", back_populates="permissions")
    granted_by = relationship("AuthorizedUser", foreign_keys=[granted_by_user_id])
    
    __table_args__ = (
        Index('idx_user_app_permission', 'user_id', 'app_id', 'is_active'),
        Index('idx_permission_expires', 'expires_at'),
    )


class AccessLog(Base):
    """Log of all access attempts"""
    __tablename__ = 'auth_access_logs'
    
    id = Column(Integer, primary_key=True)
    email = Column(String(255), nullable=False, index=True)
    app_id = Column(Integer, ForeignKey('auth_applications.id'))
    app_name = Column(String(100), nullable=False)  # Denormalized for faster queries
    access_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    access_granted = Column(Boolean, nullable=False)
    denial_reason = Column(String(255))  # e.g., "User not found", "User inactive", "No permission for app"
    ip_address = Column(String(45))  # IPv4 or IPv6
    user_agent = Column(Text)
    additional_info = Column(Text)  # JSON for any extra data
    
    # Relationships
    application = relationship("Application", back_populates="access_logs")
    
    __table_args__ = (
        Index('idx_access_log_email_time', 'email', 'access_time'),
        Index('idx_access_log_app_time', 'app_name', 'access_time'),
        Index('idx_access_log_granted', 'access_granted', 'access_time'),
    )


class ApiKey(Base):
    """API keys for service-to-service authentication"""
    __tablename__ = 'auth_api_keys'
    
    id = Column(Integer, primary_key=True)
    key_hash = Column(String(255), unique=True, nullable=False)  # SHA256 hash of the key
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by = Column(String(255), nullable=False)
    last_used_at = Column(DateTime)
    expires_at = Column(DateTime)
    allowed_ips = Column(Text)  # JSON array of allowed IP addresses/ranges
    is_admin = Column(Boolean, default=False, nullable=False)
    
    __table_args__ = (
        Index('idx_api_key_active', 'key_hash', 'is_active'),
    )


class AuditLog(Base):
    """Audit log for admin actions"""
    __tablename__ = 'auth_audit_logs'
    
    id = Column(Integer, primary_key=True)
    admin_email = Column(String(255), nullable=False, index=True)
    action = Column(String(100), nullable=False)  # e.g., "create_user", "grant_permission", "revoke_permission"
    target_email = Column(String(255))  # User affected by the action
    target_app = Column(String(100))  # App affected by the action
    action_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    details = Column(Text)  # JSON with additional details
    ip_address = Column(String(45))
    
    __table_args__ = (
        Index('idx_audit_admin_time', 'admin_email', 'action_time'),
        Index('idx_audit_action_time', 'action', 'action_time'),
    )


# Placeholder for the session factory - will be replaced by app.py
def get_db_session():
    """Placeholder for database session dependency"""
    raise NotImplementedError("This function is replaced at runtime by app.py")