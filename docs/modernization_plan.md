# Plan de Modernización para Fina‑Lite

**Objetivo:** Actualizar la base de código de Fina‑Lite usando un empaquetado Python moderno, inferencia ligera de ML y una mejor experiencia de desarrollo, sin perder la funcionalidad existente.

## Lista de pasos
1. **Adoptar `uv` para la gestión de dependencias** – reemplazar `requirements.txt` por un `pyproject.toml` y generar un archivo de bloqueo con `uv lock`.
2. **Sustituir la pila pesada de ML** – cambiar `torch`, `sentence‑transformers`, `resemblyzer` y `openai‑whisper` por alternativas basadas en ONNX‑Runtime (p. ej., `sentence‑transformers[onnx]` o `transformers[onnx]`, `whispercpp` en lugar de `openai‑whisper`).
3. **Refactorizar los módulos de autenticación** – hacer que las importaciones biométricas sean opcionales y controlarlas mediante banderas de características.
4. **Modularizar I/O y plugins** – mover los requisitos de cada plugin a su propio `requirements.txt` y dejar en el archivo central solo las dependencias esenciales.
5. **Actualizar FastAPI** – fijar versiones mínimas `fastapi>=0.115` y `uvicorn>=0.30`.
6. **Crear script de entorno virtual** – `setup.sh` que cree un `.venv` usando `uv venv` e instale las dependencias bloqueadas.
7. **Añadir configuración CI** – workflow de GitHub Actions que ejecute linting con `ruff`, comprobación de tipos con `mypy` y pruebas unitarias.
8. **Actualizar la documentación** – reflejar los nuevos pasos de instalación y gestión de dependencias.
9. **Ejecutar una comprobación de importación** – asegurarse de que la aplicación se inicia sin `ImportError` en el nuevo entorno.
10. **(Opcional) empaquetar con `shiv` o `pyoxidizer`** – generar un ejecutable autónomo.

### Próximo paso inmediato
Crear un `pyproject.toml` mínimo y generar el lockfile con `uv`.