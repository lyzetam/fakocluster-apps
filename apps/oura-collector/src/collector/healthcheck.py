"""Health check endpoint for Oura collector"""
import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class HealthStatus:
    """Singleton to track collector health status"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.last_collection = None
            cls._instance.last_error = None
            cls._instance.total_collections = 0
            cls._instance.failed_collections = 0
            cls._instance.is_running = True
        return cls._instance
    
    def update_collection(self, success: bool, error: str = None):
        """Update collection status"""
        self.last_collection = datetime.now()
        self.total_collections += 1
        if not success:
            self.failed_collections += 1
            self.last_error = error
    
    def get_status(self) -> dict:
        """Get current health status"""
        status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'is_running': self.is_running,
            'total_collections': self.total_collections,
            'failed_collections': self.failed_collections
        }
        
        if self.last_collection:
            status['last_collection'] = self.last_collection.isoformat()
            status['minutes_since_last_collection'] = (
                datetime.now() - self.last_collection
            ).total_seconds() / 60
            
            # Mark unhealthy if no collection in 2 hours
            if status['minutes_since_last_collection'] > 120:
                status['status'] = 'unhealthy'
                status['reason'] = 'No collection in over 2 hours'
        
        if self.last_error:
            status['last_error'] = self.last_error
        
        # Mark unhealthy if too many failures
        if self.failed_collections > 5:
            status['status'] = 'unhealthy'
            status['reason'] = f'Too many failed collections: {self.failed_collections}'
        
        return status

class HealthCheckHandler(BaseHTTPRequestHandler):
    """HTTP handler for health checks"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == '/health':
            self._handle_health()
        elif self.path == '/ready':
            self._handle_ready()
        else:
            self.send_response(404)
            self.end_headers()
    
    def _handle_health(self):
        """Handle /health endpoint"""
        health = HealthStatus()
        status = health.get_status()
        
        # Send response
        response_code = 200 if status['status'] == 'healthy' else 503
        self.send_response(response_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def _handle_ready(self):
        """Handle /ready endpoint"""
        health = HealthStatus()
        if health.is_running and health.total_collections > 0:
            self.send_response(200)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Ready')
        else:
            self.send_response(503)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Not Ready')
    
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