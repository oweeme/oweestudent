import flet as ft

from database import repo
from engine import estudios as motor
from i18n import t
from ui.components.widgets import confirmar, dialogo, tarjeta


def build(st, abrir, estudiar, recargar, ir_importar=lambda: None):
    """«Mis estudios»: tus carpetas (Máster, Idiomas…) con sus planes. Tocas un plan y ves todo su temario.
    abrir(plan_id) muestra el plan completo; estudiar(plan_id, tema_id, titulo) salta al siguiente tema."""
    c = st.conn

    # ---------- carpetas ----------
    def nueva_carpeta(_=None):
        campo = ft.TextField(label=t("Nombre (ej. Máster, 3º de secundaria, Idiomas)"))
        dialogo(st.page, t("Nueva carpeta"), [campo], lambda v: (
            v[0].strip() and repo.crear_carpeta(c, v[0], st.perfil_id), recargar()), t("Crear"))

    def renombrar(k):
        campo = ft.TextField(label=t("Nombre"), value=k["nombre"])
        dialogo(st.page, t("Renombrar carpeta"), [campo], lambda v: (
            v[0].strip() and repo.renombrar_carpeta(c, k["id"], v[0]), recargar()))

    def borrar_carpeta(k):
        def ok():
            ids = [p["id"] for p in repo.planes_de_carpeta(c, st.perfil_id, k["id"])]
            repo.borrar_carpeta(c, k["id"])
            if st.plan_id in ids:
                st.plan_id = st.plan_por_defecto(repo.planes(c, st.perfil_id))
            recargar()
        confirmar(st.page, t("¿Borrar la carpeta «{nombre}» con todas sus asignaturas y su progreso?", nombre=k["nombre"]), ok)

    def nueva_asignatura(carpeta_id):
        campo = ft.TextField(label=t("Nombre (ej. Matemática, Alemán, Redes)"))

        def ok(v):
            if v[0].strip():
                st.plan_id = repo.crear_plan(c, v[0].strip(), st.perfil_id, carpeta_id=carpeta_id)
                abrir(st.plan_id)
        dialogo(st.page, t("Nueva asignatura"), [campo], ok, t("Crear"))

    def mover(p):
        opciones = [ft.dropdown.Option("ninguna", t("(Sin carpeta)"))] + [
            ft.dropdown.Option(str(k["id"]), k["nombre"]) for k in repo.carpetas(c, st.perfil_id)]
        d = ft.Dropdown(label=t("Mover a la carpeta"), options=opciones,
                        value=str(p["carpeta_id"]) if p["carpeta_id"] else "ninguna")
        dialogo(st.page, t("Mover «{titulo}»", titulo=p["titulo"]), [d], lambda v: (
            repo.mover_plan(c, p["id"], None if v[0] in ("", "ninguna") else int(v[0])), recargar()), t("Mover"))

    def borrar(p):
        def ok():
            repo.borrar_plan(c, p["id"])
            if st.plan_id == p["id"]:
                st.plan_id = st.plan_por_defecto(repo.planes(c, st.perfil_id))
            recargar()
        confirmar(st.page, t("¿Borrar esta asignatura y su progreso?"), ok)

    def importar_en(carpeta_id):
        st.carpeta_destino = carpeta_id
        ir_importar()

    # ---------- cada plan ----------
    def fila_plan(p):
        sig = p["siguiente"]
        activo = p["id"] == st.plan_id
        estado = (t("{hechos} de {total} temas", hechos=p["hechos"], total=p["temas"]) if p["temas"]
                  else t("Aún sin temas: ábrelo para añadirlos o importa un archivo"))
        extra = [ft.Text(t("Sigue: {tema}", tema=sig["titulo"]), size=12, max_lines=2, overflow=ft.TextOverflow.ELLIPSIS)] if sig else []
        botones = [ft.ElevatedButton(t("Abrir plan completo"), icon=ft.Icons.LIST_ALT, on_click=lambda _, i=p["id"]: abrir(i))]
        if sig:
            botones.append(ft.OutlinedButton(t("Seguir estudiando"), icon=ft.Icons.PLAY_ARROW,
                                             on_click=lambda _, i=p["id"], s=sig: estudiar(i, s["id"], s["titulo"])))
        titulo = p["titulo"] + (t("  ·  opcional") if p["opcional"] else "")
        return ft.Container(padding=12, border_radius=10, border=ft.border.all(2 if activo else 1, ft.Colors.PRIMARY if activo else ft.Colors.OUTLINE_VARIANT),
                            content=ft.Column([
                                ft.Row([ft.Text(titulo, weight=ft.FontWeight.BOLD, size=15, expand=True),
                                        ft.PopupMenuButton(items=[
                                            ft.PopupMenuItem(text=t("Mover a otra carpeta"), on_click=lambda _, p=p: mover(p)),
                                            ft.PopupMenuItem(text=t("Borrar"), on_click=lambda _, p=p: borrar(p))])]),
                                ft.ProgressBar(value=p["progreso"]),
                                ft.Text(f"{estado} · {p['progreso']:.0%}", size=12), *extra,
                                ft.Row(botones, wrap=True)], spacing=6))

    bloques = []
    carpetas = repo.carpetas(c, st.perfil_id)
    arbol = motor.arbol(c, st.perfil_id)
    for carpeta, planes in arbol:
        if carpeta is not None:
            k = carpeta
            pie = ft.Row([ft.TextButton(t("＋ Asignatura"), on_click=lambda _, i=k["id"]: nueva_asignatura(i)),
                          ft.TextButton(t("Importar aquí"), on_click=lambda _, i=k["id"]: importar_en(i)),
                          ft.TextButton(t("Renombrar"), on_click=lambda _, k=k: renombrar(k)),
                          ft.TextButton(t("Borrar carpeta"), on_click=lambda _, k=k: borrar_carpeta(k))], wrap=True)
            cuerpo = [*([fila_plan(p) for p in planes] or [ft.Text(t("Esta carpeta está vacía."), size=12)]), pie]
            bloques.append(ft.ExpansionTile(title=ft.Text(f"📁 {k['nombre']}  ({len(planes)})", weight=ft.FontWeight.BOLD),
                                            initially_expanded=True, controls=cuerpo))
        else:
            opcional = bool(planes) and planes[0]["opcional"]
            titulo = t("Idiomas · Owee (opcional)") if opcional else (t("Sin carpeta") if carpetas else t("Mis asignaturas"))
            pie = [] if opcional else [ft.Row([ft.TextButton(t("＋ Asignatura"), on_click=lambda _: nueva_asignatura(None)),
                                              ft.TextButton(t("Importar aquí"), on_click=lambda _: importar_en(None))], wrap=True)]
            bloques.append(ft.ExpansionTile(title=ft.Text(f"{titulo}  ({len(planes)})", weight=ft.FontWeight.BOLD),
                                            initially_expanded=not opcional, controls=[*[fila_plan(p) for p in planes], *pie]))

    hay_algo = any(planes for _, planes in arbol)
    vacio = [] if hay_algo else [tarjeta(t("Empieza aquí"), ft.Text(
        t("Crea una carpeta (por ejemplo «Máster» o «Idiomas») y dentro tus planes, o importa un archivo con tu plan de estudios."), size=13))]
    return ft.Column([
        ft.Text(t("Mis estudios"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Elige un plan para ver su temario completo, o pulsa «Seguir estudiando» para continuar donde lo dejaste."), size=13),
        ft.Row([ft.ElevatedButton(t("＋ Nueva carpeta"), icon=ft.Icons.CREATE_NEW_FOLDER, on_click=nueva_carpeta),
                ft.OutlinedButton(t("Importar plan"), icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: importar_en(st.carpeta_destino))], wrap=True),
        *vacio, *bloques,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
