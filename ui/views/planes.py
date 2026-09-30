import flet as ft

from database import repo
from ui.components.widgets import confirmar, dialogo, tarjeta


def build(st, recargar, cerrar_sesion=None):
    c = st.conn

    def cambiar_perfil(e):
        nuevo = int(e.control.value)
        if nuevo == st.perfil_id:
            return
        if not repo.tiene_clave(c, nuevo):
            st.elegir_perfil(nuevo)
            recargar()
            return
        k = ft.TextField(label="Clave de ese usuario", password=True, can_reveal_password=True)

        def ok(v):
            if repo.verificar_clave(c, nuevo, v[0]):
                st.elegir_perfil(nuevo)
            else:
                st.toast("Clave incorrecta")
            recargar()
        dialogo(st.page, "Cambiar de usuario", [k], ok, "Entrar")

    perfil = ft.Dropdown(label="Perfil (quién estudia)", width=260, value=str(st.perfil_id),
                         options=[ft.dropdown.Option(str(p["id"]), ("🔒 " if p["clave_hash"] else "") + f"{p['nombre']} · {p['nivel']}")
                                  for p in repo.perfiles(c)], on_change=cambiar_perfil)

    def nuevo_perfil(_):
        nombre = ft.TextField(label="Nombre")
        nivel = ft.Dropdown(label="Nivel", value="universitario", options=[
            ft.dropdown.Option(x) for x in ("primaria", "secundaria", "adolescente", "universitario", "adulto")])

        clave = ft.TextField(label="Clave (opcional)", password=True, can_reveal_password=True)

        def ok(v):
            if v[0].strip():
                st.elegir_perfil(repo.crear_perfil(c, v[0].strip(), v[1] or "universitario", v[2] or None))
                recargar()
        dialogo(st.page, "Nuevo perfil", [nombre, nivel, clave], ok)

    def cambiar_clave(_):
        campos = []
        if repo.tiene_clave(c, st.perfil_id):
            campos.append(ft.TextField(label="Clave actual", password=True, can_reveal_password=True))
        campos.append(ft.TextField(label="Clave nueva (vacía = sin clave)", password=True, can_reveal_password=True))

        def ok(v):
            if len(v) == 2 and not repo.verificar_clave(c, st.perfil_id, v[0]):
                st.toast("La clave actual no coincide")
                return
            repo.fijar_clave(c, st.perfil_id, v[-1] or None)
            st.toast("Clave actualizada" if v[-1] else "Clave eliminada")
            recargar()
        dialogo(st.page, "Clave de acceso", campos, ok)

    def nuevo_plan(_):
        t = ft.TextField(label="Nombre del plan (ej. IT, Idiomas, 3º de secundaria)")

        def ok(v):
            if v[0].strip():
                st.plan_id = repo.crear_plan(c, v[0].strip(), st.perfil_id)
                recargar()
        dialogo(st.page, "Nuevo plan vacío", [t], ok, "Crear")

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
        confirmar(st.page, "¿Borrar este plan y su progreso?", ok)

    filas = []
    for p in repo.planes(c, st.perfil_id):
        activo = p["id"] == st.plan_id
        filas.append(ft.ListTile(
            leading=ft.Icon(ft.Icons.CHECK_CIRCLE if activo else ft.Icons.RADIO_BUTTON_UNCHECKED),
            title=ft.Text(p["titulo"]), subtitle=ft.Text(f"Progreso {repo.progreso(c, p['id']):.0%}"),
            on_click=lambda _, pid=p["id"]: activar(pid),
            trailing=ft.IconButton(ft.Icons.DELETE_OUTLINE, on_click=lambda _, pid=p["id"]: borrar(pid))))
    return ft.Column([
        ft.Text("Perfiles y planes", style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Row([perfil, ft.OutlinedButton("Nuevo perfil", icon=ft.Icons.PERSON_ADD, on_click=nuevo_perfil),
                ft.OutlinedButton("Clave de este perfil", icon=ft.Icons.LOCK, on_click=cambiar_clave),
                *([ft.OutlinedButton("Cerrar sesión", icon=ft.Icons.LOGOUT, on_click=lambda _: cerrar_sesion())]
                  if cerrar_sesion else [])], wrap=True),
        tarjeta("Planes de este perfil (toca uno para activarlo)", *(filas or [ft.Text("Sin planes todavía")])),
        ft.ElevatedButton("Nuevo plan vacío (manual)", icon=ft.Icons.ADD, on_click=nuevo_plan),
        ft.Text("Para sumar contenido a un plan usa «Importar» → «Agregar al plan activo», "
                "o los botones + dentro de «Plan»."),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
