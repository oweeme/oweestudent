import flet as ft

from database import repo
from engine import ai
from ui.components.widgets import barra_progreso, tarjeta


def build(st):
    c = st.conn
    filas = c.execute("""SELECT u.titulo, SUM(t.horas_dedicadas) h, COUNT(*) n, SUM(t.estado='completado') ok
        FROM unidades u JOIN temas t ON t.unidad_id=u.id WHERE u.plan_id=? GROUP BY u.id ORDER BY u.orden""",
                      (st.plan_id,)).fetchall()
    olvido = c.execute("""SELECT t.titulo, AVG(n.dificultad) d FROM notas n JOIN temas t ON t.id=n.tema_id
        JOIN unidades u ON u.id=t.unidad_id JOIN planes p ON p.id=u.plan_id
        WHERE p.perfil_id=? GROUP BY t.id ORDER BY d LIMIT 5""", (st.perfil_id,)).fetchall()
    pr = ai.proyeccion(c, st.plan_id) if st.plan_id else None
    if not pr:
        proy = ft.Text("Sin datos aún")
    elif pr["fin"]:
        proy = ft.Text(f"A tu ritmo real ({pr['h_sem']:.1f} h/semana) terminas hacia {pr['fin']:%d/%m/%Y}. "
                       f"Faltan {pr['restantes']} temas (~{pr['horas_rest']:.0f} h).")
    else:
        proy = ft.Text(f"Faltan {pr['restantes']} temas (~{pr['horas_rest']:.0f} h). "
                       "Registra sesiones con el Pomodoro para calcular tu fecha de fin.")
    ret, n_rep = repo.retencion(c, st.perfil_id)
    n_tj = c.execute("""SELECT COUNT(*) FROM tarjetas k JOIN temas t ON t.id=k.tema_id JOIN unidades u ON u.id=t.unidad_id
        JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=?""", (st.perfil_id,)).fetchone()[0]
    return ft.Column([
        ft.Text("Métricas", style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Row([tarjeta("🔥 Racha", ft.Text(f"{repo.racha(c, st.perfil_id)} días", size=28)),
                tarjeta("⏱ Últimos 7 días", ft.Text(f"{repo.horas_semana(c, st.perfil_id):.1f} h", size=28))], wrap=True),
        tarjeta("Retención (últimos 30 días)",
                ft.Text(f"{ret:.0%} de recuerdos acertados en {n_rep} repasos · {n_tj} tarjetas" if ret is not None
                        else "Aún sin repasos. Crea tarjetas en «Estudiar» y repásalas cada día.")),
        tarjeta("Proyección de fin", proy),
        tarjeta("Avance por unidad", *[barra_progreso((r["ok"] or 0) / r["n"], f"{r['titulo'][:45]} · {r['h'] or 0:.1f} h")
                                       for r in filas]),
        tarjeta("Mayor índice de olvido", *([ft.Text(f"{r['titulo'][:60]} — {r['d']:.1f}/5") for r in olvido]
                                            or [ft.Text("Sin datos aún")])),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
