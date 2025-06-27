"""Admin API endpoints for Auth Service"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import hashlib
import secrets
import json

from database_models import (
    get_db_session, AuthorizedUser, Application, 
    UserAppPermission, ApiKey, AccessLog, AuditLog
)
from auth_manager import AuthorizationManager
import config

# Create admin router
admin_router = APIRouter(prefix=f"{config.API_PREFIX}/admin")

# Initialize auth manager
auth_manager = AuthorizationManager()

# Pydantic models
class CreateUserRequest(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_admin: bool = False
    notes: Optional[str] = None
    
class UpdateUserRequest(BaseModel):
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    notes: Optional[str] = None
    
class CreateApplicationRequest(BaseModel):
    app_name: str
    display_name: str
    description: Optional[str] = None
    callback_urls: Optional[List[str]] = None
    
class GrantPermissionRequest(BaseModel):
    user_email: EmailStr
    app_name: str
    expires_at: Optional[datetime] = None
    notes: Optional[str] = None
    
class CreateApiKeyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    allowed_ips: Optional[List[str]] = None
    
class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    is_admin: bool
    created_at: datetime
    created_by: str
    permissions_count: int
    
class ApplicationResponse(BaseModel):
    id: int
    app_name: str
    display_name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    users_count: int

# Admin authentication dependency
async def verify_admin(
    x_api_key: str = Header(None, alias=config.API_KEY_HEADER),
    req: Request | None = None,
    db: Session = Depends(get_db_session)
):
    """Verify that the request is from an admin user"""
    if not config.ENABLE_API_KEY_AUTH:
        return {"email": config.DEFAULT_ADMIN_EMAIL, "ip_address": None}
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # For admin endpoints, we'll check if the API key has admin privileges
    # This would be stored in the API key metadata
    client_ip = req.client.host if req and req.client else None
    if not auth_manager.verify_api_key(db, x_api_key, ip_address=client_ip):
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Get admin email from API key (simplified for this example)
    # In production, you'd look this up from the API key record
    admin_email = config.DEFAULT_ADMIN_EMAIL

    return {"email": admin_email, "ip_address": client_ip}

# User management endpoints
@admin_router.post("/users", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Create a new authorized user"""
    # Check if user already exists
    existing = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == request.email.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    # Create user
    user = AuthorizedUser(
        email=request.email.lower(),
        full_name=request.full_name,
        is_admin=request.is_admin,
        created_by=admin_info["email"],
        notes=request.notes
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "create_user",
        target_email=request.email,
        details={"is_admin": request.is_admin},
        ip_address=admin_info["ip_address"]
    )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        created_by=user.created_by,
        permissions_count=0
    )

@admin_router.get("/users", response_model=List[UserResponse])
async def list_users(
    is_active: Optional[bool] = None,
    is_admin: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """List authorized users"""
    query = db.query(AuthorizedUser)
    
    if is_active is not None:
        query = query.filter(AuthorizedUser.is_active == is_active)
    
    if is_admin is not None:
        query = query.filter(AuthorizedUser.is_admin == is_admin)
    
    users = query.offset(skip).limit(limit).all()
    
    results = []
    for user in users:
        permissions_count = db.query(UserAppPermission).filter(
            and_(
                UserAppPermission.user_id == user.id,
                UserAppPermission.is_active == True
            )
        ).count()
        
        results.append(UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            created_by=user.created_by,
            permissions_count=permissions_count
        ))
    
    return results

@admin_router.patch("/users/{email}")
async def update_user(
    email: EmailStr,
    request: UpdateUserRequest,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Update user details"""
    user = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == email.lower()
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    
    # Clear cache for this user
    auth_manager.clear_cache(email=email)
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "update_user",
        target_email=email,
        details=update_data,
        ip_address=admin_info["ip_address"]
    )
    
    return {"status": "success", "message": "User updated"}

# Application management endpoints
@admin_router.post("/applications", response_model=ApplicationResponse)
async def create_application(
    request: CreateApplicationRequest,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Create a new application"""
    # Check if app already exists
    existing = db.query(Application).filter(
        Application.app_name == request.app_name
    ).first()
    
    if existing:
        raise HTTPException(status_code=409, detail="Application already exists")
    
    # Create application
    app = Application(
        app_name=request.app_name,
        display_name=request.display_name,
        description=request.description,
        callback_urls=json.dumps(request.callback_urls) if request.callback_urls else None
    )
    
    db.add(app)
    db.commit()
    db.refresh(app)
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "create_application",
        target_app=request.app_name,
        ip_address=admin_info["ip_address"]
    )
    
    return ApplicationResponse(
        id=app.id,
        app_name=app.app_name,
        display_name=app.display_name,
        description=app.description,
        is_active=app.is_active,
        created_at=app.created_at,
        users_count=0
    )

@admin_router.get("/applications", response_model=List[ApplicationResponse])
async def list_applications(
    is_active: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """List applications"""
    query = db.query(Application)
    
    if is_active is not None:
        query = query.filter(Application.is_active == is_active)
    
    apps = query.offset(skip).limit(limit).all()
    
    results = []
    for app in apps:
        users_count = db.query(UserAppPermission).filter(
            and_(
                UserAppPermission.app_id == app.id,
                UserAppPermission.is_active == True
            )
        ).count()
        
        results.append(ApplicationResponse(
            id=app.id,
            app_name=app.app_name,
            display_name=app.display_name,
            description=app.description,
            is_active=app.is_active,
            created_at=app.created_at,
            users_count=users_count
        ))
    
    return results

# Permission management endpoints
@admin_router.post("/permissions/grant")
async def grant_permission(
    request: GrantPermissionRequest,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Grant user permission to access an application"""
    # Get user
    user = db.query(AuthorizedUser).filter(
        and_(
            AuthorizedUser.email == request.user_email.lower(),
            AuthorizedUser.is_active == True
        )
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found or inactive")
    
    # Get application
    app = db.query(Application).filter(
        and_(
            Application.app_name == request.app_name,
            Application.is_active == True
        )
    ).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found or inactive")
    
    # Get admin user (for granted_by)
    admin_user = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == admin_info["email"]
    ).first()
    
    # Check if permission already exists
    existing = db.query(UserAppPermission).filter(
        and_(
            UserAppPermission.user_id == user.id,
            UserAppPermission.app_id == app.id
        )
    ).first()
    
    if existing:
        # Update existing permission
        existing.is_active = True
        existing.granted_at = datetime.utcnow()
        existing.granted_by_user_id = admin_user.id if admin_user else 1
        existing.expires_at = request.expires_at
        existing.notes = request.notes
    else:
        # Create new permission
        permission = UserAppPermission(
            user_id=user.id,
            app_id=app.id,
            granted_by_user_id=admin_user.id if admin_user else 1,
            expires_at=request.expires_at,
            notes=request.notes
        )
        db.add(permission)
    
    db.commit()
    
    # Clear cache
    auth_manager.clear_cache(email=request.user_email, app_name=request.app_name)
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "grant_permission",
        target_email=request.user_email,
        target_app=request.app_name,
        details={"expires_at": request.expires_at.isoformat() if request.expires_at else None},
        ip_address=admin_info["ip_address"]
    )
    
    return {"status": "success", "message": "Permission granted"}

@admin_router.post("/permissions/revoke")
async def revoke_permission(
    user_email: EmailStr,
    app_name: str,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Revoke user permission for an application"""
    # Get user and app
    user = db.query(AuthorizedUser).filter(
        AuthorizedUser.email == user_email.lower()
    ).first()
    
    app = db.query(Application).filter(
        Application.app_name == app_name
    ).first()
    
    if not user or not app:
        raise HTTPException(status_code=404, detail="User or application not found")
    
    # Find and deactivate permission
    permission = db.query(UserAppPermission).filter(
        and_(
            UserAppPermission.user_id == user.id,
            UserAppPermission.app_id == app.id
        )
    ).first()
    
    if permission:
        permission.is_active = False
        db.commit()
    
    # Clear cache
    auth_manager.clear_cache(email=user_email, app_name=app_name)
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "revoke_permission",
        target_email=user_email,
        target_app=app_name,
        ip_address=admin_info["ip_address"]
    )
    
    return {"status": "success", "message": "Permission revoked"}

# API key management
@admin_router.post("/api-keys")
async def create_api_key(
    request: CreateApiKeyRequest,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Create a new API key"""
    # Generate a secure random key
    api_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Create API key record
    api_key_record = ApiKey(
        key_hash=key_hash,
        name=request.name,
        description=request.description,
        created_by=admin_info["email"],
        expires_at=request.expires_at,
        allowed_ips=json.dumps(request.allowed_ips) if request.allowed_ips else None
    )
    
    db.add(api_key_record)
    db.commit()
    
    # Log admin action
    auth_manager.log_admin_action(
        db, admin_info["email"], "create_api_key",
        details={"key_name": request.name},
        ip_address=admin_info["ip_address"]
    )
    
    return {
        "status": "success",
        "api_key": api_key,
        "name": request.name,
        "message": "Save this API key securely. It will not be shown again."
    }

# Access logs and audit logs
@admin_router.get("/logs/access")
async def get_access_logs(
    email: Optional[EmailStr] = None,
    app_name: Optional[str] = None,
    access_granted: Optional[bool] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Get access logs"""
    query = db.query(AccessLog)
    
    if email:
        query = query.filter(AccessLog.email == email.lower())
    
    if app_name:
        query = query.filter(AccessLog.app_name == app_name)
    
    if access_granted is not None:
        query = query.filter(AccessLog.access_granted == access_granted)
    
    if start_time:
        query = query.filter(AccessLog.access_time >= start_time)
    
    if end_time:
        query = query.filter(AccessLog.access_time <= end_time)
    
    total = query.count()
    logs = query.order_by(AccessLog.access_time.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "logs": [
            {
                "email": log.email,
                "app_name": log.app_name,
                "access_time": log.access_time,
                "access_granted": log.access_granted,
                "denial_reason": log.denial_reason,
                "ip_address": log.ip_address
            }
            for log in logs
        ]
    }

@admin_router.get("/logs/audit")
async def get_audit_logs(
    admin_email: Optional[EmailStr] = None,
    action: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    skip: int = 0,
    limit: int = 100,
    admin_info: dict = Depends(verify_admin),
    db: Session = Depends(get_db_session)
):
    """Get audit logs"""
    query = db.query(AuditLog)
    
    if admin_email:
        query = query.filter(AuditLog.admin_email == admin_email.lower())
    
    if action:
        query = query.filter(AuditLog.action == action)
    
    if start_time:
        query = query.filter(AuditLog.action_time >= start_time)
    
    if end_time:
        query = query.filter(AuditLog.action_time <= end_time)
    
    total = query.count()
    logs = query.order_by(AuditLog.action_time.desc()).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "logs": [
            {
                "admin_email": log.admin_email,
                "action": log.action,
                "target_email": log.target_email,
                "target_app": log.target_app,
                "action_time": log.action_time,
                "details": json.loads(log.details) if log.details else None,
                "ip_address": log.ip_address
            }
            for log in logs
        ]
    }