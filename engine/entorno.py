"""Ajustes de entorno para la app empaquetada (PyInstaller)."""
import os
import sys


def restaurar_librerias(env: dict | None = None, empaquetado: bool | None = None) -> bool:
    """PyInstaller antepone su carpeta de librerías a LD_LIBRARY_PATH. Esa variable la hereda el cliente gráfico
    de Flet (un proceso aparte), que entonces carga librerías del paquete (compiladas en otra distro) en lugar de las
    de este sistema y falla (p. ej. 'libncursesw ... undefined symbol'). Se restaura el valor original.
    Devuelve True si cambió algo."""
    env = os.environ if env is None else env
    if empaquetado is None:
        empaquetado = bool(getattr(sys, "frozen", False)) and sys.platform.startswith("linux")
    if not empaquetado:
        return False
    if "LD_LIBRARY_PATH_ORIG" in env:
        if env["LD_LIBRARY_PATH_ORIG"]:
            env["LD_LIBRARY_PATH"] = env["LD_LIBRARY_PATH_ORIG"]
        else:
            env.pop("LD_LIBRARY_PATH", None)
        return True
    if env.get("LD_LIBRARY_PATH"):
        env.pop("LD_LIBRARY_PATH")
        return True
    return False
