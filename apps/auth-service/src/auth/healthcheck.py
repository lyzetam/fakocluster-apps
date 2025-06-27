"""Health check endpoint for Auth Service"""
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HealthStatus:
    """Singleton to track service health status"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.is_healthy = True
            cls._instance.last_check = datetime.now()
            cls._instance.database_healthy = True
            cls._instance.cache_healthy = True
            cls._instance.total_requests = 0
            cls._instance.failed_requests = 0
        return cls._instance
    
    def update_health(self, database_healthy: bool, cache_healthy: bool):
        """Update health status"""
        self.last_check = datetime.now()
        self.database_healthy = database_healthy
        self.cache_healthy = cache_healthy
        self.is_healthy = database_healthy  # Database is critical
    
    def increment_requests(self, failed: bool = False):
        """Increment request counters"""
        self.total_requests += 1
        if failed:
            self.failed_requests += 1
    
    def get_status(self) -> dict:
        """Get current health status"""
        status = {
            'status': 'healthy' if self.is_healthy else 'unhealthy',
            'timestamp': datetime.now().isoformat(),
            'checks': {
                'database': 'healthy' if self.database_healthy else 'unhealthy',
                'cache': 'healthy' if self.cache_healthy else 'unhealthy'
            },
            'last_check': self.last_check.isoformat(),
            'metrics': {
                'total_requests': self.total_requests,
                'failed_requests': self.failed_requests,
                'error_rate': self.failed_requests / self.total_requests if self.total_requests > 0 else 0
            }
        }
        
        # Determine overall status
        if not self.database_healthy:
            status['status'] = 'unhealthy'
            status['reason'] = 'Database connection failed'
        elif self.failed_requests > 10 and status['metrics']['error_rate'] > 0.5:
            status['status'] = 'degraded'
            status['reason'] = 'High error rate'
        
        return status

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/ready':
            self._handle_ready()
        elif self.path == '/live':
            self._handle_liveness()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_health(self):
        """Handle /health endpoint - detailed health status"""
        health = HealthStatus()
        status = health.get_status()
        
        # Send response
        response_code = 200 if status['status'] == 'healthy' else 503
        self.send_response(response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def _handle_ready(self):
        """Handle /ready endpoint - readiness probe"""
        health = HealthStatus()
        
        # Service is ready if database is healthy
        if health.database_healthy:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Ready')
        else:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Ready')
    
    def _handle_liveness(self):
        """Handle /live endpoint - liveness probe"""
        # Always return 200 unless the process is completely broken
        self.send_response(200)
        self.send_header('Content-Type', 'text/plain')
        self.end_headers()
        self.wfile.write(b'Alive')
    
    def log_message(self, format, *args):
        """Suppress request logging"""
        pass

def start_health_server(port: int = 8080):
    """Start the health check HTTP server"""
    def run_server():
        server = HTTPServer(('0.0.0.0', port), HealthCheckHandler)
        logger.info(f"Health check server started on port {port}")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread