from datetime import date

import flet as ft

from database import repo
from engine import ai
from ui.components.widgets import barra_progreso, dialogo, tarjeta

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]


def build(st, ir_a_estudio, recargar, ir_repaso=lambda: None):
    c, hoy = st.conn, date.today()
    dia = DIAS[hoy.weekday()]
    act = [ft.ListTile(dense=True, title=ft.Text(r["actividad"]), subtitle=ft.Text(r["bloque"]),
                       trailing=ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip="Quitar del cronograma",
                                              on_click=lambda _, i=r["id"]: (repo.borrar_cronograma(c, i), recargar())))
           for r in c.execute("SELECT * FROM cronograma WHERE plan_id=? AND dia=?", (st.plan_id, dia))]

    def add_crono(_):
        d = ft.Dropdown(label="Día", value=dia, options=[ft.dropdown.Option(x) for x in DIAS])
        b = ft.TextField(label="Bloque (ej. Bloque 1: IT)")
        a = ft.TextField(label="Actividad")
        dialogo(st.page, "Añadir al cronograma", [d, b, a], lambda v: (
            v[2].strip() and repo.agregar_cronograma(c, st.plan_id, v[0], v[1].strip() or "Bloque", v[2].strip()),
            recargar()))

    def reprogramar(_):
        n = ai.reprogramar_atrasados(c, st.plan_id)
        st.toast(f"{n} temas atrasados reprogramados desde hoy")
        recargar()
    temas = c.execute("""SELECT t.*, u.titulo unidad FROM temas t JOIN unidades u ON u.id=t.unidad_id
        WHERE u.plan_id=? AND t.estado!='completado' AND t.fecha_programada<=?
        ORDER BY t.fecha_programada DESC LIMIT 8""", (st.plan_id, (hoy).isoformat())).fetchall()

    def estudiar(tid, ti):
        st.tema_id, st.tema_titulo = tid, ti
        ir_a_estudio()

    tt = [ft.ListTile(dense=True, title=ft.Text(t["titulo"], size=13),
                      subtitle=ft.Text(f"{t['unidad']} · {t['fecha_programada']}", size=11),
                      trailing=ft.IconButton(ft.Icons.PLAY_CIRCLE, on_click=lambda _, i=t["id"], n=t["titulo"]: estudiar(i, n)))
          for t in temas] or [ft.Text("Nada pendiente para hoy 🎉")]
    meta = repo.meta_semanal(c, st.plan_id)
    hs = repo.horas_semana(c, st.perfil_id)
    n_rev = len(repo.tarjetas_pendientes(c, st.perfil_id)) + len(repo.repasos_pendientes(c, st.perfil_id))
    return ft.Column([ft.Text(f"{dia} {hoy.isoformat()}", style=ft.TextThemeStyle.HEADLINE_SMALL),
                      tarjeta("Esta semana", barra_progreso(min(1, hs / meta), f"{hs:.1f} de {meta:g} h ·"),
                              ft.TextButton(f"🔁 {n_rev} repasos pendientes hoy → empezar" if n_rev else "🔁 Repasos al día ✅",
                                            on_click=lambda _: ir_repaso())),
                      tarjeta("Cronograma de hoy", *(act or [ft.Text("Sin cronograma importado")]),
                              ft.TextButton("＋ Añadir al cronograma", on_click=add_crono)),
                      tarjeta("Temas programados / atrasados", *tt,
                              ft.OutlinedButton("Reprogramar atrasados (inteligente)", icon=ft.Icons.AUTO_FIX_HIGH,
                                                on_click=reprogramar))],
                     spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
