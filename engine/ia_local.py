"""IA ligera integrada: la app descarga `llama-server` (CPU, ~17 MB) y un modelo pequeño, y los ejecuta en segundo plano.

Sin Ollama, sin cuentas, sin terminal. Todo queda en la carpeta de datos de la app y se puede desinstalar.
No disponible en Android/iOS (no permiten ejecutar programas descargados): allí se usa la IA de otro equipo.
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path

from database.db import DATOS

LLAMA_TAG = "b11312"
BASE_MOTOR = f"https://github.com/ggml-org/llama.cpp/releases/download/{LLAMA_TAG}/"
HF = "https://huggingface.co/Qwen/Qwen2.5-{p}-Instruct-GGUF/resolve/main/qwen2.5-{p}-instruct-q4_k_m.gguf"
# clave -> (archivo, url, tamaño aproximado en MB, RAM aproximada en GB)
MODELOS = {"0.5b": ("qwen2.5-0.5b-instruct-q4_k_m.gguf", HF.format(p="0.5B"), 491, 0.6),
           "1.5b": ("qwen2.5-1.5b-instruct-q4_k_m.gguf", HF.format(p="1.5B"), 1117, 1.3),
           "3b": ("qwen2.5-3b-instruct-q4_k_m.gguf", HF.format(p="3B"), 2105, 2.4)}
PUERTO = 8089
INACTIVIDAD = 120  # s sin usar la IA -> se apaga el servidor y libera la RAM
DIR = DATOS / "ia"


def paquete_motor():
    """(nombre del archivo, URL) del binario de llama.cpp para este sistema, o None si no es posible."""
    import platform
    m = platform.machine().lower()
    arm = m in ("arm64", "aarch64")
    if sys.platform.startswith("linux") and "ANDROID_ROOT" not in os.environ:
        n = f"llama-{LLAMA_TAG}-bin-ubuntu-{'arm64' if arm else 'x64'}.tar.gz"
    elif sys.platform == "win32":
        n = f"llama-{LLAMA_TAG}-bin-win-cpu-{'arm64' if arm else 'x64'}.zip"
    elif sys.platform == "darwin":
        n = f"llama-{LLAMA_TAG}-bin-macos-{'arm64' if arm else 'x64'}.tar.gz"
    else:
        return None
    return n, BASE_MOTOR + n


def disponible_en_plataforma() -> bool:
    return paquete_motor() is not None


def clave_modelo_para(ram_total_gb: float, porcentaje: float = 10) -> str:
    """El modelo más grande cuya RAM cabe en el presupuesto; mínimo 0.5b."""
    pres, elegido = ram_total_gb * porcentaje / 100, "0.5b"
    for k, (_, _, _, gb) in MODELOS.items():
        if gb <= pres:
            elegido = k
    return elegido


def _exe() -> Path | None:
    nombre = "llama-server.exe" if sys.platform == "win32" else "llama-server"
    return next((p for p in (DIR / "motor").rglob(nombre)), None) if (DIR / "motor").exists() else None


def _estado_ruta() -> Path:
    return DIR / "ia.json"


def estado() -> dict:
    """{'instalado': bool, 'modelo': clave|None}"""
    try:
        d = json.loads(_estado_ruta().read_text())
    except (OSError, ValueError):
        return {"instalado": False, "modelo": None}
    ok = bool(d.get("modelo")) and _exe() is not None and (DIR / MODELOS[d["modelo"]][0]).exists()
    return {"instalado": ok, "modelo": d.get("modelo") if ok else None}


def instalado() -> bool:
    return estado()["instalado"]


# ---------------- descarga (con reanudación) ----------------
def descargar(url: str, destino: Path, progreso, etiqueta: str = "") -> None:
    """Descarga `url` a `destino` reanudando si quedó a medias. progreso(fracción 0-1, texto)."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".part")
    if destino.exists():
        return
    for intento in range(6):
        empezar = parcial.stat().st_size if parcial.exists() else 0
        req = urllib.request.Request(url, headers={"Range": f"bytes={empezar}-"} if empezar else {})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                if empezar and r.status != 206:      # el servidor no reanuda: empezar de cero
                    empezar = 0
                total = empezar + int(r.headers.get("Content-Length") or 0)
                with open(parcial, "ab" if empezar else "wb") as f:
                    hecho = empezar
                    while True:
                        bloque = r.read(1 << 18)
                        if not bloque:
                            break
                        f.write(bloque)
                        hecho += len(bloque)
                        if total:
                            progreso(hecho / total, f"{etiqueta} {hecho / 1048576:.0f} de {total / 1048576:.0f} MB")
            if total and parcial.stat().st_size < total:
                raise OSError("descarga incompleta")
            parcial.rename(destino)
            return
        except (OSError, urllib.error.URLError) as ex:
            if intento == 5:
                raise RuntimeError(f"No se pudo descargar ({ex}). Revisa tu conexión y vuelve a intentarlo: "
                                   "continuará donde se quedó.") from ex
            time.sleep(2)


def _extraer(archivo: Path, destino: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    base = destino.resolve()

    def seguro(nombre):
        if not (base / nombre).resolve().is_relative_to(base):
            raise ValueError("Archivo comprimido no seguro")
    if archivo.suffix == ".zip":
        with zipfile.ZipFile(archivo) as z:
            for n in z.namelist():
                seguro(n)
            z.extractall(destino)
    else:
        with tarfile.open(archivo) as t:
            for m in t.getmembers():
                seguro(m.name)
            try:
                t.extractall(destino, filter="data")
            except TypeError:  # Python < 3.12
                t.extractall(destino)


def instalar(clave: str, progreso) -> None:
    """Descarga e instala motor + modelo. Seguro de repetir: lo ya descargado se reutiliza."""
    paq = paquete_motor()
    if paq is None:
        raise RuntimeError("Este dispositivo no puede ejecutar la IA integrada. Usa la IA de otro equipo.")
    archivo_modelo, url_modelo, _, _ = MODELOS[clave]
    if _exe() is None:
        descargar(paq[1], DIR / paq[0], lambda f, t: progreso(f * 0.1, t), "Motor de IA")
        _extraer(DIR / paq[0], DIR / "motor")
        exe = _exe()
        if exe is None:
            raise RuntimeError("El paquete del motor de IA no contiene llama-server")
        exe.chmod(exe.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        (DIR / paq[0]).unlink(missing_ok=True)
    descargar(url_modelo, DIR / archivo_modelo, lambda f, t: progreso(0.1 + f * 0.9, t), "Modelo")
    _estado_ruta().write_text(json.dumps({"modelo": clave}))
    progreso(1.0, "Listo")


def desinstalar() -> None:
    parar()
    shutil.rmtree(DIR, ignore_errors=True)


# ---------------- servidor en segundo plano ----------------
_srv = {"proc": None, "timer": None, "lock": threading.Lock()}


def url() -> str:
    return f"http://127.0.0.1:{PUERTO}"


def _vivo() -> bool:
    p = _srv["proc"]
    return p is not None and p.poll() is None


def _sano() -> bool:
    try:
        with urllib.request.urlopen(url() + "/health", timeout=2) as r:
            return r.status == 200
    except Exception:
        return False


def asegurar(espera: int = 120) -> str:
    """Arranca el servidor si hace falta y espera a que el modelo esté cargado. Devuelve la URL."""
    with _srv["lock"]:
        e = estado()
        if not e["instalado"]:
            raise RuntimeError("La IA integrada no está instalada (Ajustes → IA)")
        if not _vivo():
            exe = _exe()
            env = dict(os.environ)
            env["LD_LIBRARY_PATH"] = str(exe.parent) + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
            kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {}   # sin ventana de consola
            log = open(DIR / "servidor.log", "wb")
            _srv["proc"] = subprocess.Popen(
                [str(exe), "-m", str(DIR / MODELOS[e["modelo"]][0]), "--host", "127.0.0.1", "--port", str(PUERTO),
                 "-c", "2048", "-np", "1"], cwd=str(exe.parent), env=env, stdout=log, stderr=log, **kw)
        fin = time.time() + espera
        while time.time() < fin:
            if not _vivo():
                raise RuntimeError(_explicar_fallo())
            if _sano():
                break
            time.sleep(0.5)
        else:
            raise RuntimeError("El motor de IA tardó demasiado en arrancar")
        _reiniciar_reloj()
    return url()


_PAQUETES = {"libgomp.so.1": "libgomp1", "libssl.so.3": "libssl3", "libcrypto.so.3": "libssl3",
             "libstdc++.so.6": "libstdc++6"}


def _explicar_fallo() -> str:
    """Traduce el error del motor a una instrucción que un estudiante pueda seguir."""
    import re
    try:
        log = (DIR / "servidor.log").read_text(errors="ignore")
    except OSError:
        log = ""
    m = re.search(r"error while loading shared libraries: (\S+?):", log)
    if m:
        lib = m.group(1)
        pkg = _PAQUETES.get(lib, lib)
        return (f"A tu sistema le falta una librería ({lib}). Instálala una vez con: sudo apt install {pkg} "
                "(o pide ayuda a quien administre el equipo) y vuelve a intentarlo.")
    return "El motor de IA se cerró al arrancar (detalles en " + str(DIR / "servidor.log") + ")"


def _reiniciar_reloj():
    if _srv["timer"]:
        _srv["timer"].cancel()
    t = threading.Timer(INACTIVIDAD, parar)
    t.daemon = True
    t.start()
    _srv["timer"] = t


def usado():
    """Llamar tras cada uso: reinicia el contador de inactividad."""
    if _vivo():
        _reiniciar_reloj()


def parar():
    if _srv["timer"]:
        _srv["timer"].cancel()
        _srv["timer"] = None
    p = _srv["proc"]
    if p is not None and p.poll() is None:
        p.terminate()
        try:
            p.wait(5)
        except subprocess.TimeoutExpired:
            p.kill()
    _srv["proc"] = None
