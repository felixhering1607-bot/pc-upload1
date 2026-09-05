@echo off
REM ============================================================
REM Installiert den PC-Client (nur den PC-Client!) unter Windows.
REM Vorher: Python 3.10+ installieren (https://python.org) und
REM beim Setup "Add Python to PATH" ankreuzen.
REM ============================================================

cd /d "%~dp0pc-client"

echo Erstelle virtuelle Umgebung...
python -m venv venv

echo Aktiviere virtuelle Umgebung und installiere Abhaengigkeiten...
call venv\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt

if not exist ".env" (
    echo Erstelle .env aus .env.example - bitte danach anpassen!
    copy .env.example .env
)

echo.
echo ============================================================
echo Fertig! Naechste Schritte:
echo  1. Oeffne pc-client\.env und trage BACKEND_URL, DEVICE_TOKEN
echo     und PC_DOWNLOAD_DIR ein.
echo  2. Teste den Client manuell mit:
echo       venv\Scripts\activate.bat
echo       python client.py
echo  3. Fuer automatischen Start mit Windows: Lege eine Verknuepfung
echo     dieser Datei (oder einer .vbs-Startdatei, siehe README) in
echo     den Autostart-Ordner:
echo       shell:startup
echo ============================================================
pause
