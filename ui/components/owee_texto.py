"""Dibujo de glifos Owee. El texto se guarda siempre en romano; aquí se convierte a glifos solo para mostrarlo,
con la fuente Owee Sans (registrada en ui/tema.py, licencia OFL)."""
import flet as ft

from i18n import owee
from ui.tema import FUENTE_OWEE


def glifos(romano: str, size: int = 28, **kw) -> ft.Text:
    return ft.Text(owee.a_escritura(romano), font_family=FUENTE_OWEE, size=size, **kw)


def texto_tarjeta(texto: str, size: int = 17, weight=None, selectable: bool = False, visible: bool = True):
    """Texto de una tarjeta: normal, o con la marca `[glifo]x` (solo el glifo) / `[owee]x` (glifo y romanización debajo)."""
    from owee_curso.curso import MARCA_GLIFO, MARCA_OWEE
    for marca, con_romano in ((MARCA_GLIFO, False), (MARCA_OWEE, True)):
        if texto.startswith(marca):
            romano = texto[len(marca):]
            hijos = [glifos(romano, size=int(size * 3), selectable=selectable)]
            if con_romano:
                hijos.append(ft.Text(romano, size=max(12, int(size * 0.75)), color=ft.Colors.OUTLINE, selectable=selectable))
            return ft.Column(hijos, spacing=2, visible=visible)
    return ft.Text(texto, size=size, weight=weight, selectable=selectable, visible=visible)
