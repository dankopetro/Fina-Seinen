# verify_imports.py

"""Script de verificación rápida de importaciones clave.
Ejecuta este script dentro del entorno virtual para confirmar que las
dependencias principales están instaladas y pueden importarse.
"""

import sys

mods = [
    "sentence_transformers",  # ONNX version
    "transformers",
    "whispercpp",
    "onnxruntime",
    "fastapi",
    "uvicorn",
    "pydantic",
    "pyautogui",
    "sounddevice",
]

failed = []
for m in mods:
    try:
        __import__(m)
        print(f"✅ {m} importado correctamente")
    except Exception as e:
        failed.append((m, str(e)))
        print(f"❌ {m}: {e}")

if failed:
    print("\nAlgunos módulos no pudieron importarse:")
    for name, err in failed:
        print(f" - {name}: {err}")
    sys.exit(1)
else:
    print("\n✅ Todas las importaciones fueron exitosas.")
