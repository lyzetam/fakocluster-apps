import os
import time
import threading
from datetime import datetime
from flask import Flask, jsonify, render_template
from kubernetes import client, config
import socket
import subprocess

# Configuration via environment
REFRESH_INTERVAL = int(os.getenv('REFRESH_INTERVAL', '30'))
FLASK_PORT = int(os.getenv('FLASK_PORT', '8080'))

# Flask app, pointing to UI templates
app = Flask(__name__, template_folder='../ui/templates')
metrics_data = {
    'timestamp': None,
    'pods': {},
    'response_times': {},
    'resource_usage': {},
    'errors': [],
    'recommendations': []
}

# Initialize Kubernetes API clients

def init_k8s():
    try:
        config.load_incluster_config()
    except:
        config.load_kube_config()
    return client.CoreV1Api(), client.AppsV1Api()

v1, apps_v1 = init_k8s()

# ----------------------
# Metric collection functions
# ----------------------

def test_component_response(host, port, timeout=5):
    start = time.time()
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        if result == 0:
            return time.time() - start
    except:
        pass
    return None


def get_pod_metrics():
    pods_info = {}
    namespaces = ['whisper', 'piper', 'openwakeword', 'homebot']
    for ns in namespaces:
        try:
            pods = v1.list_namespaced_pod(namespace=ns)
            for pod in pods.items:
                key = f"{ns}/{pod.metadata.name}"
                pods_info[key] = {
                    'namespace': ns,
                    'name': pod.metadata.name,
                    'status': pod.status.phase,
                    'node': pod.spec.node_name,
                    'ready': all(c.ready for c in pod.status.container_statuses or []),
                    'restarts': sum(c.restart_count for c in pod.status.container_statuses or [])
                }
        except Exception as e:
            metrics_data['errors'].append(f"Error pods {ns}: {e}")
    return pods_info


def get_resource_usage():
    usage = {}
    try:
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
        metrics_data['errors'].append(f"Error resource: {e}")
    return usage


def test_response_times():
    services = {
        'whisper': {'port':30300},
        'piper': {'port':30200},
        'openwakeword': {'port':30400}
    }
    resp = {}
    try:
        nodes = v1.list_node().items
        node_ip = nodes[0].status.addresses[0].address if nodes else None
        for name, info in services.items():
            t = test_component_response(node_ip, info['port']) if node_ip else None
            resp[name] = {'time': t, 'status': 'ok' if t else 'timeout'}
    except Exception as e:
        resp[name] = {'time': None, 'status': 'error', 'error': str(e)}
    return resp


def generate_recommendations():
    recs = []
    # whisper deployment checks
    try:
        dep = apps_v1.read_namespaced_deployment('whisper','whisper')
        for c in dep.spec.template.spec.containers:
            if c.args and '--model' in c.args:
                idx = c.args.index('--model')+1
                model = c.args[idx] if idx < len(c.args) else None
                if model and model!='tiny':
                    recs.append({
                        'severity':'high','component':'whisper',
                        'issue':f'Using {model} model',
                        'recommendation':'Switch to tiny for performance'
                    })
            if c.resources and c.resources.limits:
                cpu = c.resources.limits.get('cpu','0')
                if cpu.endswith('m') and int(cpu[:-1])<2000:
                    recs.append({
                        'severity':'medium','component':'whisper',
                        'issue':f'CPU limit low ({cpu})',
                        'recommendation':'Raise to at least 2000m'
                    })
    except:
        pass
    # response time slow
    for comp, data in metrics_data.get('response_times',{}).items():
        if data.get('time') and data['time']>1.0:
            recs.append({
                'severity':'high','component':comp,
                'issue':f'Slow response ({data["time"]:.2f}s)',
                'recommendation':'Inspect logs and resources'
            })
    return recs


def collect_metrics():
    global metrics_data
    while True:
        data = {
            'timestamp': datetime.utcnow().isoformat(),
            'pods': get_pod_metrics(),
            'response_times': test_response_times(),
            'resource_usage': get_resource_usage(),
            'errors': [],
            'recommendations': []
        }
        data['recommendations'] = generate_recommendations()
        metrics_data = data
        time.sleep(REFRESH_INTERVAL)

# HTTP routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/metrics')
def api_metrics():
    return jsonify(metrics_data)

# Entry point
def main():
    collector = threading.Thread(target=collect_metrics, daemon=True)
    collector.start()
    app.run(host='0.0.0.0', port=FLASK_PORT)

if __name__ == '__main__':
    main()