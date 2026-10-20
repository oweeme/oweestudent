"""Guardar un archivo generado por la app (exportaciones, escritos…).

En el escritorio se abre el diálogo «Guardar como…» para elegir dónde. En el móvil o en el modo web no hay un
diálogo fiable, así que se guarda en la carpeta de exportaciones de la app y se muestra la ruta.
"""
from pathlib import Path

import flet as ft

from database.db import DATOS

ESCRITORIO = (ft.PagePlatform.LINUX, ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS)


def carpeta_exportaciones() -> Path:
    c = DATOS / "exportaciones"
    c.mkdir(parents=True, exist_ok=True)
    return c


def hay_dialogo(page) -> bool:
    return page.platform in ESCRITORIO and not getattr(page, "web", False)


def preparar(page, al_elegir):
    """Crea el selector de archivos (una vez por pantalla). `al_elegir(ruta | None)` se llama al aceptar o cancelar."""
    picker = ft.FilePicker(on_result=lambda e: al_elegir(e.path))
    page.overlay.append(picker)
    return picker


def guardar(page, picker, nombre: str, extension: str, escribir, al_terminar):
    """Escribe el archivo con `escribir(Path)`. `al_terminar(ruta | None, error | None)` recibe el resultado.
    Con diálogo: hay que haber llamado antes a `preparar` y pasar su `picker` (el resultado llega por `al_elegir`)."""
    if hay_dialogo(page) and picker is not None:
        picker.save_file(dialog_title=nombre, file_name=f"{nombre}.{extension}", allowed_extensions=[extension])
        return
    destino = carpeta_exportaciones() / f"{nombre}.{extension}"
    try:
        escribir(destino)
    except Exception as ex:
        return al_terminar(None, ex)
    al_terminar(destino, None)


def escribir_elegido(ruta: str | None, extension: str, escribir, al_terminar):
    """Para el callback del diálogo: añade la extensión si falta, escribe y avisa. `ruta` None = canceló."""
    if not ruta:
        return
    destino = Path(ruta)
    if destino.suffix.lower() != f".{extension}":
        destino = destino.with_suffix(f".{extension}")
    try:
        escribir(destino)
    except Exception as ex:
        return al_terminar(None, ex)
    al_terminar(destino, None)
