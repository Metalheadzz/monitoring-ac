import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, Blueprint, request, jsonify, send_from_directory, Response
from flask_cors import CORS
from influxdb_client import InfluxDBClient
import paho.mqtt.client as mqtt_client

# ── Path Setup ───────────────────────────────────────────
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend', 'dist'))

# ── Flask App ────────────────────────────────────────────
app = Flask(__name__)
CORS(app)

# ── InfluxDB Config ──────────────────────────────────────
INFLUX_URL    = "http://localhost:8087"
INFLUX_TOKEN  = "yr3tJGXch-qnosHeVmts9IEPe0FPn9ptcLMM1H4jFA-CTMaZHJ8vGpTrIInLuNYr_IP2FMJ3mm0DXIp72-P7vw=="
INFLUX_ORG    = "myorg"
INFLUX_BUCKET = "mybucket"

influx_client = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
query_api = influx_client.query_api()

# ── MQTT Config ──────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_SENSOR  = "sensor/suhu"
TOPIC_CONTROL = "control/ac"

latest_data = {} # Dict to store data per room
sse_clients = []
sse_lock = threading.Lock()
mqtt_connected = False

def on_mqtt_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        client.subscribe(TOPIC_SENSOR)
        print(f"[API-MQTT] OK - Connected & subscribed to {TOPIC_SENSOR}")
    else:
        mqtt_connected = False
        print(f"[API-MQTT] FAIL - Connect failed, rc={rc}")

def on_mqtt_message(client, userdata, msg):
    global latest_data
    try:
        data = json.loads(msg.payload.decode())
        ruangan = data.get("ruangan", "Ruang Utama")
        room_data = {
            "ruangan": ruangan,
            "suhu": data.get("suhu"),
            "status_ac": data.get("status_ac", "OFF"),
            "timestamp": data.get("timestamp", datetime.now().isoformat())
        }
        latest_data[ruangan] = room_data
        event_data = f"data: {json.dumps(room_data)}\n\n"
        with sse_lock:
            dead = []
            for q in sse_clients:
                try:
                    q.append(event_data)
                except:
                    dead.append(q)
            for d in dead:
                sse_clients.remove(d)
    except Exception as e:
        print(f"[API-MQTT] Error: {e}")

def on_mqtt_disconnect(client, userdata, rc):
    global mqtt_connected
    mqtt_connected = False
    print(f"[API-MQTT] Disconnected (rc={rc})")

mqtt = mqtt_client.Client(client_id="flask-api-bridge")
mqtt.on_connect = on_mqtt_connect
mqtt.on_message = on_mqtt_message
mqtt.on_disconnect = on_mqtt_disconnect

def start_mqtt():
    while True:
        try:
            mqtt.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
            mqtt.loop_forever()
        except Exception as e:
            print(f"[API-MQTT] Connection error: {e}, retrying in 3s...")
            time.sleep(3)

mqtt_thread = threading.Thread(target=start_mqtt, daemon=True)
mqtt_thread.start()

# ══════════════════════════════════════════════════════════
#   API Blueprint (registered FIRST for priority)
# ══════════════════════════════════════════════════════════
api_bp = Blueprint('api', __name__, url_prefix='/api')

def get_valid_users():
    users = {}
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip komentar dan baris kosong
                if line and not line.startswith('#') and '=' in line:
                    key, val = line.split('=', 1)
                    if key.startswith('USER_'):
                        # Ubah USER_MSOB jadi msob
                        username = key[5:].lower()
                        users[username] = val
    else:
        # Fallback kalau file .env hilang
        users['admin'] = 'admin12345'
    return users

@api_bp.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username', '').lower()
    password = data.get('password', '')
    
    valid_users = get_valid_users()

    if username in valid_users and valid_users[username] == password:
        return jsonify({"token": f"auth-token-{username}", "success": True})
        
    return jsonify({"success": False, "message": "Invalid username or password"}), 401

@api_bp.route('/stream', methods=['GET'])
def stream():
    """SSE endpoint - streams realtime sensor data to browser"""
    def event_stream():
        q = []
        with sse_lock:
            sse_clients.append(q)
        try:
            # Send current data for all rooms on connect
            for ruangan, room_data in latest_data.items():
                if room_data["suhu"] is not None:
                    yield f"data: {json.dumps(room_data)}\n\n"
            while True:
                if q:
                    yield q.pop(0)
                else:
                    time.sleep(0.5)
        except GeneratorExit:
            with sse_lock:
                if q in sse_clients:
                    sse_clients.remove(q)

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'Connection': 'keep-alive',
            'X-Accel-Buffering': 'no'
        }
    )

@api_bp.route('/control', methods=['POST'])
def control_ac():
    """Send AC control command via MQTT"""
    data = request.json
    command = data.get('command', '').upper()
    ruangan = data.get('ruangan', 'Ruang Utama')
    if command not in ['ON', 'OFF']:
        return jsonify({"error": "Command must be ON or OFF"}), 400
    if not mqtt_connected:
        return jsonify({"error": "MQTT not connected"}), 503
    
    if ruangan == 'Ruang Utama':
        # Default behavior for original simulator
        mqtt.publish(TOPIC_CONTROL, command)
    else:
        # Publish to a room specific topic if needed, or just send a JSON payload 
        # (Assuming the new simulator_teman.py handles JSON, which currently it doesn't...
        # Wait, simulator_teman.py also expects plain string! Let's just send the command)
        mqtt.publish(f"{TOPIC_CONTROL}/{ruangan.replace(' ', '_')}", command)
        
    return jsonify({"success": True, "command": command, "ruangan": ruangan})

@api_bp.route('/status', methods=['GET'])
def get_status():
    """Get current system status"""
    return jsonify({
        "mqtt_connected": mqtt_connected,
        "latest_data": latest_data
    })

@api_bp.route('/rooms', methods=['GET'])
def get_rooms():
    """Fetch available rooms from InfluxDB tags"""
    query = f'''
        import "influxdata/influxdb/schema"
        schema.tagValues(bucket: "{INFLUX_BUCKET}", tag: "ruangan")
    '''
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        rooms = [record.get_value() for table in tables for record in table.records]
        if not rooms:
            rooms = ["Ruang Utama"]
        return jsonify({"rooms": rooms})
    except Exception as e:
        print(f"Error fetching rooms: {e}")
        return jsonify({"error": str(e), "rooms": list(latest_data.keys()) or ["Ruang Utama"]})

@api_bp.route('/history', methods=['GET'])
def get_history():
    time_range = request.args.get('range', '1y')
    ruangan = request.args.get('ruangan', 'Ruang Utama')
    date_filter = request.args.get('date', None)

    range_clause = ""
    window = "1d"
    
    if date_filter:
        try:
            # Ensure the date format is valid
            start_date = f"{date_filter}T00:00:00Z"
            end_date = f"{date_filter}T23:59:59Z"
            range_clause = f'range(start: {start_date}, stop: {end_date})'
            window = '1h' # Aggregate by hour for a specific day
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400
    else:
        if time_range == '1h':
            window = '1m'
        elif time_range == '24h':
            window = '1h'
        elif time_range == '30d':
            window = '1d'
        elif time_range == '1y':
            window = '1w'
        else:
            window = '1d'
            time_range = '1y'
        range_clause = f'range(start: -{time_range})'

    query = f'''
        from(bucket: "{INFLUX_BUCKET}")
          |> {range_clause}
          |> filter(fn: (r) => r._measurement == "suhu_ruangan")
          |> filter(fn: (r) => r._field == "suhu")
          |> filter(fn: (r) => r.ruangan == "{ruangan}")
          |> aggregateWindow(every: {window}, fn: mean, createEmpty: false)
          |> yield(name: "mean")
    '''
    try:
        tables = query_api.query(query, org=INFLUX_ORG)
        results = []
        for table in tables:
            for record in table.records:
                results.append({
                    "time": record.get_time().isoformat(),
                    "suhu": round(record.get_value(), 2) if record.get_value() else None
                })
        return jsonify(results)
    except Exception as e:
        print(f"Error querying InfluxDB: {e}")
        return jsonify({"error": str(e)}), 500

# Register API blueprint FIRST
app.register_blueprint(api_bp)

# ══════════════════════════════════════════════════════════
#   Static File Serving (catch-all, registered LAST)
# ══════════════════════════════════════════════════════════
@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_DIST, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    file_path = os.path.join(FRONTEND_DIST, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIST, path)
    return send_from_directory(FRONTEND_DIST, 'index.html')

if __name__ == '__main__':
    print("=" * 50)
    print("  SMART AC MONITORING - API SERVER")
    print("  > Web Dashboard : http://127.0.0.1:5000/")
    print("  > SSE Stream    : http://127.0.0.1:5000/api/stream")
    print("  > History API   : http://127.0.0.1:5000/api/history")
    print("  > AC Control    : http://127.0.0.1:5000/api/control")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, threaded=True)
