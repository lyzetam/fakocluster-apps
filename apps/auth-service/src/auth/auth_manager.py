"""Authorization Manager for Auth Service"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import hashlib
import json
from cachetools import TTLCache
import ipaddress

from database_models import (
    AuthorizedUser, Application, UserAppPermission, 
    AccessLog, ApiKey, AuditLog
)
import config

logger = logging.getLogger(__name__)

class AuthorizationManager:
    """Manages authorization checks and user permissions"""
    
    def __init__(self):
        """Initialize the authorization manager"""
        # Initialize caches
        if config.ENABLE_CACHING:
            self.auth_cache = TTLCache(maxsize=1000, ttl=config.CACHE_TTL_SECONDS)
            self.negative_cache = TTLCache(maxsize=1000, ttl=config.NEGATIVE_CACHE_TTL_SECONDS)
        else:
            self.auth_cache = None
            self.negative_cache = None
    
    def check_authorization(self, 
                          db: Session, 
                          email: str, 
                          app_name: str,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Check if a user is authorized to access an application
        
        Args:
            db: Database session
            email: User's email address
            app_name: Application name to check access for
            ip_address: Client IP address (for logging)
            user_agent: Client user agent (for logging)
            
        Returns:
            Tuple of (is_authorized, denial_reason)
        """
        cache_key = f"{email}:{app_name}"
        
        # Check positive cache
        if self.auth_cache and cache_key in self.auth_cache:
            logger.debug(f"Cache hit for {cache_key}")
            self._log_access(db, email, app_name, True, None, ip_address, user_agent)
            return True, None
        
        # Check negative cache
        if self.negative_cache and cache_key in self.negative_cache:
            logger.debug(f"Negative cache hit for {cache_key}")
            denial_reason = self.negative_cache[cache_key]
            self._log_access(db, email, app_name, False, denial_reason, ip_address, user_agent)
            return False, denial_reason
        
        # Perform authorization check
        is_authorized, denial_reason = self._perform_authorization_check(db, email, app_name)
        
        # Update cache
        if config.ENABLE_CACHING:
            if is_authorized:
                self.auth_cache[cache_key] = True
            else:
                self.negative_cache[cache_key] = denial_reason
        
        # Log access attempt
        self._log_access(db, email, app_name, is_authorized, denial_reason, ip_address, user_agent)
        
        return is_authorized, denial_reason
    
    def _perform_authorization_check(self, db: Session, email: str, app_name: str) -> Tuple[bool, Optional[str]]:
        """
        Perform the actual authorization check against the database
        
        Returns:
            Tuple of (is_authorized, denial_reason)
        """
        # Check if application exists and is active
        app = db.query(Application).filter(
            and_(
                Application.app_name == app_name,
                Application.is_active == True
            )
        ).first()
        
        if not app:
            return False, f"Application '{app_name}' not found or inactive"
        
        # Check if user exists and is active
        user = db.query(AuthorizedUser).filter(
            and_(
                AuthorizedUser.email == email.lower(),
                AuthorizedUser.is_active == True
            )
        ).first()
        
        if not user:
            return False, "User not authorized"
        
        # Check if user has permission for this app
        permission = db.query(UserAppPermission).filter(
            and_(
                UserAppPermission.user_id == user.id,
                UserAppPermission.app_id == app.id,
                UserAppPermission.is_active == True
            )
        ).first()
        
        if not permission:
            return False, f"User not authorized for application '{app_name}'"
        
        # Check if permission has expired
        if permission.expires_at and permission.expires_at < datetime.utcnow():
            return False, "Authorization expired"
        
        # All checks passed
        return True, None
    
    def _log_access(self, 
                   db: Session, 
                   email: str, 
                   app_name: str, 
                   access_granted: bool,
                   denial_reason: Optional[str],
                   ip_address: Optional[str],
                   user_agent: Optional[str]):
        """Log access attempt to database"""
        try:
            # Get app_id if possible
            app = db.query(Application).filter(Application.app_name == app_name).first()
            app_id = app.id if app else None
            
            log_entry = AccessLog(
                email=email.lower(),
                app_id=app_id,
                app_name=app_name,
                access_granted=access_granted,
                denial_reason=denial_reason,
                ip_address=ip_address,
                user_agent=user_agent[:500] if user_agent else None  # Limit length
            )
            
            db.add(log_entry)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log access attempt: {e}")
            db.rollback()
    
    def verify_api_key(self, db: Session, api_key: str, ip_address: Optional[str] = None) -> bool:
        """
        Verify an API key for service-to-service authentication
        
        Args:
            db: Database session
            api_key: The API key to verify
            ip_address: Client IP address (optional)
            
        Returns:
            True if valid, False otherwise
        """
        # Hash the API key
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        # Look up the key
        api_key_record = db.query(ApiKey).filter(
            and_(
                ApiKey.key_hash == key_hash,
                ApiKey.is_active == True
            )
        ).first()
        
        if not api_key_record:
            logger.warning(f"Invalid API key attempt from {ip_address}")
            return False
        
        # Check expiration
        if api_key_record.expires_at and api_key_record.expires_at < datetime.utcnow():
            logger.warning(f"Expired API key used: {api_key_record.name}")
            return False
        
        # Check IP restrictions if configured
        if api_key_record.allowed_ips and ip_address:
            allowed = self._check_ip_allowed(ip_address, json.loads(api_key_record.allowed_ips))
            if not allowed:
                logger.warning(f"API key {api_key_record.name} used from unauthorized IP: {ip_address}")
                return False
        
        # Update last used timestamp
        api_key_record.last_used_at = datetime.utcnow()
        db.commit()
        
        return True
    
    def _check_ip_allowed(self, ip_address: str, allowed_list: List[str]) -> bool:
        """Check if an IP address is in the allowed list (supports CIDR notation)"""
        try:
            client_ip = ipaddress.ip_address(ip_address)
            
            for allowed in allowed_list:
                try:
                    # Check if it's a network range
                    if '/' in allowed:
                        network = ipaddress.ip_network(allowed, strict=False)
                        if client_ip in network:
                            return True
                    else:
                        # Single IP address
                        if client_ip == ipaddress.ip_address(allowed):
                            return True
                except ValueError:
                    logger.error(f"Invalid IP/network in allowed list: {allowed}")
                    
            return False
            
        except ValueError:
            logger.error(f"Invalid client IP address: {ip_address}")
            return False
    
    def get_user_applications(self, db: Session, email: str) -> List[Dict[str, Any]]:
        """
        Get list of applications a user has access to
        
        Args:
            db: Database session
            email: User's email address
            
        Returns:
            List of application details
        """
        user = db.query(AuthorizedUser).filter(
            and_(
                AuthorizedUser.email == email.lower(),
                AuthorizedUser.is_active == True
            )
        ).first()
        
        if not user:
            return []
        
        # Get all active permissions for the user
        permissions = db.query(UserAppPermission).join(Application).filter(
            and_(
                UserAppPermission.user_id == user.id,
                UserAppPermission.is_active == True,
                Application.is_active == True,
                or_(
                    UserAppPermission.expires_at == None,
                    UserAppPermission.expires_at > datetime.utcnow()
                )
            )
        ).all()
        
        apps = []
        for perm in permissions:
            apps.append({
                'app_name': perm.application.app_name,
                'display_name': perm.application.display_name,
                'description': perm.application.description,
                'granted_at': perm.granted_at.isoformat(),
                'expires_at': perm.expires_at.isoformat() if perm.expires_at else None
            })
        
        return apps
    
    def clear_cache(self, email: Optional[str] = None, app_name: Optional[str] = None):
        """Clear authorization cache entries"""
        if not config.ENABLE_CACHING:
            return
        
        if email and app_name:
            # Clear specific entry
            cache_key = f"{email}:{app_name}"
            self.auth_cache.pop(cache_key, None)
            self.negative_cache.pop(cache_key, None)
        elif email:
            # Clear all entries for a user
            keys_to_remove = [k for k in self.auth_cache.keys() if k.startswith(f"{email}:")]
            for key in keys_to_remove:
                self.auth_cache.pop(key, None)
                self.negative_cache.pop(key, None)
        else:
            # Clear all caches
            if self.auth_cache:
                self.auth_cache.clear()
            if self.negative_cache:
                self.negative_cache.clear()
    
    def log_admin_action(self, 
                        db: Session,
                        admin_email: str,
                        action: str,
                        target_email: Optional[str] = None,
                        target_app: Optional[str] = None,
                        details: Optional[Dict[str, Any]] = None,
                        ip_address: Optional[str] = None):
        """Log an administrative action for audit purposes"""
        if not config.ENABLE_AUDIT_LOG:
            return
        
        try:
            audit_entry = AuditLog(
                admin_email=admin_email.lower(),
                action=action,
                target_email=target_email.lower() if target_email else None,
                target_app=target_app,
                details=json.dumps(details) if details else None,
                ip_address=ip_address
            )
            
            db.add(audit_entry)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to log admin action: {e}")
            db.rollback()