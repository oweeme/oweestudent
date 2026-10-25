import sys
from pathlib import Path

import flet as ft

import i18n
from database import repo
from database.db import DB_PATH
from engine import ai, enlace, sync
from engine import nivel as niveles
from owee_curso import curso as curso_owee
from engine.entorno import restaurar_librerias
from i18n import marcar, t
from ui import tema
from ui.components import pomodoro_barra
from ui.state import AppState
from ui.views import (ajustes, aprende_owee, asistente, certificacion_owee, diccionario_owee, escribir_owee, espacio, estudio, estudios, hoy, entregas, escritor, exportar, importar, lecturas, login, material, plan,
                      planes, practica, preguntar, repaso, retos, sincronizar, sprint, stats)

TEMAS = {"dark": ft.ThemeMode.DARK, "light": ft.ThemeMode.LIGHT, "system": ft.ThemeMode.SYSTEM}


def _carpeta_assets() -> str:
    """Carpeta `assets` también dentro de la app empaquetada (PyInstaller la deja en sys._MEIPASS, a veces en `_internal`)."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return str(base / "assets")


def main(page: ft.Page):
    i18n.iniciar()   # idioma guardado, o el del sistema la primera vez
    page.title = "OweeStudent"
    page.theme_mode = TEMAS.get(ai.cargar_config().get("tema", "dark"), ft.ThemeMode.DARK)
    page.padding = 16
    st = AppState(page)

    def mostrar_login():
        tema.aplicar(page)
        page.clean()
        page.navigation_bar = None
        page.on_resized = None
        page.vertical_alignment = ft.MainAxisAlignment.CENTER
        page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
        page.add(ft.SafeArea(login.build(st, mostrar_app), expand=True))
        page.update()

    def mostrar_app(vista=None):
        tema.aplicar(page)
        page.clean()
        page.vertical_alignment = ft.MainAxisAlignment.START
        page.horizontal_alignment = ft.CrossAxisAlignment.START
        construir_app(vista)

    def construir_app(vista=None):
        cuerpo = ft.Container(expand=True, alignment=ft.alignment.top_left)
        MAS = -1                 # «pantalla» del menú Más dentro del historial
        historial, actual = [], {"vista": None}
        HOY, PLAN, MATERIAL, REPASO, ESTUDIAR, PLANES, IMPORTAR, METRICAS, SINCRONIZAR, AJUSTES, OWEE, ASISTENTE, LECTURAS, PREGUNTAR, PRACTICA, EXPORTAR, ENTREGAS, ESCRITOR, RETOS, SPRINT, ESPACIO = range(21)
        PRINCIPALES = [HOY, PLAN, REPASO]      # barra inferior / barra lateral (+ «Más»). Material, Pomodoro y lectura viven DENTRO de cada estudio
        SIN_PLAN_OK = (HOY, PLAN, PLANES, IMPORTAR, ESTUDIAR, REPASO, METRICAS, SINCRONIZAR, AJUSTES, OWEE, ASISTENTE, PREGUNTAR, PRACTICA, EXPORTAR, ENTREGAS, ESCRITOR, RETOS, SPRINT)
        SECUNDARIAS = [(ENTREGAS, t("Entregas y exámenes"), ft.Icons.EVENT_AVAILABLE),
                       (ASISTENTE, t("Asistente de objetivo"), ft.Icons.FLAG),
                       (SPRINT, t("Sprint de 7 días"), ft.Icons.BOLT),
                       (RETOS, t("Retos prácticos"), ft.Icons.EMOJI_EVENTS),
                       (ESCRITOR, t("Escritor (monografías, tesis, libros)"), ft.Icons.EDIT_DOCUMENT),
                       (PRACTICA, t("Práctica activa (recordar, explicar, simulacro)"), ft.Icons.PSYCHOLOGY),
                       (LECTURAS, t("Lecturas (investigación)"), ft.Icons.LIBRARY_BOOKS),
                       (PREGUNTAR, t("Preguntar a mis documentos"), ft.Icons.QUESTION_ANSWER),
                       (PLANES, t("Perfiles y usuarios"), ft.Icons.PEOPLE),
                       (IMPORTAR, t("Importar plan"), ft.Icons.UPLOAD_FILE),
                       (METRICAS, t("Métricas"), ft.Icons.INSERT_CHART),
                       (OWEE, t("Aprende Owee (curso del idioma)"), ft.Icons.TRANSLATE),
                       (EXPORTAR, t("Exportar a Anki"), ft.Icons.IOS_SHARE),
                       (SINCRONIZAR, t("Sincronizar con otro equipo"), ft.Icons.SYNC),
                       (AJUSTES, t("Ajustes, IA y apariencia"), ft.Icons.SETTINGS)]
        investiga = niveles.ajustes(st.nivel())["investigacion"]      # la gestión de lecturas solo aparece desde la universidad
        SECUNDARIAS[:] = [x for x in SECUNDARIAS if investiga or x[0] != LECTURAS]
        vistas = {
            HOY: lambda: hoy.build(st, lambda: ir(ESTUDIAR), lambda: ir(HOY), lambda: ir(REPASO), lambda: ir(ENTREGAS), lambda: ir(SPRINT), lambda: ir(RETOS),
                     lambda: ir(ASISTENTE), lambda: ir(IMPORTAR), lambda: ir(OWEE), lambda: ir(MATERIAL)),
            PLAN: lambda: estudios.build(st, abrir_plan, estudiar_tema, lambda: ir(PLAN), lambda: ir(IMPORTAR)),
            ESPACIO: lambda: espacio.build(st, contenido_espacio, pestana, lambda: ir(PLAN)),
            MATERIAL: lambda: material.build(st, lambda: ir(ESPACIO), abrir_plan),
            REPASO: lambda: repaso.build(st),
            ESTUDIAR: lambda: estudio.build(st),
            PLANES: lambda: planes.build(st, lambda: mostrar_app(PLANES), mostrar_login),
            IMPORTAR: lambda: importar.build(st, lambda: abrir_plan(st.plan_id)),
            METRICAS: lambda: stats.build(st),
            SINCRONIZAR: lambda: sincronizar.build(st, lambda: ir(SINCRONIZAR)),
            ASISTENTE: lambda: asistente.build(st, lambda: abrir_plan(st.plan_id), lambda: ir(OWEE)),
            SPRINT: lambda: sprint.build(st, lambda nombre: ir({"material": MATERIAL, "practica": PRACTICA, "retos": RETOS, "estudiar": ESTUDIAR}[nombre])),
            RETOS: lambda: retos.build(st),
            ESCRITOR: lambda: escritor.build(st, lambda: ir(LECTURAS)),
            ENTREGAS: lambda: entregas.build(st, lambda: ir(PRACTICA)),
            PRACTICA: lambda: practica.build(st, lambda: ir(REPASO)),
            EXPORTAR: lambda: exportar.build(st),
            LECTURAS: lambda: lecturas.build(st, lambda: ir(LECTURAS), lambda mid, pag: (setattr(st, "abrir_material", (mid, pag)), ir(MATERIAL))),
            PREGUNTAR: lambda: preguntar.build(st, lambda: ir(MATERIAL), lambda: ir(LECTURAS)),
            OWEE: lambda: ver_owee(),
            AJUSTES: lambda: ajustes.build(st, lambda: ir(HOY), lambda: mostrar_app(AJUSTES)),
        }
        ETIQ = {HOY: (t("Hoy"), ft.Icons.TODAY), PLAN: (t("Estudios"), ft.Icons.SCHOOL), REPASO: (t("Repaso"), ft.Icons.REPLAY)}

        GRUPOS = [(marcar("Estudiar"), (ENTREGAS, PRACTICA, SPRINT, RETOS)),
                  (marcar("Planificar"), (ASISTENTE, IMPORTAR)),
                  (marcar("Investigar y escribir"), (ESCRITOR, LECTURAS, PREGUNTAR)),
                  (marcar("Idiomas"), (OWEE,)),
                  (marcar("Datos y ajustes"), (METRICAS, EXPORTAR, SINCRONIZAR, PLANES, AJUSTES))]

        def pantalla_mas():
            """El menú «Más», con las opciones agrupadas por lo que se quiere hacer."""
            por_id = {i: (txt, ic) for i, txt, ic in SECUNDARIAS}
            filas = []
            for nombre, ids in GRUPOS:
                presentes = [i for i in ids if i in por_id]
                if presentes:
                    filas.append(ft.Text(t(nombre), size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY))
                    filas += [ft.ListTile(leading=ft.Icon(por_id[i][1]), title=ft.Text(por_id[i][0]), dense=True,
                                          trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT), on_click=lambda _, i=i: ir(i)) for i in presentes]
            return ft.Column([ft.Text(t("Más"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), *filas],
                             spacing=2, scroll=ft.ScrollMode.AUTO, expand=True)

        def pestana(nombre):
            st.espacio_tab = nombre
            ir(ESPACIO)

        def abrir_plan(plan_id):
            """Entra al espacio de ese estudio (y lo deja como el estudio activo)."""
            st.plan_id = plan_id
            titulo = st.conn.execute("SELECT titulo FROM planes WHERE id=?", (plan_id,)).fetchone()["titulo"]
            st.espacio_tab = espacio.pestanas_de(titulo)[0]
            ir(ESPACIO)

        def estudiar_tema(plan_id, tema_id, titulo):
            st.plan_id, st.tema_id, st.tema_titulo = plan_id, tema_id, titulo
            pestana("estudiar")

        def abrir_curso_owee():
            """Aprende Owee es un estudio más: si ya está añadido se abre su espacio (Curso, Material, Estudiar, Repaso)."""
            pid = curso_owee.plan_del_curso(st.conn, st.perfil_id)
            if pid is None:
                return None
            curso_owee.actualizar_plan_del_curso(st.conn, pid)         # si el curso creció, aparecen las lecciones nuevas
            st.plan_id, st.espacio_tab = pid, "curso"
            return True

        def ver_owee():
            if abrir_curso_owee():
                return vistas[ESPACIO]()
            return aprende_owee.build(st, lambda: ir(OWEE))        # aún no añadido: pantalla de «Empezar el curso»

        def contenido_espacio(tab):
            return {"curso": lambda: aprende_owee.build(st, lambda: ir(ESPACIO)),
                    "escritura": lambda: escribir_owee.build(st),
                    "diccionario": lambda: diccionario_owee.build(st),
                    "certificacion": lambda: certificacion_owee.build(st, lambda: (setattr(st, "escritura_vista", "articulo"), pestana("escritura"))),
                    "temario": lambda: plan.build(st, lambda: pestana("estudiar"), lambda: ir(ESPACIO), lambda: pestana("material")),
                    "material": lambda: material.build(st, lambda: ir(ESPACIO), abrir_plan),
                    "estudiar": lambda: estudio.build(st),
                    "repaso": lambda: repaso.build(st, solo_plan=True)}[tab]()

        def ir_pomodoro():
            """La franja del Pomodoro lleva al estudio al que pertenece el tema en curso."""
            fila = st.conn.execute("""SELECT u.plan_id FROM temas t JOIN unidades u ON u.id=t.unidad_id WHERE t.id=?""", (st.pomodoro.tema_id,)).fetchone()
            if fila:
                st.plan_id = fila["plan_id"]
            pestana("estudiar")

        def seleccionar(i):
            i = PLAN if i == ESPACIO else i                    # dentro de un estudio sigue marcada «Estudios»
            k = PRINCIPALES.index(i) if i in PRINCIPALES else len(PRINCIPALES)
            rail.selected_index = bar.selected_index = k

        def anotar(i, guardar):
            """Recuerda de dónde vienes para poder volver atrás con la flecha."""
            if guardar and actual["vista"] is not None and actual["vista"] != i:
                historial.append(actual["vista"])
            actual["vista"] = i
            atras.visible = bool(historial)

        def volver(_=None):
            if historial:
                prev = historial.pop()
                ir_mas(guardar=False) if prev == MAS else ir(prev, guardar=False)

        def ir_mas(guardar=True):
            anotar(MAS, guardar)
            cuerpo.content = pantalla_mas()
            seleccionar(-1)
            page.update()

        def ir(i, guardar=True):
            if i in (MATERIAL, ESTUDIAR):                      # Material y Estudiar son pestañas del estudio activo
                if st.plan_id:
                    st.espacio_tab = "material" if i == MATERIAL else "estudiar"
                i = ESPACIO if st.plan_id else PLAN
            elif i == ESPACIO and not st.plan_id:
                i = PLAN
            anotar(i, guardar)
            cuerpo.content = vistas[i]() if (st.plan_id or i in SIN_PLAN_OK) else ft.Text(
                t("Aún no hay asignatura. Ve a «Más → Carpetas y asignaturas» o «Importar plan»."))
            seleccionar(i)
            page.update()

        def al_cambiar(e):
            k = e.control.selected_index
            historial.clear()                  # tocar una pestaña principal empieza de nuevo (sin flecha atrás)
            actual["vista"] = None
            ir(PRINCIPALES[k]) if k < len(PRINCIPALES) else ir_mas()

        rail = ft.NavigationRail(
            selected_index=0, label_type=ft.NavigationRailLabelType.ALL, on_change=al_cambiar,
            destinations=[ft.NavigationRailDestination(icon=ETIQ[i][1], label=ETIQ[i][0]) for i in PRINCIPALES]
            + [ft.NavigationRailDestination(icon=ft.Icons.MENU, label=t("Más"))])
        bar = ft.NavigationBar(
            selected_index=0, on_change=al_cambiar,
            destinations=[ft.NavigationBarDestination(icon=ETIQ[i][1], label=ETIQ[i][0]) for i in PRINCIPALES]
            + [ft.NavigationBarDestination(icon=ft.Icons.MENU, label=t("Más"))])
        divisor = ft.VerticalDivider(width=1)
        atras = ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Atrás"), visible=False, on_click=lambda _: volver())
        st.al_tick.clear()
        franja = ft.Row([atras, ft.Container(pomodoro_barra.crear(st, ir_pomodoro), expand=True)],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER)

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
                    st.toast(t("No se pudo sincronizar: {ex}", ex=ex))
            import threading
            threading.Thread(target=hacer, daemon=True).start()

        page.on_route_change = abrir_enlace
        page.on_resized = layout
        page.add(ft.SafeArea(ft.Row([rail, divisor, ft.Column([franja, cuerpo], expand=True, spacing=4)], expand=True,
                                    vertical_alignment=ft.CrossAxisAlignment.STRETCH), expand=True))
        layout()
        if vista is not None:      # p. ej. tras cambiar de idioma: volver a la misma pantalla
            ir(vista)
        else:
            ir(HOY)        # sin estudio propio, «Hoy» te guía: crear tu plan o importarlo (Owee es opcional)
        abrir_enlace()   # si la app se abrió desde un QR

    if repo.hay_claves(st.conn):
        mostrar_login()
    else:
        mostrar_app()


if __name__ == "__main__":
    restaurar_librerias()  # app empaquetada: que el cliente gráfico use las librerías del sistema
    if "--web" in sys.argv:  # sirve la app por Wi-Fi para móvil/tablet
        ft.app(target=main, view=None, host="0.0.0.0", port=8550, assets_dir=_carpeta_assets())  # solo servidor: no abre ventana en el PC
    else:
        ft.app(target=main, assets_dir=_carpeta_assets())
