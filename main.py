import sys

import flet as ft

from database import repo
from database.db import DB_PATH
from engine import ai, enlace, sync
from engine.entorno import restaurar_librerias
from ui.state import AppState
from ui.views import (ajustes, estudio, hoy, importar, login, material, plan, planes, repaso,
                      sincronizar, stats)

TEMAS = {"dark": ft.ThemeMode.DARK, "light": ft.ThemeMode.LIGHT, "system": ft.ThemeMode.SYSTEM}


def main(page: ft.Page):
    page.title = "OweeStudent"
    page.theme_mode = TEMAS.get(ai.cargar_config().get("tema", "dark"), ft.ThemeMode.DARK)
    page.padding = 16
    st = AppState(page)

    def mostrar_login():
        page.clean()
        page.navigation_bar = None
        page.on_resized = None
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(ft.SafeArea(login.build(st, mostrar_app), expand=True))
        page.update()

    def mostrar_app():
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        construir_app()

    def construir_app():
        cuerpo = ft.Container(expand=True, alignment=ft.alignment.top_left)
        HOY, PLAN, MATERIAL, REPASO, ESTUDIAR, PLANES, IMPORTAR, METRICAS, SINCRONIZAR, AJUSTES = range(10)
        PRINCIPALES = [HOY, PLAN, MATERIAL, REPASO]      # barra inferior / barra lateral (+ «Más»)
        SIN_PLAN_OK = (PLANES, IMPORTAR, ESTUDIAR, REPASO, METRICAS, SINCRONIZAR, AJUSTES)
        SECUNDARIAS = [(ESTUDIAR, "Estudiar (Pomodoro y tarjetas)", ft.Icons.TIMER),
                       (PLANES, "Carpetas y asignaturas", ft.Icons.FOLDER_COPY),
                       (IMPORTAR, "Importar plan", ft.Icons.UPLOAD_FILE),
                       (METRICAS, "Métricas", ft.Icons.INSERT_CHART),
                       (SINCRONIZAR, "Sincronizar con otro equipo", ft.Icons.SYNC),
                       (AJUSTES, "Ajustes, IA y apariencia", ft.Icons.SETTINGS)]
        vistas = {
            HOY: lambda: hoy.build(st, lambda: ir(ESTUDIAR), lambda: ir(HOY), lambda: ir(REPASO)),
            PLAN: lambda: plan.build(st, lambda: ir(ESTUDIAR), lambda: ir(PLAN)),
            MATERIAL: lambda: material.build(st, lambda: ir(MATERIAL)),
            REPASO: lambda: repaso.build(st),
            ESTUDIAR: lambda: estudio.build(st),
            PLANES: lambda: planes.build(st, lambda: ir(PLANES), mostrar_login, lambda: ir(IMPORTAR)),
            IMPORTAR: lambda: importar.build(st, lambda: ir(PLAN)),
            METRICAS: lambda: stats.build(st),
            SINCRONIZAR: lambda: sincronizar.build(st, lambda: ir(SINCRONIZAR)),
            AJUSTES: lambda: ajustes.build(st, lambda: ir(HOY)),
        }
        ETIQ = {HOY: ("Hoy", ft.Icons.TODAY), PLAN: ("Plan", ft.Icons.SCHOOL),
                MATERIAL: ("Material", ft.Icons.MENU_BOOK), REPASO: ("Repaso", ft.Icons.REPLAY)}

        def pantalla_mas():
            return ft.Column([ft.Text("Más", style=ft.TextThemeStyle.HEADLINE_SMALL),
                              *[ft.ListTile(leading=ft.Icon(ic), title=ft.Text(t), trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                                            on_click=lambda _, i=i: ir(i)) for i, t, ic in SECUNDARIAS]],
                             spacing=4, scroll=ft.ScrollMode.AUTO, expand=True)

        def seleccionar(i):
            k = PRINCIPALES.index(i) if i in PRINCIPALES else len(PRINCIPALES)
            rail.selected_index = bar.selected_index = k

        def ir_mas():
            cuerpo.content = pantalla_mas()
            seleccionar(-1)
            page.update()

        def ir(i):
            cuerpo.content = vistas[i]() if (st.plan_id or i in SIN_PLAN_OK) else ft.Text(
                "Aún no hay asignatura. Ve a «Más → Carpetas y asignaturas» o «Importar plan».")
            seleccionar(i)
            page.update()

        def al_cambiar(e):
            k = e.control.selected_index
            ir(PRINCIPALES[k]) if k < len(PRINCIPALES) else ir_mas()

        rail = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, on_change=al_cambiar,
            destinations=[ft.NavigationRailDestination(icon=ETIQ[i][1], label=ETIQ[i][0]) for i in PRINCIPALES]
            + [ft.NavigationRailDestination(icon=ft.Icons.MENU, label="Más")])
        bar = ft.NavigationBar(
            selected_index=0, on_change=al_cambiar,
            destinations=[ft.NavigationBarDestination(icon=ETIQ[i][1], label=ETIQ[i][0]) for i in PRINCIPALES]
            + [ft.NavigationBarDestination(icon=ft.Icons.MENU, label="Más")])
        divisor = ft.VerticalDivider(width=1)

        def layout(_=None):
            movil = (page.width or 1000) < 700
            rail.visible = divisor.visible = not movil
            page.navigation_bar = bar if movil else None
            page.update()

        def abrir_enlace(e=None):
            """Android abrió la app desde el QR (oweestudent://sync/IP:PUERTO/PIN): conectar y sincronizar."""
            datos = enlace.leer(page.route or "")
            if not datos:
                return
            ir(SINCRONIZAR)
            def hacer():
                try:
                    r = sync.recibir(st.conn, datos[0], DB_PATH, pin=datos[1])
                    st.elegir_perfil(st.perfil_id)
                    st.toast("✅ " + r)
                except Exception as ex:
                    st.toast(f"No se pudo sincronizar: {ex}")
            import threading
            threading.Thread(target=hacer, daemon=True).start()

        page.on_route_change = abrir_enlace
        page.on_resized = layout
        page.add(ft.SafeArea(ft.Row([rail, divisor, cuerpo], expand=True,
                                    vertical_alignment=ft.CrossAxisAlignment.STRETCH), expand=True))
        layout()
        ir(HOY) if st.plan_id else ir_mas()
        abrir_enlace()   # si la app se abrió desde un QR

    if repo.hay_claves(st.conn):
        mostrar_login()
    else:
        mostrar_app()


if __name__ == "__main__":
    restaurar_librerias()  # app empaquetada: que el cliente gráfico use las librerías del sistema
    if "--web" in sys.argv:  # sirve la app por Wi-Fi para móvil/tablet
        ft.app(target=main, view=None, host="0.0.0.0", port=8550)  # solo servidor: no abre ventana en el PC
    else:
        ft.app(target=main)
