import os
import time
import threading
from datetime import datetime, timedelta
from flask import Flask, jsonify, render_template, request
from kubernetes import client, config
import socket
import requests
from collections import deque, defaultdict
import json

# Configuration with validation
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '30'))
FLASK_PORT = int(os.getenv('FLASK_PORT', '8080'))
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://prometheus.monitoring.svc.cluster.local:9090')

# Security: Validate refresh interval
if REFRESH_INTERVAL < 10:
    REFRESH_INTERVAL = 10  # Minimum 10 seconds to prevent DoS
elif REFRESH_INTERVAL > 3600:
    REFRESH_INTERVAL = 3600  # Maximum 1 hour

# Flask app
app = Flask(__name__, template_folder='../ui/templates', static_folder='../ui/static')

# Metrics storage with history
metrics_history = defaultdict(lambda: deque(maxlen=100))
metrics_data = {
    'timestamp': None,
    'pods': {},
    'response_times': {},
    'resource_usage': {},
    'prometheus_metrics': {},
    'errors': [],
    'recommendations': [],
    'alerts': []
}

# Initialize Kubernetes
def init_k8s():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api()

v1, apps_v1 = init_k8s()

# Prometheus queries with security
def query_prometheus(query):
    try:
        # Security: Limit query length
        if len(query) > 1000:
            metrics_data['errors'].append("Query too long")
            return []
        
        resp = requests.get(f"{PROMETHEUS_URL}/api/v1/query", 
                          params={'query': query}, timeout=5)
        if resp.status_code == 200:
            return resp.json()['data']['result']
    except requests.exceptions.Timeout:
        metrics_data['errors'].append("Prometheus query timeout")
    except Exception as e:
        metrics_data['errors'].append(f"Prometheus error: {str(e)[:100]}")  # Limit error message length
    return []

def get_prometheus_metrics():
    metrics = {}
    
    # CPU usage by pod
    cpu_query = 'rate(container_cpu_usage_seconds_total{namespace=~"whisper|piper|openwakeword|homebot"}[5m])'
    cpu_data = query_prometheus(cpu_query)
    for item in cpu_data:
        pod = item['metric'].get('pod', '')
        if pod:
            metrics[f"cpu_{pod}"] = float(item['value'][1])
    
    # Memory usage
    mem_query = 'container_memory_working_set_bytes{namespace=~"whisper|piper|openwakeword|homebot"}'
    mem_data = query_prometheus(mem_query)
    for item in mem_data:
        pod = item['metric'].get('pod', '')
        if pod:
            metrics[f"memory_{pod}"] = float(item['value'][1]) / (1024**3)  # GB
    
    # Request rate - for voice services
    for service in ['whisper', 'piper', 'openwakeword']:
        # Try different metric names that might be exposed
        for metric_name in ['http_requests_total', 'requests_total', f'{service}_requests_total']:
            req_query = f'rate({metric_name}{{namespace="{service}"}}[5m])'
            req_data = query_prometheus(req_query)
            if req_data:
                metrics[f"requests_{service}"] = float(req_data[0]['value'][1])
                break
    
    # Latency percentiles
    for service in ['whisper', 'piper', 'openwakeword']:
        # Try different histogram names
        for metric_name in ['http_request_duration_seconds', 'request_duration_seconds', f'{service}_duration_seconds']:
            p99_query = f'histogram_quantile(0.99, rate({metric_name}_bucket{{namespace="{service}"}}[5m]))'
            p99_data = query_prometheus(p99_query)
            if p99_data:
                metrics[f"p99_{service}"] = float(p99_data[0]['value'][1])
                break
    
    # Voice pipeline specific metrics if available
    # Whisper transcription time
    whisper_time_query = 'rate(whisper_transcription_duration_seconds_sum[5m]) / rate(whisper_transcription_duration_seconds_count[5m])'
    whisper_time_data = query_prometheus(whisper_time_query)
    if whisper_time_data:
        metrics['whisper_avg_transcription_time'] = float(whisper_time_data[0]['value'][1])
    
    # Piper synthesis time
    piper_time_query = 'rate(piper_synthesis_duration_seconds_sum[5m]) / rate(piper_synthesis_duration_seconds_count[5m])'
    piper_time_data = query_prometheus(piper_time_query)
    if piper_time_data:
        metrics['piper_avg_synthesis_time'] = float(piper_time_data[0]['value'][1])
    
    # Wake word detections
    wake_word_query = 'increase(openwakeword_detections_total[5m])'
    wake_word_data = query_prometheus(wake_word_query)
    if wake_word_data:
        metrics['wake_word_detections'] = float(wake_word_data[0]['value'][1])
    
    return metrics

# Enhanced pod metrics
def get_pod_metrics():
    pods_info = {}
    namespaces = ['whisper', 'piper', 'openwakeword', 'homebot']
    
    for ns in namespaces:
        try:
            pods = v1.list_namespaced_pod(namespace=ns)
            for pod in pods.items:
                key = f"{ns}/{pod.metadata.name}"
                
                # Get pod events
                events = v1.list_namespaced_event(
                    namespace=ns,
                    field_selector=f"involvedObject.name={pod.metadata.name}"
                )
                recent_events = [e for e in events.items 
                               if e.last_timestamp and 
                               (datetime.utcnow() - e.last_timestamp.replace(tzinfo=None)) < timedelta(hours=1)]
                
                pods_info[key] = {
                    'namespace': ns,
                    'name': pod.metadata.name,
                    'status': pod.status.phase,
                    'node': pod.spec.node_name,
                    'ready': all(c.ready for c in pod.status.container_statuses or []),
                    'restarts': sum(c.restart_count for c in pod.status.container_statuses or []),
                    'age': str(datetime.utcnow() - pod.metadata.creation_timestamp.replace(tzinfo=None)),
                    'recent_events': len(recent_events),
                    'containers': [{
                        'name': c.name,
                        'ready': c.ready,
                        'restarts': c.restart_count,
                        'state': list(c.state.to_dict().keys())[0] if c.state else 'unknown'
                    } for c in pod.status.container_statuses or []]
                }
        except Exception as e:
            metrics_data['errors'].append(f"Error getting pods in {ns}: {e}")
    
    return pods_info

# Service endpoint testing
def test_response_times():
    services = {
        'whisper': {'port': 30300, 'endpoint': '/health'},
        'piper': {'port': 30200, 'endpoint': '/health'},
        'openwakeword': {'port': 30400, 'endpoint': '/health'}
    }
    resp = {}
    
    try:
        nodes = v1.list_node().items
        node_ip = nodes[0].status.addresses[0].address if nodes else None
        
        for name, info in services.items():
            if node_ip:
                start = time.time()
                try:
                    r = requests.get(f"http://{node_ip}:{info['port']}{info['endpoint']}", 
                                   timeout=5)
                    elapsed = time.time() - start
                    resp[name] = {
                        'time': elapsed,
                        'status': 'ok' if r.status_code == 200 else 'error',
                        'code': r.status_code
                    }
                except Exception as e:
                    resp[name] = {'time': None, 'status': 'error', 'error': str(e)}
            else:
                resp[name] = {'time': None, 'status': 'error', 'error': 'No node IP'}
    except Exception as e:
        metrics_data['errors'].append(f"Error testing services: {e}")
    
    return resp

# Get resource usage via kubectl top (fallback if Prometheus metrics not available)
def get_resource_usage():
    usage = {}
    try:
        # Try to get from Prometheus first
        prom_metrics = metrics_data.get('prometheus_metrics', {})
        if prom_metrics:
            for key, value in prom_metrics.items():
                if key.startswith('cpu_'):
                    pod = key.replace('cpu_', '')
                    usage[pod] = usage.get(pod, {})
                    usage[pod]['cpu'] = f"{value * 100:.1f}%"
                elif key.startswith('memory_'):
                    pod = key.replace('memory_', '')
                    usage[pod] = usage.get(pod, {})
                    usage[pod]['memory'] = f"{value:.2f}Gi"
        
        # If no Prometheus data, fall back to kubectl top
        # This is fine since the image runs in-cluster with proper RBAC
        if not usage and os.getenv('ENABLE_KUBECTL_TOP', 'false').lower() == 'true':
            import subprocess
            res = subprocess.run(
                ['kubectl', 'top', 'pods', '-A', '--no-headers'],
                capture_output=True, text=True, timeout=10
            )
            for line in res.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[0] in ['whisper','piper','openwakeword','homebot']:
                    key = f"{parts[0]}/{parts[1]}"
                    usage[key] = {'cpu': parts[2], 'memory': parts[3]}
    except Exception as e:
        metrics_data['errors'].append(f"Error getting resource usage: {str(e)[:100]}")
    
    return usage

# Alert generation
def generate_alerts():
    alerts = []
    
    # Check pod health
    for pod_key, pod_data in metrics_data.get('pods', {}).items():
        if not pod_data['ready']:
            alerts.append({
                'severity': 'critical',
                'type': 'pod_health',
                'message': f"Pod {pod_key} is not ready",
                'details': pod_data
            })
        if pod_data['restarts'] > 5:
            alerts.append({
                'severity': 'warning',
                'type': 'pod_restarts',
                'message': f"Pod {pod_key} has {pod_data['restarts']} restarts",
                'details': pod_data
            })
    
    # Check response times
    for svc, data in metrics_data.get('response_times', {}).items():
        if data.get('time') and data['time'] > 2.0:
            alerts.append({
                'severity': 'warning',
                'type': 'slow_response',
                'message': f"{svc} response time is {data['time']:.2f}s",
                'details': data
            })
        elif data.get('status') == 'error':
            alerts.append({
                'severity': 'critical',
                'type': 'service_down',
                'message': f"{svc} health check failed",
                'details': data
            })
    
    # Check Prometheus metrics
    prom = metrics_data.get('prometheus_metrics', {})
    for svc in ['whisper', 'piper', 'openwakeword']:
        cpu_key = f"cpu_{svc}"
        if cpu_key in prom and prom[cpu_key] > 0.8:
            alerts.append({
                'severity': 'warning',
                'type': 'high_cpu',
                'message': f"{svc} CPU usage is {prom[cpu_key]*100:.1f}%"
            })
        
        mem_key = f"memory_{svc}"
        if mem_key in prom and prom[mem_key] > 2.0:  # > 2GB
            alerts.append({
                'severity': 'warning',
                'type': 'high_memory',
                'message': f"{svc} memory usage is {prom[mem_key]:.2f}GB"
            })
    
    return alerts

# Enhanced recommendations
def generate_recommendations():
    recs = []
    prom = metrics_data.get('prometheus_metrics', {})
    
    # Whisper model check
    try:
        dep = apps_v1.read_namespaced_deployment('whisper', 'whisper')
        for c in dep.spec.template.spec.containers:
            if c.args and '--model' in c.args:
                idx = c.args.index('--model') + 1
                model = c.args[idx] if idx < len(c.args) else None
                if model and model != 'tiny':
                    recs.append({
                        'severity': 'high',
                        'component': 'whisper',
                        'issue': f'Using {model} model',
                        'recommendation': 'Switch to tiny model for better performance',
                        'impact': 'High latency and resource usage'
                    })
            
            # Check resource limits
            if c.resources and c.resources.limits:
                cpu = c.resources.limits.get('cpu', '0')
                if cpu.endswith('m') and int(cpu[:-1]) < 2000:
                    recs.append({
                        'severity': 'medium',
                        'component': 'whisper',
                        'issue': f'CPU limit low ({cpu})',
                        'recommendation': 'Increase to at least 2000m for better performance',
                        'impact': 'Potential throttling during transcription'
                    })
    except:
        pass
    
    # Resource recommendations based on Prometheus
    for svc in ['whisper', 'piper', 'openwakeword']:
        p99_key = f"p99_{svc}"
        if p99_key in prom and prom[p99_key] > 1.0:
            recs.append({
                'severity': 'medium',
                'component': svc,
                'issue': f'P99 latency is {prom[p99_key]:.2f}s',
                'recommendation': 'Consider scaling or optimizing',
                'impact': 'Poor user experience'
            })
        
        # Check if service-specific metrics indicate issues
        if svc == 'whisper' and 'whisper_avg_transcription_time' in prom:
            if prom['whisper_avg_transcription_time'] > 3.0:
                recs.append({
                    'severity': 'high',
                    'component': 'whisper',
                    'issue': f'Average transcription time is {prom["whisper_avg_transcription_time"]:.2f}s',
                    'recommendation': 'Use smaller model or increase resources',
                    'impact': 'Slow voice response times'
                })
    
    # Node distribution
    node_counts = defaultdict(int)
    for pod_data in metrics_data.get('pods', {}).values():
        node_counts[pod_data['node']] += 1
    
    if len(node_counts) > 0 and max(node_counts.values()) > 3:
        recs.append({
            'severity': 'low',
            'component': 'scheduler',
            'issue': 'Uneven pod distribution across nodes',
            'recommendation': 'Consider pod anti-affinity rules',
            'impact': 'Potential node overload'
        })
    
    # Check for frequent restarts
    for pod_key, pod_data in metrics_data.get('pods', {}).items():
        if pod_data['restarts'] > 2:
            recs.append({
                'severity': 'medium',
                'component': pod_key.split('/')[0],
                'issue': f'Pod {pod_key} has restarted {pod_data["restarts"]} times',
                'recommendation': 'Check logs for OOM kills or crashes',
                'impact': 'Service instability'
            })
    
    return recs

# Metric collection loop
def collect_metrics():
    global metrics_data
    while True:
        try:
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'pods': get_pod_metrics(),
                'response_times': test_response_times(),
                'prometheus_metrics': get_prometheus_metrics(),
                'resource_usage': get_resource_usage(),
                'errors': [],
                'recommendations': [],
                'alerts': []
            }
            
            data['recommendations'] = generate_recommendations()
            data['alerts'] = generate_alerts()
            
            # Store history
            metrics_history['response_times'].append({
                'timestamp': data['timestamp'],
                'data': data['response_times']
            })
            
            # Store Prometheus metrics history
            if data['prometheus_metrics']:
                metrics_history['prometheus'].append({
                    'timestamp': data['timestamp'],
                    'data': data['prometheus_metrics']
                })
            
            metrics_data = data
        except Exception as e:
            print(f"Error in collect_metrics: {e}")
            metrics_data['errors'].append(f"Collection error: {e}")
        
        time.sleep(REFRESH_INTERVAL)

# API Routes with rate limiting
from functools import wraps
from time import time

# Simple rate limiter
request_counts = defaultdict(lambda: {'count': 0, 'window_start': time()})

def rate_limit(max_requests=30, window=60):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Rate limit by IP
            client_ip = request.remote_addr
            current_time = time()
            
            # Reset window if expired
            if current_time - request_counts[client_ip]['window_start'] > window:
                request_counts[client_ip] = {'count': 0, 'window_start': current_time}
            
            # Check rate limit
            if request_counts[client_ip]['count'] >= max_requests:
                return jsonify({'error': 'Rate limit exceeded'}), 429
            
            request_counts[client_ip]['count'] += 1
            return f(*args, **kwargs)
        return wrapper
    return decorator

@app.route('/')
def index():
    return render_template('dashboard.html')

@app.route('/api/metrics')
@rate_limit(max_requests=60, window=60)  # 60 requests per minute
def api_metrics():
    # Sanitize data before sending
    safe_data = {
        'timestamp': metrics_data.get('timestamp'),
        'pods': metrics_data.get('pods', {}),
        'response_times': metrics_data.get('response_times', {}),
        'prometheus_metrics': metrics_data.get('prometheus_metrics', {}),
        'resource_usage': metrics_data.get('resource_usage', {}),
        'errors': metrics_data.get('errors', [])[:10],  # Limit errors to 10
        'recommendations': metrics_data.get('recommendations', [])[:10],  # Limit recommendations
        'alerts': metrics_data.get('alerts', [])[:20]  # Limit alerts
    }
    return jsonify(safe_data)

@app.route('/api/history/<metric_type>')
@rate_limit(max_requests=30, window=60)  # 30 requests per minute
def api_history(metric_type):
    # Validate metric_type
    if metric_type not in ['response_times', 'prometheus']:
        return jsonify({'error': 'Invalid metric type'}), 400
    
    if metric_type in metrics_history:
        # Return limited history (last 50 entries)
        return jsonify(list(metrics_history[metric_type])[-50:])
    return jsonify([])

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

# Prometheus metrics endpoint
@app.route('/metrics')
@rate_limit(max_requests=60, window=60)
def prometheus_metrics():
    """Expose metrics in Prometheus format"""
    lines = []
    lines.append('# HELP voice_monitor_up Voice monitor is up')
    lines.append('# TYPE voice_monitor_up gauge')
    lines.append('voice_monitor_up 1')
    
    # Export response times
    for svc, data in metrics_data.get('response_times', {}).items():
        if data.get('time'):
            lines.append(f'# HELP voice_monitor_response_time Response time for {svc}')
            lines.append(f'# TYPE voice_monitor_response_time gauge')
            lines.append(f'voice_monitor_response_time{{service="{svc}"}} {data["time"]}')
    
    # Export pod status
    for pod_key, pod_data in metrics_data.get('pods', {}).items():
        ns, name = pod_key.split('/')
        ready = 1 if pod_data['ready'] else 0
        lines.append(f'voice_monitor_pod_ready{{namespace="{ns}",pod="{name}"}} {ready}')
        lines.append(f'voice_monitor_pod_restarts{{namespace="{ns}",pod="{name}"}} {pod_data["restarts"]}')
    
    # Export alert count
    alert_counts = defaultdict(int)
    for alert in metrics_data.get('alerts', []):
        alert_counts[alert['severity']] += 1
    
    for severity, count in alert_counts.items():
        lines.append(f'voice_monitor_alerts{{severity="{severity}"}} {count}')
    
    return '\n'.join(lines) + '\n', 200, {'Content-Type': 'text/plain'}

# Main entry point
def main():
    collector = threading.Thread(target=collect_metrics, daemon=True)
    collector.start()
    app.run(host='0.0.0.0', port=FLASK_PORT)

if __name__ == '__main__':
    main()