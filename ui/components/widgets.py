import flet as ft

from i18n import marcar, t

ICONOS_RECURSO = {"libro": ft.Icons.MENU_BOOK, "url": ft.Icons.LINK, "busqueda": ft.Icons.SEARCH,
                  "alternativa": ft.Icons.LIGHTBULB_OUTLINE, "herramienta": ft.Icons.BUILD}

NIVELES = (marcar("primaria"), marcar("secundaria"), marcar("adolescente"), marcar("universitario"), marcar("adulto"))


def opciones_nivel():
    """Opciones para un Dropdown de nivel: el valor guardado es el español, la etiqueta se traduce."""
    return [ft.dropdown.Option(x, t(x)) for x in NIVELES]


def tarjeta(titulo, *controles):
    return ft.Card(content=ft.Container(padding=14, content=ft.Column(
        [ft.Text(titulo, theme_style=ft.TextThemeStyle.TITLE_MEDIUM), *controles], spacing=8)))


def barra_progreso(valor, etiqueta=""):
    return ft.Column([ft.Text(f"{etiqueta} {valor:.0%}".strip()),
                      ft.ProgressBar(value=valor, expand=True)], spacing=4)


def tile_recurso(r):
    sub = r["descripcion"] if r["descripcion"] else None
    return ft.ListTile(dense=True, leading=ft.Icon(ICONOS_RECURSO.get(r["tipo"], ft.Icons.LINK)),
                       title=ft.Text(r["contenido"], selectable=True, size=13),
                       subtitle=ft.Text(sub, size=12) if sub else None)


def dialogo(page, titulo, campos, on_ok, texto_ok=None):
    """Diálogo con TextFields; on_ok recibe la lista de valores (str)."""
    texto_ok = texto_ok or t("Guardar")

    def ok(_):
        vals = [c.value or "" for c in campos]
        page.close(dlg)
        on_ok(vals)
    dlg = ft.AlertDialog(modal=True, title=ft.Text(titulo), content=ft.Column(campos, tight=True, width=380),
                         actions=[ft.TextButton(t("Cancelar"), on_click=lambda _: page.close(dlg)),
                                  ft.ElevatedButton(texto_ok, on_click=ok)])
    page.open(dlg)


def confirmar(page, mensaje, on_ok):
    dlg = ft.AlertDialog(modal=True, title=ft.Text(mensaje),
                         actions=[ft.TextButton(t("Cancelar"), on_click=lambda _: page.close(dlg)),
                                  ft.ElevatedButton(t("Sí, borrar"), on_click=lambda _: (page.close(dlg), on_ok()))])
    page.open(dlg)
