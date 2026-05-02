📐 Arsitektur Sistem

[python/simulator.py]
  Simulasi sensor suhu (naik/turun berdasarkan status AC)
  PUBLISH → MQTT topic: sensor/suhu
  SUBSCRIBE ← MQTT topic: control/ac
        │
        ▼
[MQTT Broker - Mosquitto :1883]  ← pusat pesan
        │
   ┌────┴────┐
   ▼         ▼
[python/    [Node-RED :1880]
 bridge.py]  - Subscribe sensor/suhu → tampilkan realtime
  MQTT →     - Tombol AC ON/OFF → publish control/ac
  InfluxDB   - Query InfluxDB → tampilkan history grafik
        │
        ▼
[InfluxDB :8087]  ← time-series database
  measurement: suhu_ruangan
  fields: suhu, ac_on
  tags: status_ac, lokasi