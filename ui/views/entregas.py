from datetime import date, timedelta

import flet as ft

from database import repo
from i18n import marcar, t, tn
from ui.components.widgets import confirmar, dialogo

TIPOS = {"tarea": marcar("Tarea"), "examen": marcar("Examen"), "proyecto": marcar("Proyecto"), "otro": marcar("Otro")}
ICONOS = {"tarea": ft.Icons.ASSIGNMENT, "examen": ft.Icons.QUIZ, "proyecto": ft.Icons.WORK, "otro": ft.Icons.EVENT}


def cuando(dias: int) -> str:
    """«hoy», «mañana», «en 3 días» o «hace 2 días» (ya traducido)."""
    if dias == 0:
        return t("hoy")
    if dias == 1:
        return t("mañana")
    if dias > 1:
        return t("en {n} días", n=dias)
    return tn(-dias, "hace {n} día", "hace {n} días")


def build(st, ir_a_practica=lambda: None):
    c = st.conn
    planes = repo.planes(c, st.perfil_id)
    if not planes:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    cuerpo = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    ver_hechas = {"v": False}

    def refrescar():
        cuerpo.controls = construir()
        st.page.update()

    def alternar(e, eid):
        repo.marcar_entrega(c, eid, e.control.value)
        refrescar()

    def nueva(_):
        titulo = ft.TextField(label=t("¿Qué hay que entregar o estudiar?"), autofocus=True)
        tipo = ft.Dropdown(label=t("Tipo"), value="tarea", options=[ft.dropdown.Option(k, t(v)) for k, v in TIPOS.items()])
        fecha = ft.TextField(label=t("Fecha (AAAA-MM-DD)"), value=(date.today() + timedelta(days=1)).isoformat())
        plan = ft.Dropdown(label=t("Asignatura"), value=str(st.plan_id or planes[0]["id"]),
                           options=[ft.dropdown.Option(str(p["id"]), p["titulo"]) for p in planes])
        detalle = ft.TextField(label=t("Detalles (opcional)"), multiline=True, min_lines=2, max_lines=4)

        def ok(v):
            if not v[0].strip():
                return
            try:
                repo.agregar_entrega(c, int(v[3]), v[0], v[2].strip(), v[1] or "tarea", v[4])
            except ValueError:
                st.toast(t("La fecha debe tener el formato AAAA-MM-DD."))
                return
            refrescar()
        dialogo(st.page, t("Nueva entrega o examen"), [titulo, tipo, fecha, plan, detalle], ok)

    def editar(e):
        titulo = ft.TextField(label=t("¿Qué hay que entregar o estudiar?"), value=e["titulo"])
        fecha = ft.TextField(label=t("Fecha (AAAA-MM-DD)"), value=e["fecha"])
        detalle = ft.TextField(label=t("Detalles (opcional)"), value=e["detalle"] or "", multiline=True, min_lines=2, max_lines=4)

        def ok(v):
            try:
                repo.editar_entrega(c, e["id"], v[0] or None, v[1] or None, None, v[2])
            except ValueError:
                st.toast(t("La fecha debe tener el formato AAAA-MM-DD."))
                return
            refrescar()
        dialogo(st.page, t("Editar"), [titulo, fecha, detalle], ok)

    def borrar(e):
        confirmar(st.page, t("¿Borrar «{titulo}»?", titulo=e["titulo"]), lambda: (repo.borrar_entrega(c, e["id"]), refrescar()))

    def fila(e):
        hecha = e["estado"] == "hecha"
        color = ft.Colors.OUTLINE if hecha else ft.Colors.RED_300 if e["dias"] < 0 else ft.Colors.AMBER_400 if e["dias"] <= 2 else None
        sub = f"{e['plan']} · {e['fecha']}" + ("" if hecha else f" · {cuando(e['dias'])}")
        return ft.ListTile(
            leading=ft.Checkbox(value=hecha, on_change=lambda ev, i=e["id"]: alternar(ev, i)),
            title=ft.Row([ft.Icon(ICONOS[e["tipo"]], size=16, color=color),
                          ft.Text(e["titulo"], size=14, weight=ft.FontWeight.W_500, color=color,
                                  style=ft.TextStyle(decoration=ft.TextDecoration.LINE_THROUGH) if hecha else None, expand=True)]),
            subtitle=ft.Text(sub + (f"\n{e['detalle']}" if e["detalle"] else ""), size=12),
            trailing=ft.PopupMenuButton(items=[
                *([ft.PopupMenuItem(text=t("Practicar para este examen"), on_click=lambda _: ir_a_practica())] if e["tipo"] == "examen" and not hecha else []),
                ft.PopupMenuItem(text=t("Editar"), on_click=lambda _, e=e: editar(e)),
                ft.PopupMenuItem(text=t("Borrar"), on_click=lambda _, e=e: borrar(e))]))

    def construir():
        todas = repo.entregas(c, st.perfil_id)
        pend = [e for e in todas if e["estado"] == "pendiente"]
        hechas = [e for e in todas if e["estado"] == "hecha"]
        grupos = [(t("Vencidas"), [e for e in pend if e["dias"] < 0]), (t("Hoy y mañana"), [e for e in pend if 0 <= e["dias"] <= 1]),
                  (t("Esta semana"), [e for e in pend if 2 <= e["dias"] <= 7]), (t("Más adelante"), [e for e in pend if e["dias"] > 7])]
        out = [ft.Text(t("Entregas y exámenes"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
               ft.Text(t("Anota tus tareas, exámenes y proyectos con su fecha. Lo más urgente aparece en «Hoy»."), size=13),
               ft.ElevatedButton(t("＋ Nueva entrega o examen"), on_click=nueva)]
        for nombre, filas in grupos:
            if filas:
                out += [ft.Text(f"{nombre} ({len(filas)})", weight=ft.FontWeight.BOLD, size=13), *[fila(e) for e in filas]]
        if not pend:
            out.append(ft.Text(t("No tienes nada pendiente 🎉")))
        if hechas:
            out.append(ft.TextButton(t("Ocultar hechas") if ver_hechas["v"] else t("Ver hechas ({n})", n=len(hechas)),
                                     on_click=lambda _: (ver_hechas.update(v=not ver_hechas["v"]), refrescar())))
            if ver_hechas["v"]:
                out += [fila(e) for e in hechas]
        return out

    cuerpo.controls = construir()
    return cuerpo
