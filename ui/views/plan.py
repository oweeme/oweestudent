import flet as ft

from database import repo
from ui.components.widgets import barra_progreso, confirmar, dialogo, tile_recurso


def build(st, ir_a_estudio, recargar):
    c = st.conn
    if not st.plan_id:
        return ft.Text("Aún no hay plan. Ve a «Planes» para crear uno o a «Importar».")
    plan = c.execute("SELECT * FROM planes WHERE id=?", (st.plan_id,)).fetchone()
    prog = ft.Column()
    prog.controls = [barra_progreso(repo.progreso(c, st.plan_id), "Progreso general")]

    def alternar(e, tid):
        repo.marcar_tema(c, tid, "completado" if e.control.value else "pendiente")
        prog.controls = [barra_progreso(repo.progreso(c, st.plan_id), "Progreso general")]
        st.page.update()

    def estudiar(tid, titulo):
        st.tema_id, st.tema_titulo = tid, titulo
        ir_a_estudio()

    def campo(label, **kw):
        return ft.TextField(label=label, **kw)

    def add_tema(uid):
        t, f = campo("Tema"), campo("Fecha programada (AAAA-MM-DD, opcional)")
        dialogo(st.page, "Nuevo tema", [t, f], lambda v: (
            v[0].strip() and repo.agregar_tema(c, uid, v[0].strip(), v[1].strip() or None), recargar()))

    def add_recurso(uid):
        r, tp = campo("Enlace, libro o recurso"), ft.Dropdown(label="Tipo", value="url", options=[
            ft.dropdown.Option(x) for x in ("url", "libro", "herramienta", "alternativa")])
        dialogo(st.page, "Nuevo recurso", [r, tp], lambda v: (
            v[0].strip() and repo.agregar_recurso(c, uid, v[0].strip(), v[1] or "url"), recargar()))

    def edit_tema(t):
        ti = campo("Tema", value=t["titulo"])
        f = campo("Fecha (AAAA-MM-DD)", value=t["fecha_programada"] or "")
        h = campo("Horas estimadas", value=str(t["horas_estimadas"]))

        def ok(v):
            try:
                horas = float(v[2].replace(",", "."))
            except ValueError:
                horas = None
            repo.editar_tema(c, t["id"], v[0].strip() or t["titulo"], v[1].strip() or None, horas)
            recargar()
        dialogo(st.page, "Editar tema", [ti, f, h], ok)

    def del_tema(tid):
        confirmar(st.page, "¿Borrar este tema?", lambda: (repo.borrar_tema(c, tid), recargar()))

    def edit_unidad(u):
        ti = campo("Título", value=u["titulo"])
        dialogo(st.page, "Renombrar unidad", [ti], lambda v: (
            v[0].strip() and repo.renombrar_unidad(c, u["id"], v[0].strip()), recargar()))

    def del_unidad(uid):
        confirmar(st.page, "¿Borrar la unidad con sus temas y recursos?", lambda: (repo.borrar_unidad(c, uid), recargar()))

    def add_unidad():
        t = campo("Título (ej. Módulo IT: Redes, o Inglés B2)")
        dialogo(st.page, "Nueva unidad", [t], lambda v: (
            v[0].strip() and repo.agregar_unidad(c, st.plan_id, v[0].strip()), recargar()))

    bloques, semestre_prev = [], None
    for u in repo.unidades(c, st.plan_id):
        if u["semestre"] != semestre_prev:
            semestre_prev = u["semestre"]
            bloques.append(ft.Text(semestre_prev or "", style=ft.TextThemeStyle.TITLE_MEDIUM,
                                   color=ft.Colors.BLUE_200))
        filas = []
        for t in repo.temas(c, u["id"]):
            filas.append(ft.ListTile(
                dense=True,
                leading=ft.Checkbox(value=t["estado"] == "completado",
                                    on_change=lambda e, tid=t["id"]: alternar(e, tid)),
                title=ft.Text(t["titulo"], size=13),
                subtitle=ft.Text(f"{t['fecha_programada'] or ''} · {t['horas_dedicadas']:.1f}/{t['horas_estimadas']} h", size=11),
                trailing=ft.Row([
                    ft.IconButton(ft.Icons.PLAY_CIRCLE, tooltip="Estudiar",
                                  on_click=lambda _, tid=t["id"], ti=t["titulo"]: estudiar(tid, ti)),
                    ft.IconButton(ft.Icons.EDIT, tooltip="Editar", on_click=lambda _, t=t: edit_tema(t)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip="Borrar", on_click=lambda _, i=t["id"]: del_tema(i))],
                    tight=True, width=150)))
        recs = repo.recursos(c, u["id"])
        if recs:
            filas.append(ft.Text("Recursos", weight=ft.FontWeight.BOLD))
            for r in recs:
                tl = tile_recurso(r)
                tl.trailing = ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip="Quitar",
                                            on_click=lambda _, i=r["id"]: (repo.borrar_recurso(c, i), recargar()))
                filas.append(tl)
        for e in c.execute("SELECT * FROM entregables WHERE unidad_id=?", (u["id"],)):
            filas.append(ft.ListTile(leading=ft.Icon(ft.Icons.ASSIGNMENT), title=ft.Text(e["titulo"]),
                                     subtitle=ft.Text(e["descripcion"] or "")))
        for m in c.execute("SELECT * FROM metas_idioma WHERE unidad_id=?", (u["id"],)):
            filas.append(ft.ListTile(leading=ft.Icon(ft.Icons.TRANSLATE), title=ft.Text(m["objetivo"]),
                                     subtitle=ft.Text(m["detalle"] or "")))
        filas.append(ft.Row([ft.TextButton("＋ Tema", on_click=lambda _, i=u["id"]: add_tema(i)),
                             ft.TextButton("＋ Recurso", on_click=lambda _, i=u["id"]: add_recurso(i)),
                             ft.TextButton("Renombrar", on_click=lambda _, u=u: edit_unidad(u)),
                             ft.TextButton("Borrar unidad", on_click=lambda _, i=u["id"]: del_unidad(i))], wrap=True))
        rango = f" (meses {u['mes_ini']}-{u['mes_fin']})" if u["mes_ini"] else ""
        bloques.append(ft.ExpansionTile(title=ft.Text(u["titulo"] + rango), controls=filas))

    return ft.Column([ft.Text(plan["titulo"], style=ft.TextThemeStyle.HEADLINE_SMALL), prog, *bloques,
                      ft.ElevatedButton("＋ Nueva unidad / módulo", on_click=lambda _: add_unidad())],
                     spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
