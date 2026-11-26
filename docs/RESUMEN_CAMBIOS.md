# Resumen de Cambios - Sesión Fina

**Fecha:** 05 de Diciembre de 2025
**Estado:** ✅ Implementado y Probado

## 1. 📺 Control de TV (ADB)
- **Funciones:** `turn_on_tv`, `turn_off_tv`
- **Mejoras:** 
  - Soporte multi-IP (192.168.0.11 / .10)
  - Auto-recuperación (reinicio de servidor ADB)
  - Verificación de conexión antes de enviar comandos

## 2. 🔐 Experiencia de Usuario (UX)
- **Autenticación:** Feedback de voz paso a paso en `fingerprint_auth.py`.
- **Noticias:** Ahora son opcionales. Fina pregunta antes de leerlas.

## 3. 🎤 Comandos de Voz y Personalidad
- **Nuevos nombres:** "Fina", "bebe", "nena", "dora", "loquita", "compu".
- **Despedida:** Respuestas aleatorias ("Chau fiera", "Que te garue finito", etc.).
- **Corrección:** El modo "dormir" ahora escucha en español para poder despertar correctamente.

## 4. 🌦️ Clima Mejorado
- **Sensación Térmica:** Incluida en el reporte actual.
- **Mañana:** Nuevo comando "¿Cómo estará mañana?".
- **Lluvia:** Nuevo comando "¿Cuándo va a llover?" (busca en los próximos 5 días).

## 5. 🎵 Control Multimedia (Audacious)
- **Comandos:** 
  - "Pausar música"
  - "Siguiente canción"
  - "Bajar volumen"
  - "Parar música" (mejorado con `audtool`)

---
**Archivos modificados:**
- `main.py`
- `utils.py`
- `intents.json`
- `auth/fingerprint_auth.py`
- `scripts/tv_power.py`
- `scripts/tv_off.py`

---

## Sesión 10 de Diciembre de 2025 – Panel de Configuración y Autodetección

### 1. 🛠️ Nuevo panel de configuración (Flet)

- **Archivo:** `fina_config_panel.py` (nuevo)
- **Descripción:** Panel gráfico basado en Flet para configurar Fina sin editar archivos a mano.
- **Pestañas:**
  - **TVs:**
    - Hasta 4 TVs con: Nombre, IP, MAC, casilla *Activa* y casilla *Principal*.
    - Cambios guardados en `fina_settings.json` (campo `tvs`).
    - Lógica para asegurar que, si hay una TV marcada como principal, solo una quede con `primary: true`.
  - **APIs / Paths:**
    - Edición visual de claves API y rutas.
    - Botón *Importar desde config.py* para traer valores actuales.
    - Botón *Guardar en JSON* (escribe en `fina_settings.json`).
    - Botón *Guardar también en config.py* (actualiza asignaciones en `config.py`).
  - **Canales:**
    - Carga los canales desde `channels.json` y permite marcar favoritos.
    - Sección de "Canales personalizados" (nombre + número), almacenados en `fina_settings.json` (`channels.custom`), manteniéndolos **separados** de `channels.json`.
  - **Apps TV:**
    - Mapa entre nombres amigables (`"youtube"`, `"netflix"`, etc.) y paquetes Android (`"com.google.android.youtube.tv"`, etc.).
    - Puede editarse a mano y se guarda en `fina_settings.json` (`tv_apps`).

### 2. 🔧 Centralización de configuración

- **Archivo:** `fina_settings.json` (nuevo)
- **Contenido principal:**
  - `tvs`: lista de TVs con `name`, `ip`, `mac`, `enabled`, `primary`.
  - `apis`: claves API (GitHub, OpenWeather, NewsAPI, OpenAI, ElevenLabs, Unsplash, Runway, etc.).
  - `paths`: rutas internas (modelos de voz, modelo Vosk, contactos, imagen conocida).
  - `channels`: favoritos y canales personalizados (`favorites`, `custom`).
  - `tv_apps`: mapa nombre amigable → paquete Android.

### 3. 📺 Autodetección de canales

- **Archivo:** `fina_config_panel.py` (pestaña *Canales*).
- **Botón:** `Escanear canales desde la TV`.
- **Funcionamiento:**
  - Usa ADB para consultar la base de datos de canales en la TV (`content://android.media.tv/channel`).
  - Extrae `display_number` y `display_name`.
  - Agrega nuevas entradas a `channels.json` (sin pisar las ya existentes).
  - Refresca la lista de canales en el panel.
  - Muestra mensajes de estado en verde (escaneando, sin TV, error ADB, sin canales, canales agregados), que se borran automáticamente a los 5 segundos.

### 4. 📦 Autodetección de apps de TV

- **Archivo:** `fina_config_panel.py` (pestaña *Apps TV*).
- **Botón:** `Detectar apps en la TV`.
- **Funcionamiento:**
  - Usa ADB (`pm list packages`) para listar paquetes instalados en la TV.
  - Filtra por palabras clave (`tv`, `live`, `input`, `channel`, `launcher`, `home`, `iptv`, `m3u`).
  - Sugiere nuevas entradas en `tv_apps` evitando duplicados, con nombres amigables generados a partir del nombre del paquete.
  - Muestra mensajes de estado en verde (detectando, sin TV, error ADB, cantidad de apps sugeridas) que se borran tras 5 segundos.

### 5. 🔁 Integración con lógica de TV existente

- **Archivo:** `scripts/tv_on.py`
  - Se reemplazó la lista fija `TARGETS` por la función `load_targets()` que lee TVs habilitadas desde `fina_settings.json` (máx. 4), con fallback a las IPs originales si no hay configuración.

- **Archivo:** `utils.py`
  - `_get_connected_tv_ip()` ahora obtiene las IPs de TVs habilitadas desde `fina_settings.json`, con fallback a las IPs originales.
  - `tv_open_app_cmd()` ahora carga el mapa de apps desde `fina_settings.json` (`tv_apps`), con un mapa por defecto si no hay datos.

### 6. 📄 Documentación y manual

- **Archivo:** `MANUAL_DE_USUARIO.md`
  - Nueva sección "Panel de Configuración de Fina (Opcional)" que explica:
    - Cómo lanzar `fina_config_panel.py`.
    - Las pestañas (TVs, APIs/Paths, Canales, Apps TV).
    - El funcionamiento general de los botones de autodetección.

- **Archivo:** `NUEVAS_FUNCIONES.md`
  - Se agregó una entrada con fecha **2025-12-10** describiendo el panel de configuración y la autodetección de TV (canales y apps), junto a los archivos afectados.

- **Archivo:** `scripts/generate_manual.py`
  - Se añadió la subsección **3.1 Panel de configuración de Fina (opcional)** al PDF generado, describiendo el panel, sus pestañas y cómo abrirlo.
  - Se generó nuevamente `Manual_Usuario_Fina.pdf` para reflejar estos cambios.

---

## Sesión 04 de Enero de 2026 – Centro de Comando Moderno y Biometría Inmersiva

### 1. 🌐 Nuevo Centro de Comando Web (Fina Dashboard)
- **Tecnología**: FastAPI (Backend) + Vue.js 3 / Tailwind CSS (Frontend).
- **Diseño Inmersivo**: 
    - Fullscreen con avatar traslúcido y halo dinámico reactivo al audio.
    - Jerarquía visual mejorada: Bienvenido arriba, Soy Fina abajo.
    - Saludo personalizado con mayúsculas corregidas: "Bienvenido Claudio".
- **Monitor de Procesos**: Píldora de estado dinámica que indica la acción actual de Fina.

### 2. 🔐 Autenticación Biométrica Visual
- **Overlay Pantalla Completa**: Animación de escáner neón durante la autenticación.
- **Integración Backend**: Conexión con `fprintd` y soporte para `fprintd-verify`.
- **Panel de Gestión**: Pestaña dedicada para verificar estado y enrollar nuevas huellas.

### 3. 📺 Gestión Avanzada de TV Android
- **Detección Automática**: Endpoint para escanear dispositivos ADB activos en la red.
- **Sincronización de Canales**: Botón para leer base de datos de canales del sintonizador.
- **Control de Apps**: Buscador de paquetes instalados en la TV con capacidad de eliminar atajos.

### 4. 🛠️ Seguridad y UI/UX
- **Visibilidad API Keys**: Botón de "ojo" para alternar visibilidad de claves sensibles.
- **Mecanismo Auto-Apagado**: Implementación de `navigator.sendBeacon` y evento `pagehide` para cierre automático del servidor.
- **Localización**: Soporte completo para el idioma del sistema y traducciones dinámicas.

**Archivos afectados:**
- `fina_api.py` (Endpoints de escaneo, shutdown y estado).
- `static/index.html` (Reescritura total de la interfaz).
- `auth/fingerprint_auth.py` (Soporte biométrico).
- `run_web_panel.sh` (Script de lanzamiento).

---

## Sesión 05 de Febrero de 2026 – Estabilización RC v2.8.7
**Estado:** 🚀 Versión Candidata a Lanzamiento (RC) - Altamente Estable

### 1. 🧬 ADN y Voz (Biometría)
- **Corrección Crítica**: Arreglado el bug de `numpy` que convertía mal el audio. Ahora Vosk y la Biometría trabajan con datos cristalinos.
- **Confianza**: El reconocimiento de Claudio pasó de ser errático a ser instantáneo (Confianza > 0.9).

### 2. 🔌 Plugins y Cortesía
- **TV Modular**: Implementado control modular. Fina ahora verifica si la TV está conectada antes de dar órdenes.
- **Feedback Verbal**: Todos los plugins (Clima, TV, Dashboard) ejecutan y confirman verbalmente la acción de inmediato.

### 3. 🧹 Purga Atómica (Janitor)
- **Janitor.py**: Nuevo sistema de limpieza en Python que no deja procesos huérfanos.
- **Liberación de Terminal**: Se acabó la terminal "muerta". El comando `reset` y `stty sane` devuelven el control al usuario al 100%.

### 4. 📺 Mejoras de Inicio
- **Silencio al Arranque**: Eliminado el ruido molesto del motor TTS al despertar.
- **Radar de Dispositivos**: Al arrancar, Fina informa si la televisión está enlazada o fuera de línea de forma proactiva.

---
**Próximo Proyecto:** Desarrollo de **Fina-Seinen** (Adolescente). Interfaz renovada, IA más fluida y expansión del ecosistema.
