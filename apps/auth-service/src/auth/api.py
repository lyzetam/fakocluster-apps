"""API endpoints for Auth Service"""
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, text
from typing import Optional, List
from pydantic import BaseModel, EmailStr
from datetime import datetime, timedelta
import logging

import database_models
from database_models import AuthorizedUser, Application, AccessLog
from auth_manager import AuthorizationManager
from password_utils import verify_password
import config

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix=config.API_PREFIX)

# Initialize auth manager
auth_manager = AuthorizationManager()

# Pydantic models for requests/responses
class AuthCheckRequest(BaseModel):
    email: EmailStr
    app_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    authenticated: bool
    is_admin: Optional[bool] = None
    
class AuthCheckResponse(BaseModel):
    authorized: bool
    denial_reason: Optional[str] = None
    
class UserAppsResponse(BaseModel):
    email: str
    applications: List[dict]
    
class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    database: str
    cache_enabled: bool

# Dependency for API key authentication
async def verify_api_key(
    x_api_key: str = Header(None, alias=config.API_KEY_HEADER),
    req: Request = None,
):
    """Verify API key for protected endpoints."""
    if not config.ENABLE_API_KEY_AUTH:
        return True

    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    # Get DB session
    db_gen = database_models.get_db_session()
    db = next(db_gen)
    try:
        client_ip = req.client.host if req and req.client else None
        if not auth_manager.verify_api_key(db, x_api_key, ip_address=client_ip):
            raise HTTPException(status_code=401, detail="Invalid API key")
    finally:
        db.close()
        db_gen.close()

    return True

# Public endpoints (used by applications to check authorization)
@router.post("/auth/check", response_model=AuthCheckResponse)
async def check_authorization(
    request: AuthCheckRequest,
    req: Request,
    api_key_valid: bool = Depends(verify_api_key),
    db: Session = Depends(database_models.get_db_session)
):
    """
    Check if a user is authorized to access an application
    
    This is the main endpoint used during SSO flows.
    """
    # Get client IP
    client_ip = req.client.host if req.client else None
    user_agent = req.headers.get("user-agent")
    
    # Perform authorization check
    is_authorized, denial_reason = auth_manager.check_authorization(
        db=db,
        email=request.email,
        app_name=request.app_name,
        ip_address=client_ip,
        user_agent=user_agent
    )
    
    return AuthCheckResponse(
        authorized=is_authorized,
        denial_reason=denial_reason
    )


@router.post("/auth/login", response_model=LoginResponse)
async def login_user(
    request: LoginRequest,
    api_key_valid: bool = Depends(verify_api_key),
    db: Session = Depends(database_models.get_db_session),
):
    """Validate user credentials."""
    user = db.query(AuthorizedUser).filter(
        and_(AuthorizedUser.email == request.email.lower(), AuthorizedUser.is_active == True)
    ).first()

    if not user or not user.password_hash:
        return LoginResponse(authenticated=False)

    if not verify_password(request.password, user.password_hash):
        return LoginResponse(authenticated=False)

    return LoginResponse(authenticated=True, is_admin=user.is_admin)

@router.get("/users/{email}/applications", response_model=UserAppsResponse)
async def get_user_applications(
    email: EmailStr,
    api_key_valid: bool = Depends(verify_api_key),
    db: Session = Depends(database_models.get_db_session)
):
    """Get list of applications a user has access to"""
    apps = auth_manager.get_user_applications(db, email)
    
    return UserAppsResponse(
        email=email,
        applications=apps
    )

@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(database_models.get_db_session)):
    """Health check endpoint"""
    try:
        # Test database connection
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "unhealthy"
    
    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        timestamp=datetime.utcnow(),
        database=db_status,
        cache_enabled=config.ENABLE_CACHING
    )

# Cache management endpoints (for admin use)
@router.post("/cache/clear")
async def clear_cache(
    email: Optional[EmailStr] = None,
    app_name: Optional[str] = None,
    api_key_valid: bool = Depends(verify_api_key)
):
    """Clear authorization cache"""
    auth_manager.clear_cache(email=email, app_name=app_name)
    
    return {
        "status": "success",
        "message": "Cache cleared",
        "email": email,
        "app_name": app_name
    }

# Metrics endpoint (Prometheus format)
@router.get("/metrics", response_class=PlainTextResponse)
async def get_metrics(db: Session = Depends(database_models.get_db_session)):
    """Export metrics in Prometheus format"""
    metrics = []
    
    # Add basic metrics
    metrics.append("# HELP auth_service_up Auth service status")
    metrics.append("# TYPE auth_service_up gauge")
    metrics.append("auth_service_up 1")
    
    # Get some statistics
    try:
        # Total users
        total_users = db.query(AuthorizedUser).filter(AuthorizedUser.is_active == True).count()
        metrics.append(f"# HELP auth_service_total_users Total active users")
        metrics.append(f"# TYPE auth_service_total_users gauge")
        metrics.append(f"auth_service_total_users {total_users}")
        
        # Total apps
        total_apps = db.query(Application).filter(Application.is_active == True).count()
        metrics.append(f"# HELP auth_service_total_apps Total active applications")
        metrics.append(f"# TYPE auth_service_total_apps gauge")
        metrics.append(f"auth_service_total_apps {total_apps}")
        
        # Recent access attempts (last hour)
        recent_granted = db.query(AccessLog).filter(
            and_(
                AccessLog.access_time >= datetime.utcnow() - timedelta(hours=1),
                AccessLog.access_granted == True
            )
        ).count()
        
        recent_denied = db.query(AccessLog).filter(
            and_(
                AccessLog.access_time >= datetime.utcnow() - timedelta(hours=1),
                AccessLog.access_granted == False
            )
        ).count()
        
        metrics.append(f"# HELP auth_service_access_granted_1h Access granted in last hour")
        metrics.append(f"# TYPE auth_service_access_granted_1h counter")
        metrics.append(f"auth_service_access_granted_1h {recent_granted}")
        
        metrics.append(f"# HELP auth_service_access_denied_1h Access denied in last hour")
        metrics.append(f"# TYPE auth_service_access_denied_1h counter")
        metrics.append(f"auth_service_access_denied_1h {recent_denied}")
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
    
    return "\n".join(metrics) + "\n"