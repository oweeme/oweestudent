"""Fuente y tema de la página. La escritura Owee usa glifos del área privada de Unicode: solo la fuente
Owee Sans (assets/fonts, licencia OFL) los dibuja, así que se activa únicamente cuando hace falta."""
import flet as ft

import i18n

FUENTE_OWEE = "Owee Sans"


def aplicar(page: ft.Page):
    page.fonts = {FUENTE_OWEE: "fonts/OweeSans.ttf"}
    familia = FUENTE_OWEE if i18n.escritura_owee() else None
    page.theme = ft.Theme(font_family=familia)
    page.dark_theme = ft.Theme(font_family=familia)
