"""
bridge.py - Jembatan MQTT → InfluxDB
======================================
Cara kerja:
- Subscribe MQTT topic: sensor/suhu
- Setiap data masuk → tulis ke InfluxDB
- Measurement: suhu_ruangan
- Fields: suhu (float), ac_on (int 0/1)
- Tags: status_ac (ON/OFF)
"""

import paho.mqtt.client as mqtt
import json
from datetime import datetime
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# ── Konfigurasi ──────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_SENSOR = "sensor/suhu"

INFLUX_URL    = "http://localhost:8087"
INFLUX_TOKEN  = "yr3tJGXch-qnosHeVmts9IEPe0FPn9ptcLMM1H4jFA-CTMaZHJ8vGpTrIInLuNYr_IP2FMJ3mm0DXIp72-P7vw=="
INFLUX_ORG    = "myorg"
INFLUX_BUCKET = "mybucket"
# ─────────────────────────────────────────────────────────

# Setup InfluxDB client
influx_client = InfluxDBClient(
    url=INFLUX_URL,
    token=INFLUX_TOKEN,
    org=INFLUX_ORG
)
write_api = influx_client.write_api(write_options=SYNCHRONOUS)

print("=" * 50)
print("  MQTT → InfluxDB BRIDGE")
print("=" * 50)

# Verifikasi koneksi InfluxDB
try:
    health = influx_client.health()
    print(f"[✓] InfluxDB: {health.status} ({INFLUX_URL})")
except Exception as e:
    print(f"[✗] Gagal konek InfluxDB: {e}")
    exit(1)

data_count = 0

def tulis_ke_influxdb(suhu, status_ac, timestamp_str, ruangan="Ruang Utama"):
    global data_count
    try:
        point = (
            Point("suhu_ruangan")
            .tag("status_ac", status_ac)
            .tag("ruangan", ruangan)
            .field("suhu", float(suhu))
            .field("ac_on", 1 if status_ac == "ON" else 0)
        )
        write_api.write(bucket=INFLUX_BUCKET, org=INFLUX_ORG, record=point)
        data_count += 1
        return True
    except Exception as e:
        print(f"[✗] Gagal tulis InfluxDB: {e}")
        return False

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[✓] Terhubung ke MQTT Broker {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_SENSOR)
        print(f"[✓] Subscribe ke topic: {TOPIC_SENSOR}")
        print(f"[✓] Menulis ke bucket: {INFLUX_BUCKET}")
        print("=" * 50)
        print("  Menunggu data sensor...\n")
    else:
        print(f"[✗] Gagal konek MQTT, kode: {rc}")

def on_message(client, userdata, msg):
    try:
        data = json.loads(msg.payload.decode())
        suhu      = data.get("suhu")
        status_ac = data.get("status_ac", "OFF")
        timestamp = data.get("timestamp", datetime.now().isoformat())
        ruangan   = data.get("ruangan", "Ruang Utama")

        if suhu is None:
            print(f"[!] Data tidak valid: {data}")
            return

        ok = tulis_ke_influxdb(suhu, status_ac, timestamp, ruangan)
        status_icon = "✓" if ok else "✗"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] [{status_icon}] "
              f"Ruang: {ruangan} | Suhu: {suhu}°C | AC: {status_ac} | "
              f"Total tersimpan: {data_count}")

    except json.JSONDecodeError:
        print(f"[!] Payload bukan JSON valid: {msg.payload}")
    except Exception as e:
        print(f"[!] Error: {e}")

def on_disconnect(client, userdata, rc):
    print(f"\n[!] Terputus dari broker (rc={rc})")

# Setup MQTT
client = mqtt.Client(client_id="python-bridge")
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

try:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
except Exception as e:
    print(f"[✗] Tidak bisa konek ke broker: {e}")
    exit(1)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print(f"\n[!] Bridge dihentikan. Total data tersimpan: {data_count}")
    client.disconnect()
    influx_client.close()
    print("[✓] Koneksi ditutup")
