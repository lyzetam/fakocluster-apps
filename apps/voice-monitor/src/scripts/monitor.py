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
from functools import wraps
from time import time
import pytz

# Configuration with validation
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '30'))
FLASK_PORT = int(os.getenv('FLASK_PORT', '8080'))
PROMETHEUS_URL = os.getenv('PROMETHEUS_URL', 'http://kube-prometheus-stack-prometheus.monitoring.svc.cluster.local:9090')

# Timezone configuration
EST = pytz.timezone('US/Eastern')

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
    'timestamp_est': None,
    'pods': {},
    'response_times': {},
    'resource_usage': {},
    'prometheus_metrics': {},
    'gpu_metrics': {},
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

def get_gpu_metrics():
    """Get GPU-specific metrics from NVIDIA DCGM Exporter"""
    gpu_metrics = {}
    
    try:
        # GPU utilization percentage
        gpu_util_query = 'DCGM_FI_DEV_GPU_UTIL{instance="playground:9400"}'
        gpu_util_data = query_prometheus(gpu_util_query)
        for item in gpu_util_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_utilization'] = float(item['value'][1])
        
        # GPU memory utilization
        gpu_mem_query = 'DCGM_FI_DEV_MEM_COPY_UTIL{instance="playground:9400"}'
        gpu_mem_data = query_prometheus(gpu_mem_query)
        for item in gpu_mem_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_memory_util'] = float(item['value'][1])
        
        # GPU temperature
        gpu_temp_query = 'DCGM_FI_DEV_GPU_TEMP{instance="playground:9400"}'
        gpu_temp_data = query_prometheus(gpu_temp_query)
        for item in gpu_temp_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_temperature'] = float(item['value'][1])
        
        # GPU power consumption
        gpu_power_query = 'DCGM_FI_DEV_POWER_USAGE{instance="playground:9400"}'
        gpu_power_data = query_prometheus(gpu_power_query)
        for item in gpu_power_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_power'] = float(item['value'][1])
        
        # GPU memory used (bytes)
        gpu_mem_used_query = 'DCGM_FI_DEV_FB_USED{instance="playground:9400"}'
        gpu_mem_used_data = query_prometheus(gpu_mem_used_query)
        for item in gpu_mem_used_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_memory_used_mb'] = float(item['value'][1]) / (1024 * 1024)
        
        # GPU memory total (bytes)
        gpu_mem_total_query = 'DCGM_FI_DEV_FB_TOTAL{instance="playground:9400"}'
        gpu_mem_total_data = query_prometheus(gpu_mem_total_query)
        for item in gpu_mem_total_data:
            gpu_id = item['metric'].get('gpu', '0')
            gpu_metrics[f'gpu_{gpu_id}_memory_total_mb'] = float(item['value'][1]) / (1024 * 1024)
        
        # Calculate memory usage percentage
        for key in gpu_metrics:
            if 'memory_used_mb' in key:
                gpu_id = key.split('_')[1]
                total_key = f'gpu_{gpu_id}_memory_total_mb'
                if total_key in gpu_metrics and gpu_metrics[total_key] > 0:
                    percentage = (gpu_metrics[key] / gpu_metrics[total_key]) * 100
                    gpu_metrics[f'gpu_{gpu_id}_memory_percent'] = percentage
        
        # GPU process count (if available)
        gpu_proc_query = 'DCGM_FI_DEV_COUNT{instance="playground:9400"}'
        gpu_proc_data = query_prometheus(gpu_proc_query)
        if gpu_proc_data:
            gpu_metrics['gpu_count'] = float(gpu_proc_data[0]['value'][1])
            
    except Exception as e:
        metrics_data['errors'].append(f"GPU metrics error: {str(e)[:100]}")
    
    return gpu_metrics

def get_prometheus_metrics():
    metrics = {}
    
    # CPU usage by pod (already in percentage)
    cpu_query = 'rate(container_cpu_usage_seconds_total{namespace=~"whisper|piper|openwakeword|homebot|ollama|ollama-webui"}[5m]) * 100'
    cpu_data = query_prometheus(cpu_query)
    for item in cpu_data:
        pod = item['metric'].get('pod', '')
        if pod:
            metrics[f"cpu_{pod}"] = float(item['value'][1])
    
    # Memory usage
    mem_query = 'container_memory_working_set_bytes{namespace=~"whisper|piper|openwakeword|homebot|ollama|ollama-webui"}'
    mem_data = query_prometheus(mem_query)
    for item in mem_data:
        pod = item['metric'].get('pod', '')
        if pod:
            metrics[f"memory_{pod}"] = float(item['value'][1]) / (1024**3)  # GB
    
    # GPU resource requests and limits from pods
    gpu_requests_query = 'kube_pod_container_resource_requests{resource="nvidia_com_gpu"}'
    gpu_requests_data = query_prometheus(gpu_requests_query)
    for item in gpu_requests_data:
        pod = item['metric'].get('pod', '')
        if pod:
            metrics[f"gpu_requested_{pod}"] = float(item['value'][1])
    
    # Request rate - for voice services
    for service in ['whisper', 'piper', 'openwakeword', 'ollama']:
        # Try different metric names that might be exposed
        for metric_name in ['http_requests_total', 'requests_total', f'{service}_requests_total']:
            req_query = f'rate({metric_name}{{namespace="{service}"}}[5m])'
            req_data = query_prometheus(req_query)
            if req_data:
                metrics[f"requests_{service}"] = float(req_data[0]['value'][1])
                break
    
    # Latency percentiles
    for service in ['whisper', 'piper', 'openwakeword', 'ollama']:
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
    
    # Ollama model loading time
    ollama_load_query = 'rate(ollama_model_load_duration_seconds_sum[5m]) / rate(ollama_model_load_duration_seconds_count[5m])'
    ollama_load_data = query_prometheus(ollama_load_query)
    if ollama_load_data:
        metrics['ollama_avg_model_load_time'] = float(ollama_load_data[0]['value'][1])
    
    return metrics

# Enhanced pod metrics
def get_pod_metrics():
    pods_info = {}
    namespaces = ['whisper', 'piper', 'openwakeword', 'homebot', 'ollama', 'ollama-webui']
    
    for ns in namespaces:
        try:
            pods = v1.list_namespaced_pod(namespace=ns)
            for pod in pods.items:
                key = f"{ns}/{pod.metadata.name}"
                
                # Check for GPU usage
                gpu_requested = False
                gpu_limit = 0
                if pod.spec.containers:
                    for container in pod.spec.containers:
                        if container.resources and container.resources.requests:
                            gpu_req = container.resources.requests.get('nvidia.com/gpu', '0')
                            if gpu_req and int(gpu_req) > 0:
                                gpu_requested = True
                                gpu_limit = int(gpu_req)
                
                # Get node info for GPU nodes
                is_gpu_node = False
                if pod.spec.node_name:
                    try:
                        node = v1.read_node(pod.spec.node_name)
                        node_labels = node.metadata.labels or {}
                        is_gpu_node = node_labels.get('nvidia.com/gpu') == 'true'
                    except:
                        pass
                
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
                    'gpu_requested': gpu_requested,
                    'gpu_limit': gpu_limit,
                    'is_gpu_node': is_gpu_node,
                    'containers': [{
                        'name': c.name,
                        'ready': c.ready,
                        'restarts': c.restart_count,
                        'state': list(c.state.to_dict().keys())[0] if c.state else 'unknown'
                    } for c in pod.status.container_statuses or []]
                }
        except Exception as e:
            metrics_data['errors'].append(f"Error getting pods in {ns}: {str(e)[:100]}")
    
    return pods_info

# Service endpoint testing - Fixed for Wyoming protocol and added GPU services
def test_response_times():
    services = {
        'whisper': {'port': 30300, 'protocol': 'tcp'},
        'piper': {'port': 30200, 'protocol': 'tcp'},
        'openwakeword': {'port': 30400, 'protocol': 'tcp'},
        'ollama': {'port': 31434, 'protocol': 'tcp'},
        'voice-monitor': {'port': 30808, 'protocol': 'http'}
    }
    resp = {}
    
    try:
        nodes = v1.list_node().items
        node_ip = nodes[0].status.addresses[0].address if nodes else None
        
        for name, info in services.items():
            if node_ip:
                start = time.time()
                try:
                    if info['protocol'] == 'tcp':
                        # Test TCP connection for Wyoming protocol
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(5)
                        result = sock.connect_ex((node_ip, info['port']))
                        sock.close()
                        elapsed = time.time() - start
                        
                        resp[name] = {
                            'time': elapsed,
                            'status': 'ok' if result == 0 else 'error',
                            'code': result
                        }
                    elif info['protocol'] == 'http':
                        # Test HTTP endpoint
                        response = requests.get(f"http://{node_ip}:{info['port']}/health", timeout=5)
                        elapsed = time.time() - start
                        
                        resp[name] = {
                            'time': elapsed,
                            'status': 'ok' if response.status_code == 200 else 'error',
                            'code': response.status_code
                        }
                except Exception as e:
                    resp[name] = {'time': None, 'status': 'error', 'error': str(e)}
            else:
                resp[name] = {'time': None, 'status': 'error', 'error': 'No node IP'}
    except Exception as e:
        metrics_data['errors'].append(f"Error testing services: {str(e)[:100]}")
    
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
                    usage[pod]['cpu'] = f"{value:.1f}%"  # Already in percentage
                elif key.startswith('memory_'):
                    pod = key.replace('memory_', '')
                    usage[pod] = usage.get(pod, {})
                    usage[pod]['memory'] = f"{value:.2f}Gi"
                elif key.startswith('gpu_requested_'):
                    pod = key.replace('gpu_requested_', '')
                    usage[pod] = usage.get(pod, {})
                    usage[pod]['gpu'] = f"{int(value)} GPU"
        
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
                if len(parts) >= 4 and parts[0] in ['whisper','piper','openwakeword','homebot','ollama','ollama-webui']:
                    key = f"{parts[0]}/{parts[1]}"
                    usage[key] = {'cpu': parts[2], 'memory': parts[3]}
    except Exception as e:
        metrics_data['errors'].append(f"Error getting resource usage: {str(e)[:100]}")
    
    return usage

# Enhanced alert generation with GPU monitoring
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
        
        # GPU-specific alerts
        if pod_data.get('gpu_requested') and not pod_data.get('is_gpu_node'):
            alerts.append({
                'severity': 'critical',
                'type': 'gpu_scheduling',
                'message': f"GPU pod {pod_key} not scheduled on GPU node",
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
                'message': f"{svc} connection failed",
                'details': data
            })
    
    # Check Prometheus metrics
    prom = metrics_data.get('prometheus_metrics', {})
    for svc in ['whisper', 'piper', 'openwakeword', 'ollama']:
        cpu_key = f"cpu_{svc}"
        if cpu_key in prom and prom[cpu_key] > 80:  # Already in percentage
            alerts.append({
                'severity': 'warning',
                'type': 'high_cpu',
                'message': f"{svc} CPU usage is {prom[cpu_key]:.1f}%"
            })
        
        mem_key = f"memory_{svc}"
        if mem_key in prom and prom[mem_key] > 2.0:  # > 2GB
            alerts.append({
                'severity': 'warning',
                'type': 'high_memory',
                'message': f"{svc} memory usage is {prom[mem_key]:.2f}GB"
            })
    
    # GPU alerts
    gpu_metrics = metrics_data.get('gpu_metrics', {})
    for key, value in gpu_metrics.items():
        if 'temperature' in key and value > 80:
            gpu_id = key.split('_')[1]
            alerts.append({
                'severity': 'critical',
                'type': 'gpu_temperature',
                'message': f"GPU {gpu_id} temperature is {value:.1f}°C"
            })
        elif 'utilization' in key and value > 95:
            gpu_id = key.split('_')[1]
            alerts.append({
                'severity': 'warning',
                'type': 'gpu_utilization',
                'message': f"GPU {gpu_id} utilization is {value:.1f}%"
            })
        elif 'memory_percent' in key and value > 90:
            gpu_id = key.split('_')[1]
            alerts.append({
                'severity': 'warning',
                'type': 'gpu_memory',
                'message': f"GPU {gpu_id} memory usage is {value:.1f}%"
            })
    
    return alerts

# Enhanced recommendations with GPU considerations
def generate_recommendations():
    recs = []
    prom = metrics_data.get('prometheus_metrics', {})
    gpu_metrics = metrics_data.get('gpu_metrics', {})
    
    # Whisper model check
    try:
        dep = apps_v1.read_namespaced_deployment('whisper-gpu', 'whisper')
        for c in dep.spec.template.spec.containers:
            if c.args and '--model' in c.args:
                idx = c.args.index('--model') + 1
                model = c.args[idx] if idx < len(c.args) else None
                if model and model not in ['tiny', 'base']:
                    recs.append({
                        'severity': 'high',
                        'component': 'whisper',
                        'issue': f'Using {model} model with limited GPU',
                        'recommendation': 'Switch to base or tiny model for GT 1030',
                        'impact': 'High latency and potential OOM errors'
                    })
    except:
        pass
    
    # GPU usage recommendations
    gpu_util_values = [v for k, v in gpu_metrics.items() if 'utilization' in k]
    if gpu_util_values:
        avg_gpu_util = sum(gpu_util_values) / len(gpu_util_values)
        if avg_gpu_util < 30:
            recs.append({
                'severity': 'medium',
                'component': 'gpu',
                'issue': f'Low GPU utilization ({avg_gpu_util:.1f}%)',
                'recommendation': 'Consider moving GPU workloads to CPU or using larger models',
                'impact': 'Underutilized expensive hardware'
            })
        elif avg_gpu_util > 85:
            recs.append({
                'severity': 'high',
                'component': 'gpu',
                'issue': f'High GPU utilization ({avg_gpu_util:.1f}%)',
                'recommendation': 'Scale horizontally or optimize workloads',
                'impact': 'Performance bottleneck'
            })
    
    # Check GPU memory usage
    for key, value in gpu_metrics.items():
        if 'memory_percent' in key and value > 80:
            gpu_id = key.split('_')[1]
            recs.append({
                'severity': 'high',
                'component': 'gpu',
                'issue': f'GPU {gpu_id} memory usage high ({value:.1f}%)',
                'recommendation': 'Reduce model size or batch size',
                'impact': 'Risk of OOM errors'
            })
    
    # Resource recommendations based on Prometheus
    for svc in ['whisper', 'piper', 'openwakeword', 'ollama']:
        p99_key = f"p99_{svc}"
        if p99_key in prom and prom[p99_key] > 1.0:
            recs.append({
                'severity': 'medium',
                'component': svc,
                'issue': f'P99 latency is {prom[p99_key]:.2f}s',
                'recommendation': 'Consider scaling or optimizing',
                'impact': 'Poor user experience'
            })
        
        # Service-specific recommendations
        if svc == 'whisper' and 'whisper_avg_transcription_time' in prom:
            if prom['whisper_avg_transcription_time'] > 3.0:
                recs.append({
                    'severity': 'high',
                    'component': 'whisper',
                    'issue': f'Average transcription time is {prom["whisper_avg_transcription_time"]:.2f}s',
                    'recommendation': 'Use smaller model or verify GPU acceleration',
                    'impact': 'Slow voice response times'
                })
        elif svc == 'ollama' and 'ollama_avg_model_load_time' in prom:
            if prom['ollama_avg_model_load_time'] > 10.0:
                recs.append({
                    'severity': 'medium',
                    'component': 'ollama',
                    'issue': f'Model load time is {prom["ollama_avg_model_load_time"]:.2f}s',
                    'recommendation': 'Keep models loaded or use smaller models',
                    'impact': 'Slow initial responses'
                })
    
    # GPU vs CPU deployment recommendations
    gpu_pod_count = sum(1 for pod_data in metrics_data.get('pods', {}).values() 
                       if pod_data.get('gpu_requested'))
    if gpu_pod_count > 1 and gpu_util_values and max(gpu_util_values) < 50:
        recs.append({
            'severity': 'low',
            'component': 'scheduler',
            'issue': f'{gpu_pod_count} GPU pods but low utilization',
            'recommendation': 'Consider running some workloads on CPU',
            'impact': 'Resource optimization opportunity'
        })
    
    return recs

# Metric collection loop
def collect_metrics():
    global metrics_data
    while True:
        try:
            utc_now = datetime.utcnow()
            est_now = pytz.utc.localize(utc_now).astimezone(EST)
            
            data = {
                'timestamp': utc_now.isoformat(),
                'timestamp_est': est_now.strftime('%Y-%m-%d %H:%M:%S %Z'),
                'pods': get_pod_metrics(),
                'response_times': test_response_times(),
                'prometheus_metrics': get_prometheus_metrics(),
                'gpu_metrics': get_gpu_metrics(),
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
            
            # Store GPU metrics history
            if data['gpu_metrics']:
                metrics_history['gpu'].append({
                    'timestamp': data['timestamp'],
                    'data': data['gpu_metrics']
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
        'timestamp_est': metrics_data.get('timestamp_est'),
        'pods': metrics_data.get('pods', {}),
        'response_times': metrics_data.get('response_times', {}),
        'prometheus_metrics': metrics_data.get('prometheus_metrics', {}),
        'gpu_metrics': metrics_data.get('gpu_metrics', {}),
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
    if metric_type not in ['response_times', 'prometheus', 'gpu']:
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
        
        # GPU metrics
        if pod_data.get('gpu_requested'):
            lines.append(f'voice_monitor_pod_gpu_requested{{namespace="{ns}",pod="{name}"}} {pod_data["gpu_limit"]}')
    
    # Export GPU metrics
    for key, value in metrics_data.get('gpu_metrics', {}).items():
        metric_name = key.replace('_', '_').lower()
        if 'gpu_' in key:
            gpu_id = key.split('_')[1]
            metric_type = '_'.join(key.split('_')[2:])
            lines.append(f'voice_monitor_gpu_{metric_type}{{gpu="{gpu_id}"}} {value}')
    
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