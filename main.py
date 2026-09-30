import sys

import flet as ft

from database import repo
from ui.state import AppState
from ui.views import ajustes, estudio, hoy, importar, login, plan, planes, repaso, stats

def main(page: ft.Page):
    page.title = "OweeStudent"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 16
    st = AppState(page)

    def mostrar_login():
        page.clean()
        page.navigation_bar = None
        page.on_resized = None
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(login.build(st, mostrar_app))
        page.update()

    def mostrar_app():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        construir_app()

    def construir_app():
        cuerpo = ft.Container(expand=True, alignment=ft.alignment.top_left)
        idx = {"i": 0}

        HOY, PLAN, PLANES, IMPORTAR, ESTUDIAR, REPASO, METRICAS, AJUSTES = range(8)
        vistas = [
            ("Hoy", ft.Icons.TODAY, lambda: hoy.build(st, lambda: ir(ESTUDIAR), lambda: ir(HOY))),
            ("Plan", ft.Icons.SCHOOL, lambda: plan.build(st, lambda: ir(ESTUDIAR), lambda: ir(PLAN))),
            ("Planes", ft.Icons.FOLDER_COPY, lambda: planes.build(st, lambda: ir(PLANES), mostrar_login)),
            ("Importar", ft.Icons.UPLOAD_FILE, lambda: importar.build(st, lambda: ir(PLAN))),
            ("Estudiar", ft.Icons.TIMER, lambda: estudio.build(st)),
            ("Repaso", ft.Icons.REPLAY, lambda: repaso.build(st)),
            ("Métricas", ft.Icons.INSERT_CHART, lambda: stats.build(st)),
            ("Ajustes", ft.Icons.SETTINGS, lambda: ajustes.build(st, lambda: ir(HOY))),
        ]

        def ir(i):
            idx["i"] = i
            cuerpo.content = vistas[i][2]() if (st.plan_id or i in (PLANES, IMPORTAR, ESTUDIAR, REPASO, METRICAS, AJUSTES)) else ft.Text(
                "Aún no hay plan. Ve a «Planes» o «Importar».")
            rail.selected_index = i
            bar.selected_index = i
            page.update()

        dests_rail = [ft.NavigationRailDestination(icon=v[1], label=v[0]) for v in vistas]
        dests_bar = [ft.NavigationBarDestination(icon=v[1], label=v[0]) for v in vistas]
        rail = ft.NavigationRail(selected_index=0, destinations=dests_rail, label_type=ft.NavigationRailLabelType.ALL,
                                 on_change=lambda e: ir(e.control.selected_index))
        bar = ft.NavigationBar(selected_index=0, destinations=dests_bar,
                               on_change=lambda e: ir(e.control.selected_index))

        def layout(_=None):
            movil = (page.width or 1000) < 700
            rail.visible = not movil
            page.navigation_bar = bar if movil else None
            page.update()

        page.on_resized = layout
        page.add(ft.Row([rail, ft.VerticalDivider(width=1), cuerpo], expand=True,
                         vertical_alignment=ft.CrossAxisAlignment.STRETCH))
        layout()
        ir(HOY if st.plan_id else IMPORTAR)

    if repo.hay_claves(st.conn):
        mostrar_login()
    else:
        mostrar_app()


if __name__ == "__main__":
    if "--web" in sys.argv:  # sirve la app por Wi-Fi para móvil/tablet
        ft.app(target=main, view=ft.AppView.WEB_BROWSER, host="0.0.0.0", port=8550)
    else:
        ft.app(target=main)
