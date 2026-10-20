import flet as ft

from database import repo
from i18n import t
from ui.components.widgets import confirmar, dialogo, opciones_nivel


def build(st, recargar, cerrar_sesion=None, ir_importar=lambda: None):
    c = st.conn

    def cambiar_perfil(e):
        nuevo = int(e.control.value)
        if nuevo == st.perfil_id:
            return
        if not repo.tiene_clave(c, nuevo):
            st.elegir_perfil(nuevo)
            recargar()
            return
        k = ft.TextField(label=t("Clave de ese usuario"), password=True, can_reveal_password=True)

        def ok(v):
            if repo.verificar_clave(c, nuevo, v[0]):
                st.elegir_perfil(nuevo)
            else:
                st.toast(t("Clave incorrecta"))
            recargar()
        dialogo(st.page, t("Cambiar de usuario"), [k], ok, t("Entrar"))

    perfil = ft.Dropdown(label=t("Perfil (quién estudia)"), width=260, value=str(st.perfil_id),
                         options=[ft.dropdown.Option(str(p["id"]), ("🔒 " if p["clave_hash"] else "") + f"{p['nombre']} · {t(p['nivel'])}")
                                  for p in repo.perfiles(c)], on_change=cambiar_perfil)

    def nuevo_perfil(_):
        nombre = ft.TextField(label=t("Nombre"))
        nivel = ft.Dropdown(label=t("Nivel"), value="universitario", options=opciones_nivel())

        clave = ft.TextField(label=t("Clave (opcional)"), password=True, can_reveal_password=True)

        def ok(v):
            if v[0].strip():
                st.elegir_perfil(repo.crear_perfil(c, v[0].strip(), v[1] or "universitario", v[2] or None))
                recargar()
        dialogo(st.page, t("Nuevo perfil"), [nombre, nivel, clave], ok)

    def cambiar_clave(_):
        campos = []
        if repo.tiene_clave(c, st.perfil_id):
            campos.append(ft.TextField(label=t("Clave actual"), password=True, can_reveal_password=True))
        campos.append(ft.TextField(label=t("Clave nueva (vacía = sin clave)"), password=True, can_reveal_password=True))

        def ok(v):
            if len(v) == 2 and not repo.verificar_clave(c, st.perfil_id, v[0]):
                st.toast(t("La clave actual no coincide"))
                return
            repo.fijar_clave(c, st.perfil_id, v[-1] or None)
            st.toast(t("Clave actualizada") if v[-1] else t("Clave eliminada"))
            recargar()
        dialogo(st.page, t("Clave de acceso"), campos, ok)

    # ---------- carpetas y asignaturas ----------
    def nueva_carpeta(_):
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
                ps = repo.planes(c, st.perfil_id)
                st.plan_id = ps[0]["id"] if ps else None
            recargar()
        confirmar(st.page, t("¿Borrar la carpeta «{nombre}» con todas sus asignaturas y su progreso?", nombre=k["nombre"]), ok)

    def nueva_asignatura(carpeta_id):
        campo = ft.TextField(label=t("Nombre (ej. Matemática, Alemán, Redes)"))

        def ok(v):
            if v[0].strip():
                st.plan_id = repo.crear_plan(c, v[0].strip(), st.perfil_id, carpeta_id=carpeta_id)
                recargar()
        dialogo(st.page, t("Nueva asignatura"), [campo], ok, t("Crear"))

    def mover(p):
        opciones = [ft.dropdown.Option("ninguna", t("(Sin carpeta)"))] + [
            ft.dropdown.Option(str(k["id"]), k["nombre"]) for k in repo.carpetas(c, st.perfil_id)]
        d = ft.Dropdown(label=t("Mover a la carpeta"), options=opciones,
                        value=str(p["carpeta_id"]) if p["carpeta_id"] else "ninguna")
        dialogo(st.page, t("Mover «{titulo}»", titulo=p["titulo"]), [d], lambda v: (
            repo.mover_plan(c, p["id"], None if v[0] in ("", "ninguna") else int(v[0])), recargar()), t("Mover"))

    def activar(pid):
        st.plan_id = pid
        recargar()

    def borrar(pid):
        def ok():
            repo.borrar_plan(c, pid)
            if st.plan_id == pid:
                ps = repo.planes(c, st.perfil_id)
                st.plan_id = ps[0]["id"] if ps else None
            recargar()
        confirmar(st.page, t("¿Borrar esta asignatura y su progreso?"), ok)

    def fila_plan(p):
        activo = p["id"] == st.plan_id
        return ft.ListTile(
            leading=ft.Icon(ft.Icons.CHECK_CIRCLE if activo else ft.Icons.RADIO_BUTTON_UNCHECKED),
            title=ft.Text(p["titulo"], weight=ft.FontWeight.BOLD if activo else None),
            subtitle=ft.Text(t("Progreso {p:.0%}", p=repo.progreso(c, p["id"])) + (t("  ·  activa") if activo else "")),
            on_click=lambda _, pid=p["id"]: activar(pid),
            trailing=ft.PopupMenuButton(items=[
                ft.PopupMenuItem(text=t("Mover a otra carpeta"), on_click=lambda _, p=p: mover(p)),
                ft.PopupMenuItem(text=t("Borrar"), on_click=lambda _, i=p["id"]: borrar(i))]))

    def destino_importar(carpeta_id):
        st.carpeta_destino = carpeta_id
        ir_importar()

    bloques = []
    for k in repo.carpetas(c, st.perfil_id):
        ps = repo.planes_de_carpeta(c, st.perfil_id, k["id"])
        bloques.append(ft.ExpansionTile(
            title=ft.Text(f"📁 {k['nombre']}  ({len(ps)})"), initially_expanded=True,
            controls=[*[fila_plan(p) for p in ps],
                      ft.Row([ft.TextButton(t("＋ Asignatura"), on_click=lambda _, i=k["id"]: nueva_asignatura(i)),
                              ft.TextButton(t("Importar aquí"), on_click=lambda _, i=k["id"]: destino_importar(i)),
                              ft.TextButton(t("Renombrar"), on_click=lambda _, k=k: renombrar(k)),
                              ft.TextButton(t("Borrar carpeta"), on_click=lambda _, k=k: borrar_carpeta(k))], wrap=True)]))
    sueltas = repo.planes_de_carpeta(c, st.perfil_id, None)
    if sueltas or not bloques:
        bloques.append(ft.ExpansionTile(
            title=ft.Text(t("Sin carpeta") + f"  ({len(sueltas)})"), initially_expanded=True,
            controls=[*[fila_plan(p) for p in sueltas],
                      ft.Row([ft.TextButton(t("＋ Asignatura"), on_click=lambda _: nueva_asignatura(None)),
                              ft.TextButton(t("Importar aquí"), on_click=lambda _: destino_importar(None))], wrap=True)]))
    return ft.Column([
        ft.Text(t("Carpetas y asignaturas"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Una carpeta agrupa tus asignaturas (ej. «Máster» → Management, Idiomas, IT; o «3º de secundaria» → Matemática, Ciencias, Historia). Toca una asignatura para activarla."), size=13),
        ft.Row([perfil, ft.OutlinedButton(t("Nuevo perfil"), icon=ft.Icons.PERSON_ADD, on_click=nuevo_perfil),
                ft.OutlinedButton(t("Clave de este perfil"), icon=ft.Icons.LOCK, on_click=cambiar_clave),
                *([ft.OutlinedButton(t("Cerrar sesión"), icon=ft.Icons.LOGOUT, on_click=lambda _: cerrar_sesion())]
                  if cerrar_sesion else [])], wrap=True),
        ft.ElevatedButton(t("＋ Nueva carpeta"), icon=ft.Icons.CREATE_NEW_FOLDER, on_click=nueva_carpeta),
        *bloques,
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
