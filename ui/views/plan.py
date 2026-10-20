import flet as ft

from database import repo
from i18n import marcar, t
from ui.components.widgets import barra_progreso, confirmar, dialogo, tile_recurso

TIPOS_RECURSO = (marcar("url"), marcar("libro"), marcar("herramienta"), marcar("alternativa"))


def build(st, ir_a_estudio, recargar):
    c = st.conn
    if not st.plan_id:
        st.plan_abierto = False
        return ft.Text(t("Aún no hay plan. Ve a «Planes» para crear uno o a «Importar»."))
    plan = c.execute("SELECT * FROM planes WHERE id=?", (st.plan_id,)).fetchone()
    carpeta = c.execute("SELECT nombre FROM carpetas WHERE id=?", (plan["carpeta_id"],)).fetchone() if plan["carpeta_id"] else None

    def volver(_=None):
        st.plan_abierto = False
        recargar()
    prog = ft.Column()
    prog.controls = [barra_progreso(repo.progreso(c, st.plan_id), t("Progreso general"))]

    def alternar(e, tid):
        repo.marcar_tema(c, tid, "completado" if e.control.value else "pendiente")
        prog.controls = [barra_progreso(repo.progreso(c, st.plan_id), t("Progreso general"))]
        st.page.update()

    def estudiar(tid, titulo):
        st.tema_id, st.tema_titulo = tid, titulo
        ir_a_estudio()

    def campo(label, **kw):
        return ft.TextField(label=label, **kw)

    def add_tema(uid):
        tm, f = campo(t("Tema")), campo(t("Fecha programada (AAAA-MM-DD, opcional)"))
        dialogo(st.page, t("Nuevo tema"), [tm, f], lambda v: (
            v[0].strip() and repo.agregar_tema(c, uid, v[0].strip(), v[1].strip() or None), recargar()))

    def add_recurso(uid):
        r, tp = campo(t("Enlace, libro o recurso")), ft.Dropdown(label=t("Tipo"), value="url", options=[
            ft.dropdown.Option(x, t(x)) for x in TIPOS_RECURSO])
        dialogo(st.page, t("Nuevo recurso"), [r, tp], lambda v: (
            v[0].strip() and repo.agregar_recurso(c, uid, v[0].strip(), v[1] or "url"), recargar()))

    def edit_tema(tema):
        ti = campo(t("Tema"), value=tema["titulo"])
        f = campo(t("Fecha (AAAA-MM-DD)"), value=tema["fecha_programada"] or "")
        h = campo(t("Horas estimadas"), value=str(tema["horas_estimadas"]))

        def ok(v):
            try:
                horas = float(v[2].replace(",", "."))
            except ValueError:
                horas = None
            repo.editar_tema(c, tema["id"], v[0].strip() or tema["titulo"], v[1].strip() or None, horas)
            recargar()
        dialogo(st.page, t("Editar tema"), [ti, f, h], ok)

    def del_tema(tid):
        confirmar(st.page, t("¿Borrar este tema?"), lambda: (repo.borrar_tema(c, tid), recargar()))

    def edit_unidad(u):
        ti = campo(t("Título"), value=u["titulo"])
        dialogo(st.page, t("Renombrar unidad"), [ti], lambda v: (
            v[0].strip() and repo.renombrar_unidad(c, u["id"], v[0].strip()), recargar()))

    def del_unidad(uid):
        confirmar(st.page, t("¿Borrar la unidad con sus temas y recursos?"), lambda: (repo.borrar_unidad(c, uid), recargar()))

    def add_unidad():
        ti = campo(t("Título (ej. Módulo IT: Redes, o Inglés B2)"))
        dialogo(st.page, t("Nueva unidad"), [ti], lambda v: (
            v[0].strip() and repo.agregar_unidad(c, st.plan_id, v[0].strip()), recargar()))

    bloques, semestre_prev = [], None
    for u in repo.unidades(c, st.plan_id):
        if u["semestre"] != semestre_prev:
            semestre_prev = u["semestre"]
            bloques.append(ft.Text(semestre_prev or "", theme_style=ft.TextThemeStyle.TITLE_MEDIUM,
                                   color=ft.Colors.BLUE_200))
        filas = []
        for tema in repo.temas(c, u["id"]):
            filas.append(ft.ListTile(
                dense=True,
                leading=ft.Checkbox(value=tema["estado"] == "completado",
                                    on_change=lambda e, tid=tema["id"]: alternar(e, tid)),
                title=ft.Text(tema["titulo"], size=13),
                subtitle=ft.Text(t("{fecha} · {hechas:.1f}/{est} h", fecha=tema["fecha_programada"] or "",
                                   hechas=tema["horas_dedicadas"], est=tema["horas_estimadas"]), size=11),
                trailing=ft.Row([
                    ft.IconButton(ft.Icons.PLAY_CIRCLE, tooltip=t("Estudiar"),
                                  on_click=lambda _, tid=tema["id"], ti=tema["titulo"]: estudiar(tid, ti)),
                    ft.IconButton(ft.Icons.EDIT, tooltip=t("Editar"), on_click=lambda _, tm=tema: edit_tema(tm)),
                    ft.IconButton(ft.Icons.DELETE_OUTLINE, tooltip=t("Borrar"), on_click=lambda _, i=tema["id"]: del_tema(i))],
                    tight=True, width=150)))
        recs = repo.recursos(c, u["id"])
        if recs:
            filas.append(ft.Text(t("Recursos"), weight=ft.FontWeight.BOLD))
            for r in recs:
                tl = tile_recurso(r)
                tl.trailing = ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip=t("Quitar"),
                                            on_click=lambda _, i=r["id"]: (repo.borrar_recurso(c, i), recargar()))
                filas.append(tl)
        for e in c.execute("SELECT * FROM entregables WHERE unidad_id=?", (u["id"],)):
            filas.append(ft.ListTile(leading=ft.Icon(ft.Icons.ASSIGNMENT), title=ft.Text(e["titulo"]),
                                     subtitle=ft.Text(e["descripcion"] or "")))
        for m in c.execute("SELECT * FROM metas_idioma WHERE unidad_id=?", (u["id"],)):
            filas.append(ft.ListTile(leading=ft.Icon(ft.Icons.TRANSLATE), title=ft.Text(m["objetivo"]),
                                     subtitle=ft.Text(m["detalle"] or "")))
        filas.append(ft.Row([ft.TextButton(t("＋ Tema"), on_click=lambda _, i=u["id"]: add_tema(i)),
                             ft.TextButton(t("＋ Recurso"), on_click=lambda _, i=u["id"]: add_recurso(i)),
                             ft.TextButton(t("Renombrar"), on_click=lambda _, u=u: edit_unidad(u)),
                             ft.TextButton(t("Borrar unidad"), on_click=lambda _, i=u["id"]: del_unidad(i))], wrap=True))
        rango = t(" (meses {a}-{b})", a=u["mes_ini"], b=u["mes_fin"]) if u["mes_ini"] else ""
        bloques.append(ft.ExpansionTile(title=ft.Text(u["titulo"] + rango), controls=filas))

    cabecera = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Mis estudios"), on_click=volver),
                       ft.Column([ft.Text((f"📁 {carpeta['nombre']}" if carpeta else t("Mis estudios")), size=12),
                                  ft.Text(plan["titulo"], theme_style=ft.TextThemeStyle.HEADLINE_SMALL)], spacing=0, expand=True)])
    return ft.Column([cabecera, prog, *bloques,
                      ft.ElevatedButton(t("＋ Nueva unidad / módulo"), on_click=lambda _: add_unidad())],
                     spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)
