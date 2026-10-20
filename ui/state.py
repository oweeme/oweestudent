from database import repo
from database.db import init_db


class AppState:
    """Estado compartido entre vistas: conexión, plan activo y tema en estudio."""

    def __init__(self, page):
        self.page = page
        self.conn = init_db()
        self.perfil_id = repo.perfiles(self.conn)[0]["id"]
        self.plan_id = None
        self.carpeta_destino = None
        self.tema_id = None
        self.tema_titulo = ""
        self.abrir_material = None     # (id de material, página): lo consume la pantalla de Material
        self.abrir_lectura = None      # id de lectura: lo consume la pantalla de Lecturas
        self.elegir_perfil(self.perfil_id)

    def elegir_perfil(self, perfil_id):
        self.perfil_id = perfil_id
        ps = repo.planes(self.conn, perfil_id)
        self.plan_id = ps[0]["id"] if ps else None
        self.tema_id, self.tema_titulo = None, ""
        self.carpeta_destino = None

    def nivel(self) -> str:
        """Nivel del perfil activo (primaria, secundaria, adolescente, universitario, adulto)."""
        for p in repo.perfiles(self.conn):
            if p["id"] == self.perfil_id:
                return p["nivel"] or "universitario"
        return "universitario"

    def toast(self, msg):
        import flet as ft
        self.page.open(ft.SnackBar(ft.Text(msg)))
