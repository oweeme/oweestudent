import flet as ft

from database import repo
from engine import escritura_owee as motor
from i18n import t
from owee_curso import curso
from ui.components.owee_texto import glifos


def tarjeta_de_palabra(st, palabra: str, significado: str) -> int:
    """Añade la palabra a «Repaso» (leerla y escribirla). Devuelve cuántas tarjetas nuevas se crearon."""
    plan_id = curso.plan_del_curso(st.conn, st.perfil_id)
    tema = repo.tema_para_tarjetas(st.conn, plan_id) if plan_id else None
    if not tema:
        return 0
    return (repo.crear_tarjetas(st.conn, tema, [(curso.MARCA_OWEE + palabra, significado)], "owee")
            + repo.crear_tarjetas(st.conn, tema, [(significado, curso.MARCA_OWEE + palabra)], "produccion"))


def build(st):
    """Diccionario Owee ⇄ español: busca por la palabra o por su significado, mira su glifo y llévala a Repaso."""
    cuerpo = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    resultados = ft.Column(spacing=2)
    busqueda = ft.TextField(label=t("Buscar en Owee o en español"), dense=True, expand=True, autofocus=False)
    clase = ft.Dropdown(label=t("Clase"), dense=True, width=190, value="todas",
                        options=[ft.dropdown.Option("todas", t("Todas"))] + [ft.dropdown.Option(c, c) for c in motor.clases()])

    def añadir(palabra, significado):
        n = tarjeta_de_palabra(st, palabra, significado)
        st.toast(t("Añadida a Repaso") if n else t("Ya estaba en Repaso"))

    def fila(palabra, significado, cl):
        return ft.ListTile(dense=True, leading=glifos(palabra, size=26),
                           title=ft.Text(f"{palabra}  ·  {significado}", size=14),
                           subtitle=ft.Text(cl, size=11),
                           trailing=ft.IconButton(ft.Icons.ADD_TASK, tooltip=t("Añadir a Repaso"),
                                                  on_click=lambda _, p=palabra, s=significado: añadir(p, s)))

    def buscar(_=None):
        filas, total = motor.buscar(busqueda.value, None if clase.value == "todas" else clase.value)
        resultados.controls = [fila(*f) for f in filas] or [ft.Text(t("No encontré nada. Prueba con otra palabra."))]
        if total > len(filas):
            resultados.controls.append(ft.Text(t("Mostrando {n} de {total}: escribe más para afinar.", n=len(filas), total=total), size=12, color=ft.Colors.OUTLINE))
        st.page.update()
    busqueda.on_change = clase.on_change = buscar

    dia = motor.palabra_del_dia()
    tarjeta_dia = []
    if dia:
        tarjeta_dia = [ft.Container(ft.Row([glifos(dia[0], size=40), ft.Column([
            ft.Text(t("Palabra del día"), size=12, color=ft.Colors.OUTLINE), ft.Text(f"{dia[0]}  ·  {dia[1]}", size=16, weight=ft.FontWeight.BOLD)], spacing=0, expand=True),
            ft.OutlinedButton(t("＋ Repaso"), on_click=lambda _: añadir(*dia))]),
            padding=12, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT))]
    cuerpo.controls = [ft.Text(t("Diccionario Owee"), theme_style=ft.TextThemeStyle.TITLE_LARGE), *tarjeta_dia,
                       ft.Row([busqueda, clase], wrap=True), resultados]
    buscar()
    return cuerpo
