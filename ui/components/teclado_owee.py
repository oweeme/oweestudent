import flet as ft

from engine import escritura_owee as motor
from i18n import t
from ui.components.owee_texto import glifos


def teclado(on_tecla, incluir_digitos: bool = True):
    """Teclado para ESCRIBIR en Owee Script sin instalar nada: cada tecla es una sílaba (glifo + romano).
    on_tecla(texto) recibe la sílaba, un dígito o «-» (nexo de palabras compuestas)."""
    def tecla(romano, ancho=58):
        return ft.Container(
            ft.Column([glifos(romano, size=24), ft.Text(romano, size=11, color=ft.Colors.OUTLINE)], spacing=0,
                      horizontal_alignment=ft.CrossAxisAlignment.CENTER),
            width=ancho, padding=ft.padding.symmetric(vertical=6), border_radius=8, ink=True,
            border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), on_click=lambda _: on_tecla(romano))

    k = motor.teclas()
    filas = [ft.Text(t("Vocales"), size=12, color=ft.Colors.OUTLINE), ft.Row([tecla(v) for v in k["vocales"]], spacing=6),
             ft.Text(t("Sílabas"), size=12, color=ft.Colors.OUTLINE)]
    filas += [ft.Row([tecla(s) for s in fila], spacing=6) for fila in k["silabas"]]
    if incluir_digitos:
        filas += [ft.Text(t("Números"), size=12, color=ft.Colors.OUTLINE),
                  ft.Row([tecla(d, 46) for d in k["digitos"]], spacing=6, wrap=True)]
    # varias columnas en pantallas anchas: las filas de sílabas fluyen en un Row con wrap
    return ft.Column([filas[0], filas[1], filas[2],
                      ft.Row([ft.Column([f], spacing=0) for f in filas[3:3 + len(k["silabas"])]], wrap=True, spacing=14, run_spacing=6),
                      *filas[3 + len(k["silabas"]):]], spacing=6)
