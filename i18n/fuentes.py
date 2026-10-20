"""Chino y japonés necesitan una fuente con esos caracteres. Windows, macOS y Android ya la traen;
en Linux puede faltar y la interfaz se vería con cuadros vacíos."""
import subprocess
import sys

PAQUETE_LINUX = "sudo apt install fonts-noto-cjk"
CON_FUENTE_PROPIA = ("zh", "ja")


def comando_para_instalar(codigo: str) -> str | None:
    """Comando que instala la fuente si el idioma la necesita y este sistema no la tiene; si no, None.
    Si no se puede comprobar (sin fontconfig) devuelve None: mejor no avisar en falso."""
    if codigo not in CON_FUENTE_PROPIA or not sys.platform.startswith("linux"):
        return None
    try:
        r = subprocess.run(["fc-list", f":lang={codigo}", "family"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    return None if r.stdout.strip() else PAQUETE_LINUX
