from datetime import date

import flet as ft

from database import repo
from engine import ai
from i18n import marcar, t, tn
from ui.components.widgets import barra_progreso, dialogo, tarjeta

# Se guardan en español en la base (cronograma.dia); solo se traducen al mostrarlos.
DIAS = [marcar("Lunes"), marcar("Martes"), marcar("Miércoles"), marcar("Jueves"), marcar("Viernes"),
        marcar("Sábado"), marcar("Domingo")]


def build(st, ir_a_estudio, recargar, ir_repaso=lambda: None, ir_entregas=lambda: None):
    c, hoy = st.conn, date.today()
    dia = DIAS[hoy.weekday()]
    act = [ft.ListTile(dense=True, title=ft.Text(r["actividad"]), subtitle=ft.Text(r["bloque"]),
                       trailing=ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip=t("Quitar del cronograma"),
                                              on_click=lambda _, i=r["id"]: (repo.borrar_cronograma(c, i), recargar())))
           for r in c.execute("SELECT * FROM cronograma WHERE plan_id=? AND dia=?", (st.plan_id, dia))]

    def add_crono(_):
        d = ft.Dropdown(label=t("Día"), value=dia, options=[ft.dropdown.Option(x, t(x)) for x in DIAS])
        b = ft.TextField(label=t("Bloque (ej. Bloque 1: IT)"))
        a = ft.TextField(label=t("Actividad"))
        dialogo(st.page, t("Añadir al cronograma"), [d, b, a], lambda v: (
            v[2].strip() and repo.agregar_cronograma(c, st.plan_id, v[0], v[1].strip() or t("Bloque"), v[2].strip()),
            recargar()))

    def reprogramar(_):
        n = ai.reprogramar_atrasados(c, st.plan_id)
        st.toast(tn(n, "{n} tema atrasado reprogramado desde hoy", "{n} temas atrasados reprogramados desde hoy"))
        recargar()
    temas = c.execute("""SELECT t.*, u.titulo unidad FROM temas t JOIN unidades u ON u.id=t.unidad_id
        WHERE u.plan_id=? AND t.estado!='completado' AND t.fecha_programada<=?
        ORDER BY t.fecha_programada DESC LIMIT 8""", (st.plan_id, (hoy).isoformat())).fetchall()

    def estudiar(tid, ti):
        st.tema_id, st.tema_titulo = tid, ti
        ir_a_estudio()

    tt = [ft.ListTile(dense=True, title=ft.Text(tm["titulo"], size=13),
                      subtitle=ft.Text(f"{tm['unidad']} · {tm['fecha_programada']}", size=11),
                      trailing=ft.IconButton(ft.Icons.PLAY_CIRCLE, on_click=lambda _, i=tm["id"], n=tm["titulo"]: estudiar(i, n)))
          for tm in temas] or [ft.Text(t("Nada pendiente para hoy 🎉"))]
    meta = repo.meta_semanal(c, st.plan_id)
    hs = repo.horas_semana(c, st.perfil_id)
    n_rev = len(repo.tarjetas_pendientes(c, st.perfil_id)) + len(repo.repasos_pendientes(c, st.perfil_id))
    prox = repo.proximas_entregas(c, st.perfil_id, 7)
    from ui.views.entregas import ICONOS, cuando
    tarjeta_entregas = tarjeta(
        t("Entregas y exámenes"),
        *([ft.ListTile(dense=True, leading=ft.Icon(ICONOS[e["tipo"]], size=18, color=ft.Colors.RED_300 if e["dias"] < 0 else ft.Colors.AMBER_400 if e["dias"] <= 1 else None),
                       title=ft.Text(e["titulo"], size=13), subtitle=ft.Text(f"{e['plan']} · {cuando(e['dias'])}", size=11), on_click=lambda _: ir_entregas())
           for e in prox[:5]] or [ft.Text(t("Nada para esta semana 🎉"))]),
        ft.TextButton(t("Ver todas / añadir"), on_click=lambda _: ir_entregas()))
    return ft.Column([ft.Text(f"{t(dia)} {hoy.isoformat()}", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                      tarjeta(t("Esta semana"), barra_progreso(min(1, hs / meta), t("{h:.1f} de {meta:g} h ·", h=hs, meta=meta)),
                              ft.TextButton(tn(n_rev, "🔁 {n} repaso pendiente hoy → empezar", "🔁 {n} repasos pendientes hoy → empezar")
                                            if n_rev else t("🔁 Repasos al día ✅"),
                                            on_click=lambda _: ir_repaso())),
                      tarjeta_entregas,
                      tarjeta(t("Cronograma de hoy"), *(act or [ft.Text(t("Sin cronograma importado"))]),
                              ft.TextButton(t("＋ Añadir al cronograma"), on_click=add_crono)),
                      tarjeta(t("Temas programados / atrasados"), *tt,
                              ft.OutlinedButton(t("Reprogramar atrasados (inteligente)"), icon=ft.Icons.AUTO_FIX_HIGH,
                                                on_click=reprogramar))],
                     spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
