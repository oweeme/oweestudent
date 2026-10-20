from datetime import date

import flet as ft

from database import repo
from engine import sprints as sp
from i18n import t, tn
from ui.components.widgets import confirmar

# a qué pantalla lleva «Ir» en cada paso: (vista, pestaña de Práctica)
DESTINOS = {"material": ("material", None), "feynman": ("practica", 1), "retos": ("retos", None), "estudiar": ("estudiar", None),
            "recuperacion": ("practica", 0), "simulacro": ("practica", 2), "debiles": ("practica", 3)}


def build(st, ir=lambda vista: None):
    c = st.conn
    if not st.plan_id:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    cuerpo = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    temas = [(tm["id"], tm["titulo"]) for u in repo.unidades(c, st.plan_id) for tm in repo.temas(c, u["id"])]

    def ir_a(accion, tema_id):
        vista, pestana = DESTINOS.get(accion, ("estudiar", None))
        if tema_id:
            st.tema_id = tema_id
            st.tema_titulo = next((x for i, x in temas if i == tema_id), "")
        st.pestana_practica = pestana
        ir(vista)

    def nuevo(_):
        tema = ft.Dropdown(label=t("Tema del sprint"), width=320, value=str(st.tema_id if st.tema_id in [i for i, _ in temas] else temas[0][0]),
                           options=[ft.dropdown.Option(str(i), x) for i, x in temas])

        def empezar(_):
            sp.crear_sprint(c, st.plan_id, int(tema.value), date.today())
            mostrar()
        cuerpo.controls = [ft.Text(t("Sprint de 7 días"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                           ft.Text(t("Una semana intensiva sobre un solo tema, con un paso por día: explorar, entender, practicar, fijar, recordar, probarte y corregir."), size=13),
                           tema, ft.ElevatedButton(t("Empezar el sprint hoy"), icon=ft.Icons.PLAY_ARROW, on_click=empezar)]
        st.page.update()

    def mostrar():
        s = sp.sprint_activo(c, st.perfil_id, st.plan_id)
        if s is None:
            if not temas:
                cuerpo.controls = [ft.Text(t("Esta asignatura aún no tiene temas. Añade alguno en «Plan»."))]
                return st.page.update()
            return nuevo(None)
        ts = sp.tareas(c, s["id"])
        d = sp.dia_actual(s)
        p = sp.progreso(c, s["id"])
        atrasado = sp.va_atrasado(c, s)
        toca = sp.tarea_de_hoy(c, s)

        def marcar(e, i):
            sp.marcar_tarea(c, i, e.control.value)
            mostrar()

        filas = []
        for x in ts:
            es_hoy = toca is not None and x["id"] == toca["id"]
            filas.append(ft.ListTile(
                leading=ft.Checkbox(value=bool(x["hecha"]), on_change=lambda e, i=x["id"]: marcar(e, i)),
                title=ft.Text(t("Día {n}", n=x["dia"]) + " · " + x["titulo"], size=13, weight=ft.FontWeight.BOLD if es_hoy else None,
                              color=ft.Colors.PRIMARY if es_hoy else ft.Colors.OUTLINE if x["hecha"] else None),
                trailing=ft.TextButton(t("Ir"), on_click=lambda _, a=x["accion"]: ir_a(a, s["tema_id"])) if not x["hecha"] else None))
        estado = (t("Empieza mañana o más adelante.") if d == 0 else t("¡Sprint completo! 🎉") if p["hechas"] == sp.DIAS else
                  t("Vas con retraso: haz primero el paso marcado, los pasos van en orden.") if atrasado else
                  tn(max(1, sp.DIAS - d + 1), "Queda {n} día de la semana.", "Quedan {n} días de la semana.") if d <= sp.DIAS else
                  t("La semana ya pasó: termina los pasos que faltan."))
        cuerpo.controls = [
            ft.Text(s["titulo"], theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
            ft.Text(t("{a} de {b} pasos hechos · {estado}", a=p["hechas"], b=p["total"], estado=estado), size=13,
                    color=ft.Colors.AMBER_400 if atrasado else None),
            ft.ProgressBar(value=p["porcentaje"] / 100), *filas,
            ft.Row([ft.OutlinedButton(t("Nuevo sprint"), icon=ft.Icons.ADD, on_click=lambda _: nuevo(None)),
                    ft.TextButton(t("Terminar este sprint"), on_click=lambda _: (sp.terminar(c, s["id"]), mostrar())),
                    ft.TextButton(t("Borrar sprint"), icon=ft.Icons.DELETE_OUTLINE,
                                  on_click=lambda _: confirmar(st.page, t("¿Borrar este sprint?"), lambda: (sp.borrar(c, s["id"]), mostrar())))], wrap=True)]
        st.page.update()

    mostrar()
    return cuerpo
