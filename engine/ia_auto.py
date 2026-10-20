"""Activar la IA con un solo botón: usa lo que ya hay en el equipo y solo descarga si hace falta.

Orden: IA integrada ya instalada → servidor local que ya responde (Ollama, LM Studio…) → Ollama instalado pero apagado
(se enciende y, si no tiene modelos, descarga uno ligero) → IA integrada (motor de ~20 MB + modelo pequeño).
"""
import shutil
import subprocess
import sys
import time

from engine import ai, ia_local, recursos
from i18n import t

# Modelos de Ollama ordenados de más ligero a más pesado: entre los que ya tiene, se prefiere el más ligero que sirva.
_PREFERIDOS = [m[0] for m in recursos.MODELOS]


def diagnostico(ram_pct: float = 10) -> dict:
    """Qué hay en este equipo y qué haría el botón «Activar IA». `accion` ∈
    lista | usar_servidor | arrancar_ollama | instalar_integrada | ninguna."""
    total, libre = recursos.ram_gb()
    servidor = None if ia_local.instalado() else ai.detectar_local()
    ollama = shutil.which("ollama")
    if ia_local.instalado():
        accion = "lista"
    elif servidor:
        accion = "usar_servidor"
    elif ollama:
        accion = "arrancar_ollama"
    elif ia_local.disponible_en_plataforma():
        accion = "instalar_integrada"
    else:
        accion = "ninguna"
    return {"accion": accion, "integrada": ia_local.instalado(), "servidor": servidor, "ollama": ollama,
            "ram_total": total, "ram_libre": libre, "modelo_ollama": recursos.recomendar(total, ram_pct)[0],
            "modelo_integrado": ia_local.clave_modelo_para(total, ram_pct)}


def describir(d: dict) -> str:
    """Una frase para el estudiante sobre lo que se va a hacer."""
    a = d["accion"]
    if a == "lista":
        return t("✅ Tu IA ya está lista (IA integrada).")
    if a == "usar_servidor":
        url, ms = d["servidor"]
        return t("Encontré una IA en este equipo ({url}, {n} modelos). La usaré: no hace falta descargar nada.", url=url, n=len(ms))
    if a == "arrancar_ollama":
        return t("Tienes Ollama instalado. Lo encenderé y, si no tiene modelos, descargaré uno ligero ({modelo}).", modelo=d["modelo_ollama"])
    if a == "instalar_integrada":
        mb = ia_local.MODELOS[d["modelo_integrado"]][2]
        return t("No encontré Ollama. Instalaré una IA ligera integrada (modelo {modelo}, ~{gb:.1f} GB, una sola vez) sin que tengas que usar la terminal.",
                 modelo=d["modelo_integrado"].upper(), gb=mb / 1024)
    return t("Este dispositivo no puede ejecutar una IA por sí solo. Usa la de tu PC: «Opciones avanzadas» → «Buscar en mi red».")


def elegir_modelo(modelos: list[str]) -> str:
    """El más ligero de los conocidos si está; si no, el primero de la lista."""
    return next((p for p in _PREFERIDOS if p in modelos), modelos[0])


def _guardar(url: str, modelo: str, ram_pct: float) -> None:
    ai.guardar_config(local_url=url, local_modelo=modelo, ram_pct=ram_pct)


def _encender_ollama(espera: int = 20) -> str | None:
    """Arranca `ollama serve` sin ventana y devuelve su URL cuando responde."""
    kw = {"creationflags": 0x08000000} if sys.platform == "win32" else {"start_new_session": True}
    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kw)
    fin = time.time() + espera
    while time.time() < fin:
        try:
            ai.modelos_locales("http://localhost:11434")
            return "http://localhost:11434"
        except Exception:
            time.sleep(0.5)
    return None


def activar(progreso, ram_pct: float = 10) -> str:
    """Hace lo que dice `diagnostico()['accion']` y devuelve un mensaje final. progreso(fracción 0-1, texto)."""
    d = diagnostico(ram_pct)
    a = d["accion"]
    if a == "lista":
        return describir(d)
    if a == "usar_servidor":
        url, ms = d["servidor"]
        modelo = elegir_modelo(ms)
        _guardar(url, modelo, ram_pct)
        return t("✅ Usaré {modelo} de {url}.", modelo=modelo, url=url)
    if a == "arrancar_ollama":
        progreso(0, t("Encendiendo Ollama…"))
        url = _encender_ollama()
        if url is None:
            raise RuntimeError(t("No pude encender Ollama. Ábrelo una vez a mano y vuelve a pulsar el botón."))
        ms = ai.modelos_locales(url)
        if not ms:
            modelo = d["modelo_ollama"]
            recursos.descargar_modelo(url, modelo, progreso)
        else:
            modelo = elegir_modelo(ms)
        _guardar(url, modelo, ram_pct)
        return t("✅ Ollama listo con {modelo}.", modelo=modelo)
    if a == "instalar_integrada":
        ia_local.instalar(d["modelo_integrado"], progreso)
        ai.guardar_config(ram_pct=ram_pct)
        return t("✅ IA instalada. Ya puedes usar «Generar plan con IA» y las tarjetas con IA.")
    raise RuntimeError(describir(d))
