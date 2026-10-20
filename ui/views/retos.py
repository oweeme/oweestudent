import threading

import flet as ft

from database import repo
from engine import ai
from engine import practica as pr
from engine import retos as rt
from i18n import t
from ui.components.widgets import confirmar, dialogo


def build(st, recargar=lambda: None):
    c = st.conn
    if not st.plan_id:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    temas = [(tm["id"], tm["titulo"]) for u in repo.unidades(c, st.plan_id) for tm in repo.temas(c, u["id"])]
    cuerpo = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    aviso = ft.Text("")
    hechos = {"ver": False}

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- crear ----------
    def nuevo(_):
        if not temas:
            return msg(t("Esta asignatura aún no tiene temas. Añade alguno en «Plan»."), True)
        tema = ft.Dropdown(label=t("Tema"), width=320, value=str(st.tema_id if st.tema_id in [i for i, _ in temas] else temas[0][0]),
                           options=[ft.dropdown.Option(str(i), x) for i, x in temas])
        tipo = ft.Dropdown(label=t("Tipo de reto"), width=320, value="aplicar", options=[ft.dropdown.Option(k, t(v)) for k, v in rt.NOMBRES.items()])
        con_ia = ft.Switch(label=t("Que la IA proponga el reto con mi material"), value=False, visible=ai.ia_disponible())

        def ok(v):
            tid = int(v[0])
            if con_ia.value and ai.ia_disponible():
                msg(t("La IA está pensando un reto…"))

                def hacer():
                    try:
                        p = rt.proponer_con_ia(dict(temas)[tid], pr.referencia_de_tema(c, tid))
                        mostrar(rt.crear_reto(c, st.plan_id, tid, v[1] or "aplicar", p["titulo"], p["criterios"]))
                    except Exception as ex:
                        msg(t("Error IA: {ex}", ex=ex), True)
                        mostrar(rt.crear_reto(c, st.plan_id, tid, v[1] or "aplicar"))
                threading.Thread(target=hacer, daemon=True).start()
            else:
                mostrar(rt.crear_reto(c, st.plan_id, tid, v[1] or "aplicar"))
        dialogo(st.page, t("Nuevo reto"), [tema, tipo, con_ia], ok, t("Crear"))

    def para_todo(_):
        n = rt.retos_para_el_plan(c, st.plan_id)
        msg(t("{n} retos creados: uno por cada tema que no tenía.", n=n) if n else t("Todos los temas ya tienen un reto."), n == 0)
        lista()

    # ---------- lista ----------
    def lista():
        todos = rt.retos(c, st.perfil_id, st.plan_id)
        pend = [r for r in todos if r["estado"] == "pendiente"]
        hech = [r for r in todos if r["estado"] == "hecho"]

        def fila(r):
            p = rt.progreso(r)
            return ft.ListTile(
                leading=ft.Icon(ft.Icons.CHECK_CIRCLE if r["estado"] == "hecho" else ft.Icons.FLAG_OUTLINED,
                                color=ft.Colors.GREEN_400 if r["estado"] == "hecho" else None),
                title=ft.Text(r["titulo"], size=14, weight=ft.FontWeight.W_500),
                subtitle=ft.Column([ft.Text(r["tema"] or "", size=11), ft.ProgressBar(value=p)], spacing=2),
                on_click=lambda _, i=r["id"]: mostrar(i))
        cuerpo.controls = [
            ft.Text(t("Retos prácticos"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
            ft.Text(t("Saber un tema no es lo mismo que saber usarlo. Cada reto tiene criterios que tú compruebas; termina cuando los cumples y escribes qué hiciste y qué aprendiste."), size=13),
            ft.Row([ft.ElevatedButton(t("＋ Nuevo reto"), on_click=nuevo),
                    ft.OutlinedButton(t("Un reto por cada tema"), icon=ft.Icons.AUTO_AWESOME, on_click=para_todo)], wrap=True),
            *([fila(r) for r in pend] or [ft.Text(t("No tienes retos pendientes."))]),
            *([ft.TextButton(t("Ocultar hechos") if hechos["ver"] else t("Ver hechos ({n})", n=len(hech)),
                             on_click=lambda _: (hechos.update(ver=not hechos["ver"]), lista()))] if hech else []),
            *([fila(r) for r in hech] if hechos["ver"] else [])]
        st.page.update()

    # ---------- un reto ----------
    def mostrar(reto_id):
        r = rt.reto(c, reto_id)
        if r is None:
            return lista()
        crit = rt.criterios_de(r)
        hechos_i = set(rt.cumplidos_de(r))
        barra = ft.ProgressBar(value=rt.progreso(r))
        evidencia = ft.TextField(label=t("Tu evidencia: ¿qué hiciste y qué aprendiste?"), value=r["evidencia"] or "", multiline=True,
                                 min_lines=4, max_lines=10)
        nuevo_criterio = ft.TextField(label=t("Añadir un criterio propio"), width=320)

        def marcar(e, i):
            rt.marcar_criterio(c, reto_id, i, e.control.value)
            barra.value = rt.progreso(rt.reto(c, reto_id))
            st.page.update()

        def guardar(_):
            rt.guardar_evidencia(c, reto_id, evidencia.value)
            msg(t("Guardado"))

        def terminar(_):
            if rt.completar(c, reto_id, evidencia.value):
                st.toast(t("¡Reto cumplido! 🎉"))
                lista()
            else:
                msg(t("Para terminar, marca todos los criterios y escribe tu evidencia."), True)

        def agregar(_):
            rt.agregar_criterio(c, reto_id, nuevo_criterio.value)
            mostrar(reto_id)

        def borrar(_):
            confirmar(st.page, t("¿Borrar este reto?"), lambda: (rt.borrar(c, reto_id), lista()))

        hecho = r["estado"] == "hecho"
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Volver a los retos"), on_click=lambda _: lista()),
                    ft.Text(r["titulo"], theme_style=ft.TextThemeStyle.TITLE_MEDIUM, expand=True)]), aviso,
            *([ft.Text(t("Tema: {tema}", tema=r["tema"]), size=12)] if r["tema"] else []),
            ft.Text(t("Criterios de éxito"), weight=ft.FontWeight.BOLD), barra,
            *[ft.Checkbox(label=x, value=i in hechos_i, on_change=lambda e, i=i: marcar(e, i)) for i, x in enumerate(crit)],
            ft.Row([nuevo_criterio, ft.OutlinedButton(t("＋ Criterio"), on_click=agregar)], wrap=True), evidencia,
            ft.Row([ft.ElevatedButton(t("Guardar"), icon=ft.Icons.SAVE, on_click=guardar),
                    ft.ElevatedButton(t("Marcar el reto como hecho"), icon=ft.Icons.CHECK, on_click=terminar, disabled=hecho),
                    *([ft.OutlinedButton(t("Reabrir"), on_click=lambda _: (rt.reabrir(c, reto_id), mostrar(reto_id)))] if hecho else []),
                    ft.TextButton(t("Borrar reto"), icon=ft.Icons.DELETE_OUTLINE, on_click=borrar)], wrap=True)]
        st.page.update()

    lista()
    return cuerpo
