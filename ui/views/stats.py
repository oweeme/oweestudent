from datetime import date

import flet as ft

from database import repo
from engine import ai
from engine import resumen as resumen_motor
from i18n import t, tn
from ui.components import guardar
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
        proy = ft.Text(t("Sin datos aún"))
    elif pr["fin"]:
        proy = ft.Text(t("A tu ritmo real ({h:.1f} h/semana) terminas hacia {fin:%d/%m/%Y}. Faltan {n} temas (~{horas:.0f} h).",
                    h=pr["h_sem"], fin=pr["fin"], n=pr["restantes"], horas=pr["horas_rest"]))
    else:
        proy = ft.Text(t("Faltan {n} temas (~{horas:.0f} h). Registra sesiones con el Pomodoro para calcular tu fecha de fin.",
                    n=pr["restantes"], horas=pr["horas_rest"]))
    ret, n_rep = repo.retencion(c, st.perfil_id)
    n_tj = c.execute("""SELECT COUNT(*) FROM tarjetas k JOIN temas t ON t.id=k.tema_id JOIN unidades u ON u.id=t.unidad_id
        JOIN planes p ON p.id=u.plan_id WHERE p.perfil_id=?""", (st.perfil_id,)).fetchone()[0]
    aviso = ft.Text("", selectable=True)

    def copiar_resumen(_):
        st.page.set_clipboard(resumen_motor.a_texto(resumen_motor.resumen(c, st.perfil_id, st.plan_id)))
        aviso.value, aviso.color = t("Resumen copiado: pégalo en un mensaje o un correo."), ft.Colors.GREEN_400
        st.page.update()

    def escribir(destino):
        destino.write_text(resumen_motor.a_html(resumen_motor.resumen(c, st.perfil_id, st.plan_id)), encoding="utf-8")

    def terminado(destino, error):
        aviso.value, aviso.color = (t("No se pudo guardar: {ex}", ex=error), ft.Colors.RED_300) if error else (t("✅ Guardado en: {ruta}", ruta=str(destino)), ft.Colors.GREEN_400)
        st.page.update()

    picker = guardar.preparar(st.page, lambda ruta: guardar.escribir_elegido(ruta, "html", escribir, terminado))
    compartir = tarjeta(t("Compartir con tu familia o docente"),
                        ft.Text(t("Un resumen de la semana con cifras y títulos (nunca el contenido de tus notas). Lo compartes tú: la app no envía nada."), size=12),
                        ft.Row([ft.OutlinedButton(t("Copiar resumen"), icon=ft.Icons.COPY, on_click=copiar_resumen),
                                ft.OutlinedButton(t("Guardar resumen (HTML)"), icon=ft.Icons.SAVE_ALT,
                                                  on_click=lambda _: guardar.guardar(st.page, picker, f"resumen-{date.today():%Y%m%d}", "html", escribir, terminado))],
                               wrap=True), aviso)
    return ft.Column([
        ft.Text(t("Métricas"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Row([tarjeta(t("🔥 Racha"), ft.Text(tn(repo.racha(c, st.perfil_id), "{n} día", "{n} días"), size=28)),
                tarjeta(t("⏱ Últimos 7 días"), ft.Text(t("{h:.1f} h", h=repo.horas_semana(c, st.perfil_id)), size=28))], wrap=True),
        tarjeta(t("Retención (últimos 30 días)"),
                ft.Text(t("{ret:.0%} de recuerdos acertados en {rep} repasos · {tj} tarjetas", ret=ret, rep=n_rep, tj=n_tj)
                        if ret is not None
                        else t("Aún sin repasos. Crea tarjetas en «Estudiar» y repásalas cada día."))),
        tarjeta(t("Proyección de fin"), proy),
        tarjeta(t("Avance por unidad"), *[barra_progreso((r["ok"] or 0) / r["n"], f"{r['titulo'][:45]} · {r['h'] or 0:.1f} h")
                                       for r in filas]),
        tarjeta(t("Mayor índice de olvido"), *([ft.Text(f"{r['titulo'][:60]} — {r['d']:.1f}/5") for r in olvido]
                                            or [ft.Text(t("Sin datos aún"))])),
        compartir,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
