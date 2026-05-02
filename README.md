Smart AC Monitoring System (Multi-Room)



\#Persyaratan Sistem

pastikan sudah ter-install:

\- \[Docker Desktop]

\- \[Python 3.10+]

\- \[Node.js]

\- Git 



\#Konfigurasi InfluxDB

jalankan perintah di terminal untuk membuat InfluxDB secara otomatis:



docker run -d -p 8087:8086 --name influxdb2 -e DOCKER\_INFLUXDB\_INIT\_MODE=setup -e DOCKER\_INFLUXDB\_INIT\_USERNAME=admin -e DOCKER\_INFLUXDB\_INIT\_PASSWORD=admin12345 -e DOCKER\_INFLUXDB\_INIT\_ORG=myorg -e DOCKER\_INFLUXDB\_INIT\_BUCKET=mybucket -e DOCKER\_INFLUXDB\_INIT\_ADMIN\_TOKEN=yr3tJGXch-qnosHeVmts9IEPe0FPn9ptcLMM1H4jFA-CTMaZHJ8vGpTrIInLuNYr\_IP2FMJ3mm0DXIp72-P7vw== influxdb:2.7





\#Jalankan Mosquitto (MQTT) \& Node-RED

docker-compose up -d



\#Jalankan Backend (API)

pip install paho-mqtt flask influxdb-client flask-cors

python api.py



\#Jalankan Simulator AC
python simulator.py



\#Jalankan Tampilan Web Dashboard (Frontend)

arahkan ke folder `frontend`:

npm install

npm run dev



\#Cara Mengakses Aplikasi

Setelah semua langkah di atas berjalan, buka Browser Anda (Chrome/Edge):



\- Dashboard Utama (Website): `http://localhost:5173`

&#x20; - Login Username: `admin`

&#x20; - Login Password: `admin12345`

\- Node-RED Editor (Backend Flow): `http://localhost:1880`

