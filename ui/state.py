from database import repo
from database.db import init_db


class AppState:
    """Estado compartido entre vistas: conexión, plan activo y tema en estudio."""

    def __init__(self, page):
        self.page = page
        self.conn = init_db()
        self.perfil_id = repo.perfiles(self.conn)[0]["id"]
        self.plan_id = None
        self.tema_id = None
        self.tema_titulo = ""
        self.elegir_perfil(self.perfil_id)

    def elegir_perfil(self, perfil_id):
        self.perfil_id = perfil_id
        ps = repo.planes(self.conn, perfil_id)
        self.plan_id = ps[0]["id"] if ps else None
        self.tema_id, self.tema_titulo = None, ""

    def toast(self, msg):
        import flet as ft
        self.page.open(ft.SnackBar(ft.Text(msg)))
