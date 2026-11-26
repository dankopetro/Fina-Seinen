"""
hardware_profiler.py — Fina Seinen Universal Adaptive Architecture
Detecta el perfil de hardware real de la máquina y elige el tier óptimo.

Tiers:
  tier_0_minimal   → CPU muy antigua sin AVX2, <4 GB RAM (baseline Ivy Bridge)
  tier_1_eco       → CPU moderna SIN GPU dedicada, 4-8 GB RAM
  tier_2_balanced  → CPU moderna + iGPU/APU decente, 8-16 GB RAM
  tier_3_pro       → GPU dedicada NVIDIA/AMD con VRAM, 16+ GB RAM

Uso:
    from hardware_profiler import get_profile
    profile = get_profile()
    print(profile["tier"])  # "tier_1_eco"
    print(profile["recommended_tts"])  # "piper"
"""

import os
import json
import platform
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger("HardwareProfiler")

# Ruta de salida del perfil
FINA_CONFIG = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "Fina"
PROFILE_PATH = FINA_CONFIG / "hardware_profile.json"

# ─── Detección de CPU ────────────────────────────────────────────────────────

def _cpu_flags() -> set:
    """Lee /proc/cpuinfo y extrae las flags de la primera CPU."""
    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if line.startswith("flags"):
                    return set(line.split(":")[1].strip().split())
    except Exception:
        pass
    return set()

def _cpu_physical_cores() -> int:
    try:
        import psutil
        return psutil.cpu_count(logical=False) or 1
    except ImportError:
        try:
            out = subprocess.check_output(
                ["grep", "-c", "^processor", "/proc/cpuinfo"],
                stderr=subprocess.DEVNULL, text=True
            ).strip()
            return max(1, int(out) // 2)
        except Exception:
            return 1

def _cpu_max_freq_ghz() -> float:
    """Frecuencia máxima de la CPU en GHz."""
    try:
        import psutil
        freq = psutil.cpu_freq()
        if freq and freq.max > 0:
            return freq.max / 1000.0
        return freq.current / 1000.0 if freq else 1.5
    except Exception:
        pass
    try:
        # Fallback: leer desde sysfs
        p = Path("/sys/devices/system/cpu/cpu0/cpufreq/cpuinfo_max_freq")
        if p.exists():
            return int(p.read_text().strip()) / 1_000_000
    except Exception:
        pass
    return 1.5

# ─── Detección de RAM ────────────────────────────────────────────────────────

def _ram_total_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().total / (1024 ** 3)
    except ImportError:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        except Exception:
            pass
    return 4.0

def _ram_available_gb() -> float:
    try:
        import psutil
        return psutil.virtual_memory().available / (1024 ** 3)
    except ImportError:
        try:
            with open("/proc/meminfo") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        kb = int(line.split()[1])
                        return kb / (1024 ** 2)
        except Exception:
            pass
    return 2.0

# ─── Detección de GPU ────────────────────────────────────────────────────────

def _detect_gpu() -> dict:
    """
    Retorna:
      {"type": "nvidia|amd|intel|none", "vram_mb": int, "vulkan": bool,
       "cuda": bool, "rocm": bool}
    """
    result = {"type": "none", "vram_mb": 0, "vulkan": False, "cuda": False, "rocm": False}

    # NVIDIA con nvidia-smi
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            stderr=subprocess.DEVNULL, timeout=3, text=True
        ).strip().splitlines()
        if out:
            vram = sum(int(x.strip()) for x in out if x.strip().isdigit())
            result.update({"type": "nvidia", "vram_mb": vram, "cuda": True})
            return result
    except Exception:
        pass

    # AMD ROCm / VRAM via /sys
    for drm_path in Path("/sys/class/drm").glob("card*/device"):
        vendor_path = drm_path / "vendor"
        mem_path = drm_path / "mem_info_vram_total"
        try:
            vendor = vendor_path.read_text().strip()
            if vendor in ("0x1002",):  # AMD
                vram_bytes = int(mem_path.read_text().strip()) if mem_path.exists() else 0
                result.update({
                    "type": "amd",
                    "vram_mb": vram_bytes // (1024 ** 2),
                    "rocm": Path("/usr/bin/rocminfo").exists()
                })
                break
        except Exception:
            pass

    # Intel iGPU: detectar por /sys/class/drm con vendor 0x8086
    if result["type"] == "none":
        for drm_path in Path("/sys/class/drm").glob("card*/device"):
            vendor_path = drm_path / "vendor"
            try:
                if vendor_path.read_text().strip() == "0x8086":
                    result["type"] = "intel"
                    break
            except Exception:
                pass

    # Vulkan disponible?
    try:
        subprocess.check_output(["vulkaninfo", "--summary"], stderr=subprocess.DEVNULL, timeout=3)
        result["vulkan"] = True
    except Exception:
        pass

    return result

# ─── Detección de disco ──────────────────────────────────────────────────────

def _disk_free_gb(path: str = "~") -> float:
    try:
        import psutil
        return psutil.disk_usage(os.path.expanduser(path)).free / (1024 ** 3)
    except Exception:
        try:
            out = subprocess.check_output(
                ["df", "--output=avail", "-BG", os.path.expanduser(path)],
                stderr=subprocess.DEVNULL, text=True
            ).splitlines()[1].strip().rstrip("G")
            return float(out)
        except Exception:
            return 10.0

# ─── Detección de entorno ────────────────────────────────────────────────────

def _session_type() -> str:
    """x11 | wayland | tty | unknown"""
    return os.environ.get("XDG_SESSION_TYPE", "unknown").lower()

def _is_on_battery() -> bool:
    for bat in Path("/sys/class/power_supply").glob("BAT*"):
        status = bat / "status"
        try:
            return status.read_text().strip().lower() == "discharging"
        except Exception:
            pass
    return False

def _system_locale() -> str:
    for var in ("LANG", "LC_ALL", "LC_MESSAGES", "LANGUAGE"):
        v = os.environ.get(var, "")
        if v:
            return v.split("_")[0].split(".")[0].lower()
    return "es"

# ─── Lógica de Tier ──────────────────────────────────────────────────────────

def _assign_tier(flags: set, cores: int, ram_gb: float, gpu: dict, freq_ghz: float) -> str:
    """
    Asigna el tier basado en capacidades reales del hardware.
    Criterios conservadores: preferir estabilidad sobre velocidad.
    """
    has_avx2 = "avx2" in flags
    has_avx   = "avx"  in flags
    has_cuda  = gpu.get("cuda", False)
    has_rocm  = gpu.get("rocm", False)
    vram_mb   = gpu.get("vram_mb", 0)

    # tier_3_pro: GPU dedicada con suficiente VRAM
    if (has_cuda or has_rocm) and vram_mb >= 4000 and ram_gb >= 12:
        return "tier_3_pro"

    # tier_2_balanced: CPU moderna con AVX2, buen RAM
    if has_avx2 and cores >= 4 and ram_gb >= 8:
        return "tier_2_balanced"

    # tier_1_eco: AVX (no AVX2) O poca RAM pero razonable
    if (has_avx or has_avx2) and cores >= 2 and ram_gb >= 4:
        return "tier_1_eco"

    # tier_0_minimal: sin AVX2, poco RAM, lento (Ivy Bridge y similares)
    return "tier_0_minimal"

# ─── Recomendaciones por tier ────────────────────────────────────────────────

TIER_RECOMMENDATIONS = {
    "tier_0_minimal": {
        "intent_engine": "tfidf",
        "stt":           "vosk_small",
        "tts":           "piper_low",
        "voice_id":      False,
        "slm":           None,
        "ui_fps":        15,
        "ui_particles":  30,
        "ui_blur":       False,
    },
    "tier_1_eco": {
        "intent_engine": "tfidf",
        "stt":           "vosk_small",
        "tts":           "piper_medium",
        "voice_id":      False,   # opcional: sherpa-onnx cam++
        "slm":           "smollm2_360m_q4",
        "ui_fps":        20,
        "ui_particles":  60,
        "ui_blur":       False,
    },
    "tier_2_balanced": {
        "intent_engine": "model2vec",
        "stt":           "sherpa_zipformer",
        "tts":           "kokoro_onnx",
        "voice_id":      True,
        "slm":           "qwen3_0_6b_q4",
        "ui_fps":        30,
        "ui_particles":  150,
        "ui_blur":       True,
    },
    "tier_3_pro": {
        "intent_engine": "model2vec",
        "stt":           "sherpa_sensevoice",
        "tts":           "kokoro_onnx",
        "voice_id":      True,
        "slm":           "qwen3_4b_q4",
        "ui_fps":        60,
        "ui_particles":  300,
        "ui_blur":       True,
    },
}

# ─── API pública ─────────────────────────────────────────────────────────────

def build_profile(force_refresh: bool = False) -> dict:
    """
    Construye el perfil completo de hardware y lo guarda en
    ~/.config/Fina/hardware_profile.json.

    Args:
        force_refresh: Si True, re-detecta incluso si existe el archivo.

    Returns:
        dict con claves: tier, flags_subset, cores, ram_total_gb,
        ram_available_gb, gpu, freq_ghz, session_type, on_battery,
        locale, disk_free_gb, recommended_* (intent_engine, stt, tts, ...)
    """
    # Cargar desde cache si existe y no se pide refresco
    if not force_refresh and PROFILE_PATH.exists():
        try:
            cached = json.loads(PROFILE_PATH.read_text())
            if cached.get("tier") and cached.get("schema_version") == 2:
                return cached
        except Exception:
            pass

    logger.info("🔍 Detectando perfil de hardware...")

    flags       = _cpu_flags()
    cores       = _cpu_physical_cores()
    ram_gb      = _ram_total_gb()
    ram_avail   = _ram_available_gb()
    freq_ghz    = _cpu_max_freq_ghz()
    gpu         = _detect_gpu()
    disk_free   = _disk_free_gb("~")
    session     = _session_type()
    on_battery  = _is_on_battery()
    locale      = _system_locale()

    tier = _assign_tier(flags, cores, ram_gb, gpu, freq_ghz)
    recommendations = TIER_RECOMMENDATIONS[tier].copy()

    # Ajuste dinámico: si está en batería, bajar un tier en rendimiento UI
    if on_battery and tier in ("tier_2_balanced", "tier_3_pro"):
        recommendations["ui_fps"]       = min(recommendations["ui_fps"], 20)
        recommendations["ui_particles"] = min(recommendations["ui_particles"], 60)
        recommendations["ui_blur"]      = False

    # Solo guardar subset relevante de flags (para no inflar el JSON)
    relevant_flags = ["avx", "avx2", "fma", "avx512f", "sse4_2", "aes", "cx16"]
    flags_subset = {f: f in flags for f in relevant_flags}

    profile = {
        "schema_version":   2,
        "tier":             tier,
        "flags":            flags_subset,
        "cores_physical":   cores,
        "ram_total_gb":     round(ram_gb, 2),
        "ram_available_gb": round(ram_avail, 2),
        "cpu_max_ghz":      round(freq_ghz, 2),
        "gpu":              gpu,
        "disk_free_gb":     round(disk_free, 1),
        "session_type":     session,
        "on_battery":       on_battery,
        "locale":           locale,
        "platform":         platform.machine(),
        **{f"recommended_{k}": v for k, v in recommendations.items()},
    }

    # Guardar
    try:
        FINA_CONFIG.mkdir(parents=True, exist_ok=True)
        PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False))
        logger.info(f"✅ Perfil guardado → {PROFILE_PATH} (tier={tier})")
    except Exception as e:
        logger.warning(f"⚠️ No se pudo guardar el perfil: {e}")

    return profile


# Cache en memoria para no releer el archivo en cada llamada
_cached_profile: dict | None = None

def get_profile(force_refresh: bool = False) -> dict:
    """
    Versión con cache en memoria. Usar esta función en toda la app.
    La primera llamada detecta y guarda; las siguientes son instantáneas.
    """
    global _cached_profile
    if _cached_profile is None or force_refresh:
        _cached_profile = build_profile(force_refresh=force_refresh)
    return _cached_profile


def get_tier() -> str:
    """Shortcut: retorna solo el string del tier activo."""
    return get_profile()["tier"]


# ─── CLI de diagnóstico ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    force = "--force" in sys.argv or "-f" in sys.argv
    p = build_profile(force_refresh=force)
    print("\n" + "=" * 54)
    print(f"  FINA HARDWARE PROFILE")
    print("=" * 54)
    print(f"  Tier        : {p['tier']}")
    print(f"  CPU cores   : {p['cores_physical']} físicos @ {p['cpu_max_ghz']} GHz")
    print(f"  RAM         : {p['ram_total_gb']:.1f} GB total / {p['ram_available_gb']:.1f} GB disponible")
    print(f"  GPU         : {p['gpu']['type'].upper()}  VRAM={p['gpu']['vram_mb']} MB  CUDA={p['gpu']['cuda']}")
    print(f"  SIMD        : AVX={p['flags']['avx']}  AVX2={p['flags']['avx2']}  FMA={p['flags']['fma']}")
    print(f"  Disco libre : {p['disk_free_gb']:.1f} GB")
    print(f"  Sesión      : {p['session_type']}  Batería={p['on_battery']}")
    print(f"  Locale      : {p['locale']}")
    print("-" * 54)
    print(f"  → Intent engine : {p['recommended_intent_engine']}")
    print(f"  → STT           : {p['recommended_stt']}")
    print(f"  → TTS           : {p['recommended_tts']}")
    print(f"  → Voice ID      : {p['recommended_voice_id']}")
    print(f"  → SLM           : {p['recommended_slm']}")
    print(f"  → UI FPS        : {p['recommended_ui_fps']}  Partículas={p['recommended_ui_particles']}  Blur={p['recommended_ui_blur']}")
    print("=" * 54)
    print(f"\n  Perfil guardado en: {PROFILE_PATH}\n")
