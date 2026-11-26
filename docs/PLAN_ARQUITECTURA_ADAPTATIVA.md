# Plan Maestro: Fina Ergen — Arquitectura Universal Adaptativa

> **Objetivo:** Unificar las variantes *Principal* y *Lite* en **un único instalador universal** que funcione en cualquier PC o notebook (armada o de marca, en cualquier idioma y región), detectando automáticamente las capacidades reales del hardware al arrancar para elegir los motores más rápidos, livianos y precisos que esa máquina pueda ejecutar sin degradar la experiencia.

---

## 1. Principios de Diseño

1. **Un solo código fuente, un solo instalador (`.deb` / `.rpm` / `.AppImage`):**
   - El paquete base contiene únicamente la app Tauri + backend Python ligero + binarios portables mínimos (`piper`, etc.) sin modelos pesados embebidos (~30–45 MB).
   - Al primer arranque (y ante cambios de hardware o idioma), Fina perfila la máquina y descarga **exclusivamente** los modelos compatibles con su nivel de hardware e idioma.
2. **Cero PyTorch / TensorFlow / Dlib en el núcleo:**
   - Todo el procesamiento de audio, biometría básica y embeddings en el core migra a **`ONNX Runtime` + `numpy` + `scikit-learn`**, eliminando ~1.5–3 GB de entorno Python y cientos de MB de RAM innecesaria.
3. **Piso mínimo garantizado (Baseline 2013):**
   - Toda funcionalidad esencial (escucha por voz, intenciones, respuestas habladas, UI, plugins IoT, auth por huella/contraseña) debe correr fluida en una máquina equivalente a:
     - **CPU:** Dual-core / 4 hilos @ 1.9 GHz **sin AVX2** (ej. Intel Core i3-3227U Ivy Bridge).
     - **RAM:** 8 GB DDR3 (o incluso modo emergencia 4 GB).
     - **GPU:** Integrada antigua (ej. Intel HD 4000) o sin aceleración 3D moderna.
4. **Escalado automático hacia arriba + control manual:**
   - En máquinas modernas (AVX2/AVX-512, 16+ GB RAM, GPU NVIDIA/AMD/Intel Arc), Fina activa automáticamente motores neuronales superiores (`kokoro-onnx`, `sherpa-onnx` SenseVoice/Zipformer, `Model2Vec`, biometría de voz ONNX, `llama.cpp` residente, UI fluida).
   - En **Ajustes -> Sistema / Rendimiento**, el usuario siempre puede ver el perfil detectado y cambiar entre `Auto` o forzar `Eco (Lite)` / `Balanceado` / `Ultra`.

---

## 2. Detector de Hardware Universal (`hardware_profiler.py`)

El detector **no depende de marcas ni listas de modelos comerciales**; mide capacidades objetivas del sistema operativo y hardware en < 100 ms al arrancar:

### Señales a inspeccionar
| Dimensión | Cómo medirlo en Linux (portable) | Para qué decide |
| :--- | :--- | :--- |
| **CPU Arquitectura & SIMD** | `platform.machine()`, `/proc/cpuinfo` (`avx`, `avx2`, `fma`, `avx512f`, `neon`) | Decide si `llama.cpp` / `sherpa-onnx` / `faster-whisper` pueden usar kernels AVX2 rápidos o deben ir a modo SSE/AVX legacy o Vosk Small. |
| **Núcleos físicos vs hilos** | `psutil.cpu_count(logical=False)` y `cpu_freq().max` | Define hilos óptimos (`threads = physical_cores`) para evitar thrashing de caché en inferencia CPU. |
| **RAM Total y Disponible** | `psutil.virtual_memory()` | Habilita o bloquea SLM local en memoria residente, modelos STT medianos/grandes y precarga de modelos. |
| **GPU / Aceleración** | `nvidia-smi` (CUDA/VRAM), `vulkaninfo` / `/sys/class/drm` (AMD/Intel Vulkan/ROCm), `glxinfo` | Decide offload a GPU en `llama.cpp` (`-ngl`) / `whisper.cpp` y si WebKitGTK soporta efectos visuales o no. |
| **Energía / Notebook** | `/sys/class/power_supply/BAT*` (`status`: Discharging/Charging) | Si está en batería, puede activar modo ahorro automático (bajar FPS de avatar, pausar SLM residente). |
| **Display / Compositor** | `$XDG_SESSION_TYPE` (`x11` vs `wayland`), compositor activo | En X11 con iGPU antigua desactiva `transparent: true` y `backdrop-blur` para evitar lag de ventana. |
| **Disco libre** | `psutil.disk_usage(CONFIG_DIR)` | Impide descargas pesadas si quedan < 2 GB libres en `~/.config/Fina`. |
| **Idioma / Región global** | `LANG`, `LC_ALL`, `FINA_LANGUAGE` | Selecciona `intents-<lang>.json`, `lang.json`, `modismos.json` y el par de modelos STT+TTS exacto para ese idioma. |

### Salida del Profiler
Guarda `~/.config/Fina/hardware_profile.json` (y lo re-evalúa si cambia CPU/RAM/GPU o versión de Fina) y expone `GET /api/system/profile` en [fina_api.py](fina_api.py) para que tanto Python como Vue ([src/App.vue](src/App.vue)) ajusten su comportamiento al instante.

---

## 3. Matriz de Perfiles Automáticos

| Capacidad / Tier | `tier_0_minimal` (Rescate ≤ 4 GB RAM) | `tier_1_eco` (Baseline: sin AVX2 o RAM ≤ 8 GB o iGPU vieja) | `tier_2_balanced` (AVX2 + 4+ núcleos + 8–16 GB RAM sin dGPU) | `tier_3_pro` (≥ 16 GB RAM + dGPU VRAM ≥ 4 GB o CPU ≥ 8 núcleos AVX2) |
| :--- | :--- | :--- | :--- | :--- |
| **VAD + Wake Word** | Botón / Push-to-talk o `Silero VAD` | `Silero VAD` ONNX + `openWakeWord` (con VAD gate) | `Silero VAD` ONNX + `openWakeWord` / `sherpa-onnx` KWS | `Silero VAD` + `openWakeWord` / `sherpa-onnx` KWS |
| **STT (Voz a texto)** | `Vosk Small` (~45 MB) | `Vosk Small` (~45 MB) o `sherpa-onnx` CTC liviano | `sherpa-onnx` (`Zipformer` / `SenseVoice` int8) o `Moonshine` | `sherpa-onnx` (`SenseVoice`) o `faster-whisper` (`small`/`medium` CUDA/Vulkan) |
| **Clasificador Intents** | Reglas + `TF-IDF` (`numpy`/`sklearn`) | `TF-IDF` + `rapidfuzz` + reglas (< 15 MB RAM, < 20 ms) | `Model2Vec` (`potion-multilingual-128M`, `numpy` puro) + reglas | `Model2Vec` + enrutamiento semántico por SLM |
| **Voice ID (Voz)** | Desactivado (Huella/Pass) | Desactivado por defecto; opcional `sherpa-onnx` (`CAM++` ONNX) | `sherpa-onnx` `SpeakerEmbeddingExtractor` (`CAM++` ONNX) | `sherpa-onnx` (`TitaNet`/`CAM++` ONNX) |
| **TTS (Síntesis voz)** | `Piper` persistente (`low`, ~15–25 MB) | `Piper` persistente en RAM (`low`/`medium`, ~20–60 MB) | `kokoro-onnx` (`Kokoro-82M`: `ef_dora`, `em_alex`) + fallback `Piper` | `kokoro-onnx` streaming (o TTS GPU avanzado) |
| **IA Local (SLM)** | Desactivado (Cloud opcional) | Desactivado residente; **bajo demanda** `SmolLM2-360M` / `Qwen2.5-0.5B` `Q4_K_M` con auto-descarga por inactividad | `Qwen3-0.6B` / `Qwen2.5-1.5B` `Q4_K_M` (`llama.cpp` lazy + unload tras N min) | `Qwen3-3B/4B` / `Gemma-3-4B` / `FunctionGemma` residente con GPU offload |
| **UI / Gráficos** | Sin Canvas (avatar SVG/PNG estático), 0 blur | Avatar Canvas capped 15–20 FPS (sin `createRadialGradient` en loop), `idle` estático, 0 `backdrop-blur`, polling espaciado | Avatar 30 FPS optimizado (sprites pre-renderizados), transiciones suaves | Avatar 60 FPS completo, efectos visuales completos |

---

## 4. Reemplazos Tecnológicos Clave (Stack Moderno 2026)

### 4.1. De `sentence-transformers` + `PyTorch` → `TF-IDF + RapidFuzz` / `Model2Vec`
- **Problema actual:** [intent_classifier.py](intent_classifier.py) importa `sentence_transformers` + `torch` para clasificar apenas ~117 intenciones (~2.350 frases en `intents-es.json`). Eso añade ~458 MB en caché HF + cientos de MB de RAM y segundos de carga.
- **Solución:**
  - Interfaz unificada `IntentEngine` manteniendo la firma exacta `detect_intent(text, confidence_threshold=0.55) -> (intent, confidence)`.
  - **`TfidfIntentEngine`** (`scikit-learn` `TfidfVectorizer` word+char n-grams + similitud coseno en `numpy` + `rapidfuzz` para tolerancia a errores STT): < 15 MB RAM, arranca en < 50 ms. Ideal para `tier_0` y `tier_1_eco`.
  - **`Model2VecIntentEngine`** (`model2vec` con `minishlab/potion-multilingual-128M`, solo depende de `numpy`, sin `torch`): embeddings estáticos multilingües ~500x más rápidos que un transformer. Ideal para `tier_2` y `tier_3`.

### 4.2. De loop continuo Vosk → `Silero VAD` + `openWakeWord`
- **Problema actual:** `main.py` mantiene `listen()` continuamente procesando audio con Vosk en estado `idle`.
- **Solución:**
  - Poner **`Silero VAD` (ONNX, ~1–2 MB, < 1 ms/chunk)** como primera puerta antes del wake word / STT. Mientras haya silencio ambiental, no se ejecuta inferencia pesada y la CPU en reposo cae por debajo del 2–5%.
  - Usar `openWakeWord` con `vad_threshold` habilitado (o `sherpa-onnx` KWS) para activar la escucha activa solo al escuchar `"Fina"`.

### 4.3. De `Resemblyzer` (`torch`) → `sherpa-onnx` Speaker Identification
- **Problema actual:** En Lite se tuvo que apagar la biometría de voz (`HAS_RESEMBLYZER = False` en [auth/voice_auth.py](auth/voice_auth.py)) porque `resemblyzer` arrastra `torch`, `librosa` y `scipy`.
- **Solución:** Migrar `VoiceAuthenticator` a **`sherpa-onnx` `SpeakerEmbeddingExtractor`** (modelos ONNX como **CAM++** o **ECAPA-TDNN**). Corre sin PyTorch, en milisegundos, y sirve tanto para Principal como opcionalmente para Lite.
- **Además:** En [main.py](main.py#L800), solo pasar `return_audio=True` a `listen()` si la biometría de voz está habilitada en el perfil activo (evita copiar buffers PCM `numpy` en cada turno).

### 4.4. De `Piper` por subproceso + ElevenLabs → `Piper` persistente + `kokoro-onnx`
- **Problema actual:** [utils.py](utils.py#L729-L740) lanza `subprocess.run("... piper ...", shell=True)` en cada frase, recargando el modelo ONNX desde disco en cada respuesta, y repite warnings si falta `es_MX-ald-medium.onnx`.
- **Solución:**
  - Resolver el modelo de voz una sola vez al iniciar (sin loguear warnings por frase) y priorizar modelos `low`/`medium` en `tier_1_eco`.
  - Mantener el motor TTS **persistente en memoria** (instancia `piper-tts` / `sherpa-onnx` `OfflineTts` o pipe continuo con `--json-input`), eliminando la latencia de arranque por frase.
  - En `tier_2` / `tier_3` (y opcional en `tier_1`), ofrecer **`kokoro-onnx` (`Kokoro-82M`, Apache 2.0)** con voces naturales multilingües (`ef_dora`, `em_alex`, `em_santa` en español; `af_*`/`am_*` en inglés, etc.), logrando calidad cercana a cloud 100% offline.

### 4.5. De diccionarios rígidos / Cloud LLM → `lang.json` estático + `llama.cpp` Adaptativo
- **UI e internacionalización ([lang.json](lang.json)):** Se mantiene estático (JSON en memoria, 0 ms, 0 latencia, sin `deep_translator` en runtime).
- **Personalidad ([modismos.json](modismos.json)) y conversación libre:**
  - En `tier_0` / `tier_1_eco` (sin SLM residente): respuestas instantáneas desde `modismos.json` adaptado al `locale` (`es_AR`, `es_MX`, `es_ES`, `en_US`, `pt_BR`, `fr_FR`, `de_DE`, `ja_JP`, `zh_CN`, etc.).
  - Cuando hay SLM local (`llama.cpp` server o `llama-cpp-python` con carga bajo demanda e `idle_timeout` de descarga): reemplaza a OpenAI/Mistral como cerebro conversacional offline, genera respuestas naturales acordes al idioma/región del usuario (via system prompt compacto) y puede resolver intenciones ambiguas o extraer parámetros JSON para plugins.
  - Si el usuario configura API keys cloud (OpenAI/Mistral), el `LLMEngine` puede escalar a nube como fallback o preferencia explícita.

### 4.6. Frontend Adaptativo (`src/` + `src-tauri/`)
- Exponer `ui_tier` (`minimal` | `eco` | `balanced` | `pro`) desde `/api/system/profile` y eventos `brain-event`.
- **[src/components/FinaAvatar.vue](src/components/FinaAvatar.vue):**
  - Pre-renderizar el brillo/partícula en un pequeño canvas offscreen (eliminar `createRadialGradient` dentro del loop de render).
  - En `eco`: reducir partículas (300 → 60) y rayos (40 → 10), cap a 15–20 FPS en `speaking`, y detener/ralentizar animación en `idle` (o usar CSS/SVG estático en `minimal`).
- **[src/App.vue](src/App.vue) y [src/components/WeatherModule.vue](src/components/WeatherModule.vue):**
  - Eliminar o condicionar dinámicamente con `:class` los últimos `backdrop-blur` y `blur-[80px]` según `ui_tier`.
  - Mantener polling de stats (`psutil`) en 30s (o bajo demanda cuando se abre la pestaña Sistema) y sin timers de 1s en UI.

---

## 5. Soporte Global de Idiomas y Gestión de Modelos (`model_manager.py`)

Para que funcione para **cualquier usuario del planeta**:
1. **Detección de idioma al primer arranque:** `FINA_LANGUAGE` > `$LC_ALL`/`$LANG` > fallback `en` (y editable en Ajustes con reinicio limpio de modelos).
2. **Catálogo centralizado (`models_manifest.json`):** Mapea `(idioma, tier)` → `{ stt_model, tts_model, intent_model, slm_model, sha256, size_mb }`.
   - Si un idioma aún no tiene modelo `kokoro-onnx`, cae limpiamente a `Piper` (que cubre decenas de idiomas) o `Vosk` / `sherpa-onnx`.
   - Si no existe `intents-<lang>.json` para un idioma exótico, usa `intents-en.json` + traducción inicial opcional o SLM router.
3. **Auto-limpieza de almacenamiento:** Al cambiar de perfil o idioma, ofrecer/purgar modelos heredados pesados que ya no corresponden al perfil activo (por ejemplo `vosk-model-es-0.42` de 2.3 GB o cachés obsoletas de HuggingFace), verificando siempre el espacio en disco antes de descargar.

---

## 6. Roadmap de Implementación (Para llevar a Fina-Ergen Principal / Nueva Versión)

### Fase 1 — Baseline y Cimientos de Perfilado
- [ ] Crear `hardware_profiler.py` con detección portable de CPU/SIMD/RAM/GPU/Batería/Display/Disco/Locale y persistencia en `~/.config/Fina/hardware_profile.json`.
- [ ] Exponer `/api/system/profile` (GET/POST para override manual `Auto | Eco | Balanceado | Pro`) en [fina_api.py](fina_api.py).
- [ ] Registrar métricas de referencia en el hardware mínimo (`i3-3227U`, 8 GB RAM): RAM RSS total, %CPU en `idle`, tiempo hasta `"SISTEMA LISTO"` y latencia fin-de-voz → inicio de audio.

### Fase 2 — Limpieza de PyTorch y Nuevo Pipeline de Intenciones
- [ ] Refactorizar [intent_classifier.py](intent_classifier.py) con arquitectura de adaptadores (`TfidfIntentEngine` + `Model2VecIntentEngine`), conservando reglas deterministas, `custom_intents.json` y el contrato `detect_intent()`.
- [ ] Crear script de evaluación automática sobre todos los `intents-*.json` para validar precisión (> 95% en intents directos) y tiempo de arranque (< 100 ms).
- [ ] Limpiar [requirements.txt](requirements.txt) (core sin `torch`, `sentence-transformers`, `transformers`, `resemblyzer`, `openai-whisper`, `face-recognition`) y actualizar [src-tauri/binaries/brain-x86_64-unknown-linux-gnu](src-tauri/binaries/brain-x86_64-unknown-linux-gnu) para que el primer arranque tome segundos en lugar de 10–20 minutos compilando C++.

### Fase 3 — Motor de Audio Moderno (VAD + STT + TTS + Voice ID)
- [ ] Integrar `Silero VAD` ONNX delante de `listen()` en [utils.py](utils.py) para llevar la CPU en reposo (`idle`) a < 5%.
- [ ] Evitar `return_audio=True` en [main.py](main.py) cuando la biometría de voz esté desactivada.
- [ ] Mantener `Piper` persistente en memoria en `tier_1_eco` (eliminando el `subprocess.run` por frase y los warnings repetidos de modelo faltante) e integrar `kokoro-onnx` para `tier_2`/`tier_3`.
- [ ] Migrar [auth/voice_auth.py](auth/voice_auth.py) a `sherpa-onnx` `SpeakerEmbeddingExtractor` (ONNX puro) y unificar `STTEngine` (`Vosk Small` / `sherpa-onnx` Zipformer-SenseVoice).

### Fase 4 — Gestor de Modelos + SLM Local Opcional (`llama.cpp`)
- [ ] Implementar `model_manager.py` con manifiesto por idioma/perfil, barra de progreso en UI, verificación de espacio en disco y limpieza de modelos pesados obsoletos.
- [ ] Implementar `LLMEngine` unificado (`llama.cpp` local con auto-unload por inactividad + soporte API cloud existente) eligiendo `SmolLM2-360M` / `Qwen2.5-0.5B` en `tier_1` (bajo demanda), `Qwen3-0.6B/1.5B` en `tier_2` y `3B/4B` en `tier_3`.

### Fase 5 — Frontend Adaptativo (`src/` + `src-tauri/`)
- [ ] Consumir `ui_tier` en [src/App.vue](src/App.vue) para activar/desactivar blurs, transiciones y frecuencia de polling.
- [ ] Optimizar [src/components/FinaAvatar.vue](src/components/FinaAvatar.vue) con sprites pre-renderizados, FPS adaptativo según estado (`idle` vs `speaking`) y `ui_tier`.
- [ ] Remover `backdrop-blur` restantes en [src/App.vue](src/App.vue#L3323) y [src/components/WeatherModule.vue](src/components/WeatherModule.vue#L3) en modos `minimal`/`eco`, y añadir selector de perfil (`Auto` / manual) en Ajustes.

### Fase 6 — Empaquetado Universal y Validación Multi-Equipo
- [ ] Unificar `productName` y rutas en [src-tauri/tauri.conf.json](src-tauri/tauri.conf.json), `brain` y `utils.py` bajo el nombre definitivo de la versión unificada.
- [ ] Generar instaladores (`.deb`, `.rpm`, `.AppImage` comprimido XZ) y validar en al menos:
  1. **Equipo Legacy Baseline:** `i3-3227U` / 8 GB RAM / HD 4000 / Linux Mint 22.3 (`192.168.0.200`).
  2. **Equipo Moderno:** CPU con AVX2 / 16+ GB RAM / con o sin GPU dedicada.
  3. **Múltiples idiomas:** al menos `es`, `en`, `pt` (y fallback seguro para idiomas no listados).

---

## 7. Checklist Rápido para Migrar al Repositorio Principal

Si llevás este plan a la carpeta principal de **Fina-Ergen** (o un nuevo repo/versión):
1. Copiar [AGENTS.md](../AGENTS.md) y este archivo [docs/PLAN_ARQUITECTURA_ADAPTATIVA.md](PLAN_ARQUITECTURA_ADAPTATIVA.md).
2. No duplicar repositorios ni ramas `lite` vs `full`: implementar `hardware_profiler.py` + adaptadores desde la Fase 1 sobre el repo unificado.
3. Mantener intactos los contratos que consumen los plugins del Market ([plugin_manager.py](../plugin_manager.py), [fina_plugin_integration.py](../fina_plugin_integration.py), UDP `:13333` y API `:18000`) para no romper compatibilidad con extensiones existentes.

