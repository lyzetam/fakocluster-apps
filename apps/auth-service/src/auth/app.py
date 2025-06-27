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

from database_models import Base, get_db_session
from api import router
from admin_api import admin_router
from healthcheck import start_health_server
import config
from externalconnections.fetch_secrets import get_postgres_credentials, build_postgres_connection_string

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