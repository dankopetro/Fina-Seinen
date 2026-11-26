# AGENTS.md — Fina Ergen (Arquitectura Universal Adaptativa)

Este documento sirve como guía técnica, arquitectónica y de contexto para cualquier agente o desarrollador que trabaje en **Fina Ergen** (tanto en esta base **Lite** de laboratorio como en el repositorio principal / nueva versión unificada).

---

## 1. Visión y Objetivo del Proyecto

**Fina Ergen** es un asistente de voz modular, offline-first, multilingüe y domótico para escritorio Linux (con proyección multiplataforma).

### Cambio de Paradigma: De dos ramas ("Principal" vs "Lite") a un Solo Instalador Adaptativo
En lugar de mantener dos versiones separadas, **Fina debe distribuirse en un único paquete universal** que, al instalarse y arrancar en cualquier PC o notebook (armada o de marca, en cualquier idioma del mundo), **detecte automáticamente su hardware real** y active los motores óptimos para esa máquina — permitiendo además al usuario ajustar o forzar su perfil manualmente desde la UI.

> Documento maestro portable con el plan completo, matriz de perfiles, reemplazos tecnológicos y roadmap de migración: [docs/PLAN_ARQUITECTURA_ADAPTATIVA.md](docs/PLAN_ARQUITECTURA_ADAPTATIVA.md).

### Hardware Mínimo de Referencia (Baseline)
Equipo real de prueba en red local (`danko@192.168.0.200`, host `petro`):
- **CPU:** Intel Core i3-3227U @ 1.90 GHz (Ivy Bridge 3ra Gen, 2 núcleos / 4 hilos, 800–1900 MHz, **sin AVX2/FMA**, solo AVX).
- **RAM:** 7.6 GiB totales (DDR3).
- **GPU:** Intel HD Graphics 4000 integrada (sensible a `backdrop-blur`, transparencia X11 y Canvas a 60 FPS).
- **SO / Runtime:** Linux Mint 22.3 (base Ubuntu 24.04) / Kernel 6.8 / Python 3.12.

Cualquier arquitectura nueva debe funcionar fluida desde este piso hacia arriba (notebooks modernos, desktops sin GPU dedicada, y estaciones con GPU NVIDIA/AMD).

---

## 2. Arquitectura General

El sistema corre dividido en tres capas coordinadas:

1. **Frontend / Shell de Escritorio (`src/` + `src-tauri/`):**
   - **Tauri v2** (Rust en [src-tauri/src/lib.rs](src-tauri/src/lib.rs)) + **Vue 3** + **Tailwind/Vite** ([src/App.vue](src/App.vue)).
   - Al arrancar, Rust lanza el sidecar universal `brain` ([src-tauri/binaries/brain-x86_64-unknown-linux-gnu](src-tauri/binaries/brain-x86_64-unknown-linux-gnu)).
   - La UI debe adaptar FPS del avatar ([src/components/FinaAvatar.vue](src/components/FinaAvatar.vue)), efectos `backdrop-blur`, transparencia y frecuencias de polling según el perfil de hardware recibido desde el backend.
2. **Backend REST (`fina_api.py`):**
   - Servidor **FastAPI + Uvicorn** en `0.0.0.0:18000` (puerto reservado `18000`).
   - Expone estado (`/api/state`), comandos (`/api/command`), auth de respaldo (`/api/auth/password`), settings, contactos, plugins, migración y perfil de hardware.
3. **Cerebro de Voz, IA e Intenciones (`main.py`, `utils.py`, `intent_classifier.py`):**
   - **VAD + Wake Word (Objetivo):** `Silero VAD` (ONNX) como compuerta previa de silencio + detector de wake word (`openWakeWord` / `sherpa-onnx` KWS).
   - **STT (Escucha):** `Vosk Small` (~45 MB) en baseline legacy / `sherpa-onnx` (`Zipformer` / `SenseVoice`) o `Moonshine` / `faster-whisper` en hardware moderno.
   - **TTS (Voz):** `Piper` en modo persistente en memoria (`low`/`medium`) para baseline, o `kokoro-onnx` (`Kokoro-82M`: `ef_dora`, `em_alex`, etc.) en CPUs modernas.
   - **Clasificador de Intenciones:** [intent_classifier.py](intent_classifier.py) sobre `intents-<lang>.json` + `~/.config/Fina/custom_intents.json` + reglas deterministas rápidas. **Objetivo inmediato:** migrar de `sentence-transformers` + `torch` a **TF-IDF + `rapidfuzz`** o **`Model2Vec`** (`numpy` puro, sin PyTorch).
   - **Biometría:** Huella (`fprintd`) + contraseña PAM en [auth/fingerprint_auth.py](auth/fingerprint_auth.py); voz vía **`sherpa-onnx` Speaker ID** (CAM++/TitaNet ONNX, reemplazando a `resemblyzer` + `torch` de [auth/voice_auth.py](auth/voice_auth.py)).
   - **SLM Local Opcional (`llama.cpp`):** Modelos cuantizados (`Q4_K_M`) según RAM/CPU/GPU (`SmolLM2-360M` / `Qwen2.5-0.5B` bajo demanda en 8 GB RAM hasta `Qwen3-3B/4B` en equipos con 16+ GB / dGPU) para conversación libre, resúmenes y tool calling, manteniendo `lang.json` estático para UI.
   - **Plugins Modulares:** [plugin_manager.py](plugin_manager.py) y [fina_plugin_integration.py](fina_plugin_integration.py) descubren plugins en `plugins/` (`biometria`, `system`, `web_apps`) y `~/.config/Fina/plugins/`, comunicándose vía eventos **UDP en `127.0.0.1:13333`**.

### Rutas y Convenciones Críticas
- **Configuración de usuario persistente:** `~/.config/Fina/` (respetando `$XDG_CONFIG_HOME/Fina`), incluyendo `settings.json`, `config.py`, `contacts.json`, `custom_intents.json`, `model/`, `voice_models/`, `plugins/`, `Logs/`, `venv/`.
- **Prioridad de configuración:** UI (`settings.json`) > `config.py` de usuario > `config.py` interno (`utils.get_unified_config`).
- **Idiomas soportados actualmente:** `es`, `en`, `fr`, `de`, `ja`, `zh`, `pt` (`intents-*.json`, `lang.json`, `modismos.json`), con fallback automático a `en` y descarga modular bajo demanda.

---

## 3. Estado Actual de esta Carpeta (2026)

### Ya implementado (26/04/2026)
- `productName` en [src-tauri/tauri.conf.json](src-tauri/tauri.conf.json) configurado como `"Fina-Ergen Lite"` v3.6.0 y `.deb` generado.
- Rutas de recursos para `Fina-Ergen Lite` y `fina-ergen-lite` agregadas en `brain-x86_64-unknown-linux-gnu` y `utils.py`.
- `resemblyzer` deshabilitado en [auth/voice_auth.py](auth/voice_auth.py) (`HAS_RESEMBLYZER = False`), manteniendo huella (`fprintd`) y contraseña.
- Reducción de polling en [src/App.vue](src/App.vue) y [main.py](main.py), eliminación de la mayoría de `backdrop-blur`, y Vosk restringido a modelos `small`.

### Deuda técnica prioritaria (a resolver para converger al núcleo universal)
1. [intent_classifier.py](intent_classifier.py) sigue cargando `sentence-transformers` + `torch` (`paraphrase-multilingual-MiniLM-L12-v2`).
2. [requirements.txt](requirements.txt) y [brain-x86_64-unknown-linux-gnu](src-tauri/binaries/brain-x86_64-unknown-linux-gnu) todavía verifican e instalan `torch`, `resemblyzer` y `openai-whisper`.
3. [src/components/FinaAvatar.vue](src/components/FinaAvatar.vue) sigue corriendo Canvas a 60 FPS continuos con `createRadialGradient` por partícula, y quedan `backdrop-blur` en [src/App.vue](src/App.vue#L3323) y [src/components/WeatherModule.vue](src/components/WeatherModule.vue#L3).
4. [utils.py](utils.py) ejecuta `piper` vía `subprocess.run(..., shell=True)` en cada frase y vuelve a loguear rescate de modelo cada vez que falta `es_MX-ald-medium.onnx`; además [main.py](main.py#L800) sigue pasando `return_audio=True` incluso sin Voice ID activo.
5. Falta implementar el módulo detector de hardware (`hardware_profiler.py`) y el gestor limpio de modelos bajo demanda (`model_manager.py`).

---

## 4. Reglas Innegociables de Diseño para Ambas Ramas

- **Cero PyTorch en el instalador base:** El runtime principal de inferencia debe basarse en **`ONNX Runtime` + `numpy` / `scikit-learn` + `llama.cpp` (opcional/modular)**.
- **Adaptación automática sin suposiciones de marca:** Detectar capacidades reales (CPU flags `avx`/`avx2`, núcleos físicos, RAM libre, VRAM/Vulkan/CUDA, tipo de sesión X11/Wayland, batería, espacio en disco, locale del SO).
- **Descarga modular por idioma y perfil:** El `.deb`/`.AppImage` base debe ser liviano; los modelos de voz/STT/SLM se descargan solo según perfil + idioma del usuario, con verificación y limpieza de obsoletos.
- **Compatibilidad total hacia atrás:** Preservar `detect_intent(text, confidence_threshold)` -> `(intent, confidence)`, API `:18000`, UDP `:13333`, esquema `~/.config/Fina/` y fallback de autenticación por contraseña/huella.
- **Verificación real en baseline:** Todo cambio estructural debe medirse en `danko@192.168.0.200` (RSS RAM, %CPU en `idle`, latencia fin-de-voz -> audio TTS, y tamaño total en disco).
