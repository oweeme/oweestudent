import flet as ft

from database import repo
from i18n import t
from ui.components.widgets import dialogo, opciones_nivel


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

    return ft.Column([
        ft.Text(t("Perfiles y usuarios"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Cada perfil tiene sus propias carpetas y planes. Tus carpetas y asignaturas están en la pestaña «Plan»."), size=13),
        ft.Row([perfil, ft.OutlinedButton(t("Nuevo perfil"), icon=ft.Icons.PERSON_ADD, on_click=nuevo_perfil),
                ft.OutlinedButton(t("Clave de este perfil"), icon=ft.Icons.LOCK, on_click=cambiar_clave),
                *([ft.OutlinedButton(t("Cerrar sesión"), icon=ft.Icons.LOGOUT, on_click=lambda _: cerrar_sesion())]
                  if cerrar_sesion else [])], wrap=True),
    ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True)
