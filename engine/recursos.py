"""Detección de RAM, elección de modelo local según un presupuesto y descarga con progreso."""
import ctypes
import json
import subprocess
import sys
import urllib.request

# (modelo Ollama, RAM aproximada en GB con contexto de 2048 tokens, descripción)
MODELOS = [("qwen2.5:0.5b", 0.6, "mínimo (equipos muy justos)"),
           ("qwen2.5:1.5b", 1.3, "ligero"),
           ("qwen2.5:3b", 2.4, "equilibrado"),
           ("qwen2.5:7b", 5.2, "completo")]


def ram_gb() -> tuple[float, float]:
    """(total, disponible) en GB. Sin dependencias externas."""
    try:
        if sys.platform.startswith("linux"):
            m = {l.split(":")[0]: int(l.split()[1]) for l in open("/proc/meminfo") if ":" in l}
            return m["MemTotal"] / 1048576, m.get("MemAvailable", m["MemFree"]) / 1048576
        if sys.platform == "win32":
            class E(ctypes.Structure):
                _fields_ = [("l", ctypes.c_ulong), ("m", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                            ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
            e = E(); e.l = ctypes.sizeof(E)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(e))
            return e.total / 2**30, e.avail / 2**30
        if sys.platform == "darwin":
            t = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"])) / 2**30
            return t, t / 2
    except Exception:
        pass
    return 4.0, 2.0  # valor prudente si no se pudo leer


def recomendar(total_gb: float, porcentaje: float = 10) -> tuple[str, float, str, float]:
    """Mejor modelo cuya RAM quepa en `porcentaje`% de la memoria total. Devuelve (modelo, gb, desc, presupuesto)."""
    presupuesto = total_gb * porcentaje / 100
    elegido = MODELOS[0]  # si nada cabe, el más pequeño (y la UI avisa)
    for m in MODELOS:
        if m[1] <= presupuesto:
            elegido = m
    return (*elegido, presupuesto)


def descargar_modelo(url: str, modelo: str, progreso) -> None:
    """Descarga con la API de Ollama; llama progreso(fracción 0-1, texto)."""
    req = urllib.request.Request(url.rstrip("/") + "/api/pull",
                                 json.dumps({"model": modelo, "stream": True}).encode(),
                                 {"content-type": "application/json"})
    with urllib.request.urlopen(req, timeout=None) as r:
        for linea in r:
            d = json.loads(linea)
            if d.get("error"):
                raise RuntimeError(d["error"])
            if d.get("total"):
                progreso(d.get("completed", 0) / d["total"], d.get("status", ""))
            else:
                progreso(0, d.get("status", ""))
    progreso(1, "listo")
