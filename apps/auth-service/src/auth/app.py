"""Main FastAPI application for Auth Service"""
import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uvicorn

from database_models import Base, get_db_session, ApiKey
from api import router
from admin_api import admin_router
from healthcheck import start_health_server
import config
from externalconnections.fetch_secrets import (
    get_postgres_credentials,
    build_postgres_connection_string,
    get_api_key_config,
    get_super_user,
)
import hashlib

# Configure logging
if config.LOG_FORMAT == 'json':
    import json
    
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_obj = {
                'timestamp': self.formatTime(record),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            if hasattr(record, 'extra'):
                log_obj.update(record.extra)
            return json.dumps(log_obj)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logging.root.handlers = [handler]
else:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

logger = logging.getLogger(__name__)

# Database setup
def setup_database():
    """Setup database connection"""
    try:
        # Get database credentials
        if config.DATABASE_HOST and config.DATABASE_NAME:
            # Use environment variables if provided
            connection_string = f"postgresql://{config.DATABASE_USER}:{config.DATABASE_PASSWORD}@{config.DATABASE_HOST}:{config.DATABASE_PORT}/{config.DATABASE_NAME}"
        else:
            # Get from AWS Secrets Manager
            postgres_secrets = get_postgres_credentials(
                secret_name=config.POSTGRES_SECRETS_NAME,
                region_name=config.AWS_REGION
            )
            connection_string = build_postgres_connection_string(postgres_secrets)
        
        # Create engine
        engine = create_engine(
            connection_string,
            pool_size=config.CONNECTION_POOL_SIZE,
            max_overflow=config.CONNECTION_POOL_OVERFLOW,
            pool_pre_ping=True,
            echo=False
        )
        
        # Create session factory
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Update the get_db_session function
        def get_db():
            db = SessionLocal()
            try:
                yield db
            finally:
                db.close()
        
        # Replace the placeholder
        import database_models
        database_models.get_db_session = get_db
        
        # Test connection
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        
        logger.info("Database connection established")

        # Load API keys from secrets and ensure they exist in the database
        try:
            api_config = get_api_key_config(
                secret_name=config.API_SECRETS_NAME,
                region_name=config.AWS_REGION,
            )
            session = SessionLocal()

            def upsert_key(raw_key: str, meta: dict, is_admin: bool):
                key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
                record = session.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()
                if record:
                    record.name = meta.get("name", record.name)
                    record.description = meta.get("description", record.description)
                    record.created_by = meta.get("email", record.created_by)
                    record.is_admin = is_admin
                    record.is_active = True
                else:
                    session.add(
                        ApiKey(
                            key_hash=key_hash,
                            name=meta.get("name", "API Key"),
                            description=meta.get("description"),
                            created_by=meta.get("email", config.DEFAULT_ADMIN_EMAIL),
                            is_admin=is_admin,
                            is_active=True,
                        )
                    )

            # Master key (non-admin)
            master_key = api_config.get("master_api_key")
            if master_key:
                upsert_key(master_key, {"name": "Master API Key"}, False)

            # Admin keys
            for key, meta in api_config.get("admin_api_keys", {}).items():
                upsert_key(key, meta or {}, meta.get("is_admin", True))

            session.commit()
            logger.info("API keys synchronized")

            # Create or update super user
            try:
                from password_utils import hash_password
                from externalconnections.fetch_secrets import get_super_user

                super_cfg = get_super_user(
                    secret_name=config.SUPERUSER_SECRETS_NAME,
                    region_name=config.AWS_REGION,
                )
                email = (super_cfg.get("email") or config.DEFAULT_ADMIN_EMAIL).lower()
                password = super_cfg.get("password")
                full_name = super_cfg.get("full_name")

                if not password:
                    raise ValueError("Super user password not provided")

                user = session.query(AuthorizedUser).filter(AuthorizedUser.email == email).first()
                pwd_hash = hash_password(password, iterations=config.PASSWORD_HASH_ITERATIONS)
                if user:
                    user.password_hash = pwd_hash
                    user.full_name = full_name or user.full_name
                    user.is_admin = True
                    user.is_active = True
                else:
                    session.add(
                        AuthorizedUser(
                            email=email,
                            full_name=full_name,
                            password_hash=pwd_hash,
                            is_admin=True,
                            created_by=email,
                        )
                    )
                session.commit()
                logger.info("Super user synchronized")
            except Exception as exc:
                logger.error(f"Failed to create super user: {exc}")
        except Exception as exc:
            logger.error(f"Failed to load API keys: {exc}")
            if 'session' in locals():
                session.rollback()
        finally:
            if 'session' in locals():
                session.close()

        return engine
        
    except Exception as e:
        logger.error(f"Failed to setup database: {e}")
        raise

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info("Starting Auth Service")
    
    # Setup database
    engine = setup_database()
    
    # Start health check server
    health_server = start_health_server(port=config.HEALTH_CHECK_PORT)
    logger.info(f"Health check server started on port {config.HEALTH_CHECK_PORT}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Auth Service")
    engine.dispose()

# Create FastAPI app
app = FastAPI(
    title="Auth Service",
    description="Authorization service for SSO authentication",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
if config.CORS_ENABLED:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add rate limiting middleware
if config.ENABLE_RATE_LIMITING:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        # Apply rate limiting
        try:
            return await limiter.limit(f"{config.RATE_LIMIT_PER_MINUTE}/minute")(call_next)(request)
        except RateLimitExceeded:
            return PlainTextResponse("Rate limit exceeded", status_code=429)

# Include routers
app.include_router(router)
app.include_router(admin_router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Auth Service",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "api": config.API_PREFIX,
            "admin": f"{config.API_PREFIX}/admin",
            "metrics": "/metrics"
        }
    }

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return PlainTextResponse(
        status_code=500,
        content="Internal server error"
    )

def main():
    """Main entry point"""
    uvicorn.run(
        "app:app",
        host=config.API_HOST,
        port=config.API_PORT,
        workers=config.MAX_WORKERS,
        log_config=None  # We handle logging ourselves
    )

if __name__ == "__main__":
    main()