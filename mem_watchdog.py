#!/usr/bin/env python3
import time
import psutil
import os
import subprocess
import sys

THRESHOLD = 92.0  # Límite de RAM
PROCESS_NAMES = [
    "fina-seinen", "seinen_brain.py", "monitor_seinen.py", "main.py", "fina_api.py",
    "streamer.py", "scrcpy", "ffmpeg", "npm", "node", "vite"
]

def kill_all():
    print(f"\n🚨 ALERTA: Memoria crítica detectada (> {THRESHOLD}%). Matando procesos...")
    # Matar agresivamente
    for proc in PROCESS_NAMES:
        subprocess.run(f"pkill -9 -f {proc}", shell=True)
    print("✅ Sistema protegido. Procesos terminados.")
    sys.exit(1)

def main():
    print(f"🛡️ Watchdog activo. Límite RAM: {THRESHOLD}%")
    try:
        while True:
            # Obtener uso de RAM en porcentaje
            mem = psutil.virtual_memory().percent
            
            if mem > THRESHOLD:
                kill_all()
            
            # Chequeo cada 2 segundos
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("🛡️ Watchdog desactivado.")

if __name__ == "__main__":
    main()
