import time

import flet as ft

from database import repo


def build(st, al_entrar):
    """Pantalla de acceso: elige perfil y escribe su clave (si tiene)."""
    perfiles = repo.perfiles(st.conn)
    sel = ft.Dropdown(label="Usuario", value=str(perfiles[0]["id"]), width=300, options=[
        ft.dropdown.Option(str(p["id"]), ("🔒 " if p["clave_hash"] else "") + p["nombre"]) for p in perfiles])
    clave = ft.TextField(label="Clave", password=True, can_reveal_password=True, width=300, autofocus=True)
    error = ft.Text("", color=ft.Colors.RED_300)
    intentos = {"n": 0, "hasta": 0.0}

    def entrar(_=None):
        pid = int(sel.value)
        if time.time() < intentos["hasta"]:
            error.value = f"Demasiados intentos. Espera {int(intentos['hasta'] - time.time()) + 1} s"
        elif repo.verificar_clave(st.conn, pid, clave.value):
            intentos["n"] = 0
            st.elegir_perfil(pid)
            al_entrar()
            return
        else:
            intentos["n"] += 1
            if intentos["n"] >= 5:
                intentos["hasta"], intentos["n"] = time.time() + 30, 0
            error.value = "Clave incorrecta"
        clave.value = ""
        st.page.update()

    clave.on_submit = entrar
    return ft.Column([
        ft.Text("🎓 OweeStudent", style=ft.TextThemeStyle.HEADLINE_MEDIUM),
        ft.Text("Inicia sesión para continuar"), sel, clave,
        ft.ElevatedButton("Entrar", icon=ft.Icons.LOGIN, on_click=entrar), error,
    ], spacing=14, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
