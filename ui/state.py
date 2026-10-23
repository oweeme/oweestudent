from database import repo
import threading
import time

from database.db import init_db
from engine import nivel as niveles
from engine.pomodoro import Pomodoro
from i18n import t
from owee_curso.curso import TITULO_PLAN as TITULO_CURSO_OWEE


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
        self.espacio_tab = "temario"   # pestaña abierta dentro del estudio activo (temario, material, estudiar, repaso, curso)
        self.pestana_practica = None   # pestaña de Práctica a abrir (la consume la pantalla)
        self.pomodoro = Pomodoro()
        self.al_tick = []              # funciones que redibujan el reloj (barra global y pantalla Estudiar)
        self._ticker = None
        self.elegir_perfil(self.perfil_id)

    def elegir_perfil(self, perfil_id):
        self.perfil_id = perfil_id
        ps = repo.planes(self.conn, perfil_id)
        self.plan_id = self.plan_por_defecto(ps)
        self.tema_id, self.tema_titulo = None, ""
        self.carpeta_destino = None

    @staticmethod
    def plan_por_defecto(planes) -> int | None:
        """La asignatura que se abre sola: tu estudio propio primero (el más reciente); el curso de Owee, que es opcional,
        solo si es lo único que hay."""
        propios = [p for p in planes if p["titulo"] != TITULO_CURSO_OWEE]
        elegido = (propios or list(planes) or [None])[0]
        return elegido["id"] if elegido else None

    # ---------- Pomodoro global ----------
    def iniciar_pomodoro(self, tema_id, titulo: str) -> None:
        """Empieza un Pomodoro sobre un tema; sigue corriendo aunque cambies de pantalla."""
        mins_estudio, mins_descanso = niveles.ajustes(self.nivel())["pomodoro"]     # un niño de primaria no estudia 25 min seguidos
        self.tema_id, self.tema_titulo = tema_id, titulo
        self.pomodoro.iniciar(tema_id, titulo, mins_estudio, mins_descanso)
        self._arrancar_ticker()
        self.redibujar_pomodoro()

    def redibujar_pomodoro(self) -> None:
        for f in list(self.al_tick):
            try:
                f()
            except Exception:       # una pantalla que ya no existe no debe parar el reloj
                pass
        try:
            self.page.update()
        except Exception:
            pass

    def _arrancar_ticker(self) -> None:
        if self._ticker is not None and self._ticker.is_alive():
            return

        def bucle():
            while self.pomodoro.activo:
                for ev in self.pomodoro.avanzar():
                    if ev[0] == "estudio_completo":
                        repo.registrar_sesion(self.conn, ev[1], ev[2])
                        self.toast(t("Pomodoro registrado (+{n} min)", n=ev[2]))
                self.redibujar_pomodoro()
                time.sleep(1)
            self.redibujar_pomodoro()
        self._ticker = threading.Thread(target=bucle, daemon=True)
        self._ticker.start()

    def nivel(self) -> str:
        """Nivel del perfil activo (primaria, secundaria, adolescente, universitario, adulto)."""
        for p in repo.perfiles(self.conn):
            if p["id"] == self.perfil_id:
                return p["nivel"] or "universitario"
        return "universitario"

    def toast(self, msg):
        import flet as ft
        self.page.open(ft.SnackBar(ft.Text(msg)))
