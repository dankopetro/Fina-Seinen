# 🛠️ Guía de Creación de Plugins para Fina Seinen

Crear un plugin para Fina es muy sencillo gracias a su arquitectura modular. Solo necesitas una carpeta con el nombre de tu plugin y dos archivos básicos.

## 📂 Estructura recomendada
```text
nombre-del-plugin/
├── plugin.yaml       # Definición de comandos e intenciones
├── tu_script.py      # Lógica del plugin (puede ser cualquier lenguaje)
├── requirements.txt  # (Opcional) Dependencias de Python
└── README.md         # (Opcional) Documentación para la comunidad
```

## 1. El archivo `plugin.yaml`
Es el cerebro del plugin. Aquí defines qué frases debe entender Fina y qué comando debe ejecutar.

```yaml
name: "Mi Super Plugin"
version: "1.0.0"
description: "Controla algo asombroso"
main: "mi_script.py"
enabled: true
priority: 50
intents:
  - name: "accion_personalizada"
    patterns:
      - "haz lo mío"
      - "ejecuta mi accion"
    response: "Claro, ejecutando tu acción ahora."
    action: "python3 mi_script.py --run"
```

## 2. El Script de Lógica
Fina simplemente ejecuta el comando que pongas en `action`. Puedes recibir parámetros dinámicos usando llaves `{}`.

Ejemplo básico de `mi_script.py`:
```python
import sys
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--run', action='store_true')
args = parser.parse_args()

if args.run:
    print("LOG: Acción ejecutada con éxito")
    # Aquí va tu código (control IoT, API, etc.)
```

## 🚀 Cómo publicarlo
1. Sube tu carpeta al repositorio de GitHub: `Fina-Plugins-Market`.
2. Envía un Pull Request.
3. ¡Tu plugin aparecerá en el Fina Market oficial!
