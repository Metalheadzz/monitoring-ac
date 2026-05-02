@echo off
echo ============================================================
echo   MONITORING SUHU AC - Startup Script
echo ============================================================
echo.

echo [1/3] Menjalankan Mosquitto dan Node-RED via Docker Compose...
docker compose up -d --build
if %errorlevel% neq 0 (
    echo [ERROR] Docker Compose gagal! Pastikan Docker Desktop berjalan.
    pause
    exit /b 1
)

echo.
echo [2/3] Menunggu container siap (15 detik)...
timeout /t 15 /nobreak >nul

echo.
echo [3/3] Menginstall dependencies Python...
cd python
pip install -r requirements.txt
cd ..

echo.
echo ============================================================
echo   SEMUA SIAP! Buka terminal baru untuk menjalankan Python:
echo   Menjalankan Semua Layanan Python (API, Bridge, Simulator):
echo     cd python
echo     python run_all.py
echo.
echo   Web Dashboard Premium (Vite + Flask):
echo     http://127.0.0.1:5000/
echo.
echo   Dashboard Node-RED:
echo     http://localhost:1880/ui
echo.
echo   Node-RED Editor (untuk lihat flow):
echo     http://localhost:1880
echo ============================================================
echo.
pause
