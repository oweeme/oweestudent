"""Enlace propio de la app para sincronizar: oweestudent://sync/<ip>:<puerto>/<pin>

Va dentro del QR. Si el móvil lo abre con la cámara, Android abre OweeStudent y se conecta solo (experimental);
si no, el texto se puede pegar en «Conectar por IP».
"""
import re

ESQUEMA = "oweestudent"
_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3})(?::(\d{2,5}))?\D+(\d{6})(?!\d)")


def crear(host: str, puerto: int, pin: str) -> str:
    return f"{ESQUEMA}://sync/{host}:{puerto}/{pin}"


def leer(texto: str, puerto_defecto: int = 8765):
    """Devuelve (url_base, pin) o None. Tolera rutas como '/192.168.1.5:8765/123456' o texto pegado entero."""
    m = _RE.search(texto or "")
    if not m:
        return None
    host, puerto, pin = m.group(1), int(m.group(2) or puerto_defecto), m.group(3)
    if not all(0 <= int(x) <= 255 for x in host.split(".")):
        return None
    return f"http://{host}:{puerto}", pin
