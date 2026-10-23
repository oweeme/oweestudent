import flet as ft

from i18n import marcar, t
from owee_curso.curso import TITULO_PLAN as TITULO_CURSO_OWEE
from ui.components.widgets import barra_progreso

NOMBRES = {"curso": marcar("Curso"), "temario": marcar("Temario"), "material": marcar("Material"), "estudiar": marcar("Estudiar"), "repaso": marcar("Repaso")}


def pestanas_de(titulo_plan: str) -> list[str]:
    """El curso de Owee añade su propia pestaña «Curso» (lecciones con glifos) al principio."""
    return (["curso"] if titulo_plan == TITULO_CURSO_OWEE else []) + ["temario", "material", "estudiar", "repaso"]


def build(st, contenido, cambiar, volver):
    """El espacio de UN estudio (p. ej. «Máster»): cabecera con su carpeta y su avance, y pestañas con todo lo suyo:
    temario, material, Pomodoro/apuntes y repaso. contenido(pestaña) devuelve el control; cambiar(pestaña) recarga."""
    c = st.conn
    plan = c.execute("SELECT * FROM planes WHERE id=?", (st.plan_id,)).fetchone()
    carpeta = c.execute("SELECT nombre FROM carpetas WHERE id=?", (plan["carpeta_id"],)).fetchone() if plan["carpeta_id"] else None
    orden = pestanas_de(plan["titulo"])
    actual = st.espacio_tab if st.espacio_tab in orden else orden[0]
    from database import repo
    botones = ft.Row([(ft.FilledButton if p == actual else ft.OutlinedButton)(t(NOMBRES[p]), on_click=lambda _, p=p: cambiar(p))
                      for p in orden], wrap=True, spacing=8)
    cabecera = ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Mis estudios"), on_click=lambda _: volver()),
                       ft.Column([ft.Text((f"📁 {carpeta['nombre']}" if carpeta else t("Mis estudios")), size=12),
                                  ft.Text(plan["titulo"], theme_style=ft.TextThemeStyle.TITLE_LARGE, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)],
                                 spacing=0, expand=True)])
    return ft.Column([cabecera, barra_progreso(repo.progreso(c, st.plan_id), t("Progreso general")), botones,
                      ft.Container(contenido(actual), expand=True)], spacing=8, expand=True)
