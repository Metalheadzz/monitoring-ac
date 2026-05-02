"""
simulator.py - Simulasi Sensor Suhu dengan Kontrol AC
======================================================
Cara kerja:
- Publish data suhu ke MQTT topic: sensor/suhu
- Subscribe perintah AC dari topic: control/ac
- Suhu naik jika AC OFF, turun jika AC ON
"""

import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime

# ── Konfigurasi ──────────────────────────────────────────
BROKER_HOST = "localhost"
BROKER_PORT = 1883
TOPIC_SENSOR  = "sensor/suhu"
TOPIC_CONTROL = "control/ac"
INTERVAL_DETIK = 2          # kirim data setiap 2 detik

SUHU_AWAL    = 30.0         # suhu awal ruangan (°C)
SUHU_MIN     = 18.0         # batas minimal (AC nyala)
SUHU_MAX     = 40.0         # batas maksimal (ruangan panas)
# ─────────────────────────────────────────────────────────

suhu_saat_ini = SUHU_AWAL
status_ac     = "OFF"

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"[✓] Terhubung ke MQTT Broker {BROKER_HOST}:{BROKER_PORT}")
        client.subscribe(TOPIC_CONTROL)
        print(f"[✓] Subscribe ke topic: {TOPIC_CONTROL}")
    else:
        print(f"[✗] Gagal konek, kode error: {rc}")

def on_message(client, userdata, msg):
    global status_ac
    perintah = msg.payload.decode().strip().upper()
    if perintah in ["ON", "OFF"]:
        status_ac = perintah
        print(f"\n[PERINTAH] AC diubah → {status_ac}")
    else:
        print(f"[!] Perintah tidak dikenal: {perintah}")

def on_disconnect(client, userdata, rc):
    print(f"[!] Terputus dari broker (rc={rc}), mencoba reconnect...")

# Setup MQTT client
client = mqtt.Client(client_id="python-simulator")
client.on_connect    = on_connect
client.on_message    = on_message
client.on_disconnect = on_disconnect

print("=" * 50)
print("  SIMULATOR SUHU RUANGAN - Monitoring AC")
print("=" * 50)
print(f"  Broker : {BROKER_HOST}:{BROKER_PORT}")
print(f"  Publish: {TOPIC_SENSOR}")
print(f"  Control: {TOPIC_CONTROL}")
print(f"  Interval: {INTERVAL_DETIK} detik")
print("=" * 50)

try:
    client.connect(BROKER_HOST, BROKER_PORT, keepalive=60)
except Exception as e:
    print(f"[✗] Tidak bisa konek ke broker: {e}")
    print("    Pastikan Mosquitto sudah berjalan (docker compose up -d)")
    exit(1)

client.loop_start()

try:
    while True:
        #global suhu_saat_ini

        # Efek AC terhadap suhu
        if status_ac == "ON":
            # AC nyala: suhu turun 0.1–0.3 per interval
            delta = random.uniform(0.1, 0.3)
            suhu_saat_ini = max(SUHU_MIN, suhu_saat_ini - delta)
        else:
            # AC mati: suhu naik 0.05–0.15 per interval (efek panas ruangan)
            delta = random.uniform(0.05, 0.15)
            suhu_saat_ini = min(SUHU_MAX, suhu_saat_ini + delta)

        # Tambah noise sensor (±0.1°C) biar lebih realistis
        noise = random.uniform(-0.1, 0.1)
        suhu_terukur = round(suhu_saat_ini + noise, 1)

        # Payload JSON
        payload = {
            "suhu"      : suhu_terukur,
            "status_ac" : status_ac,
            "timestamp" : datetime.now().isoformat()
        }

        # Publish ke MQTT
        result = client.publish(TOPIC_SENSOR, json.dumps(payload), qos=0)

        # Indikator visual di terminal
        bar_len   = int((suhu_terukur - 15) / 30 * 20)  # 15–45°C → 0–20 bar
        bar_len   = max(0, min(20, bar_len))
        temp_bar  = "█" * bar_len + "░" * (20 - bar_len)
        ac_icon   = "❄️ " if status_ac == "ON" else "🌡️"

        print(f"[{datetime.now().strftime('%H:%M:%S')}] "
              f"{ac_icon} AC: {status_ac:<3} | "
              f"Suhu: [{temp_bar}] {suhu_terukur:5.1f}°C")

        time.sleep(INTERVAL_DETIK)

except KeyboardInterrupt:
    print("\n\n[!] Simulator dihentikan oleh user (Ctrl+C)")
    client.loop_stop()
    client.disconnect()
    print("[✓] Koneksi MQTT ditutup")
