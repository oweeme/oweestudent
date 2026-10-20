"""La aplicación completa con una página falsa: cada opción del menú «Más» se abre sin errores."""
import flet as ft
import pytest

import i18n
import main as app
from database import repo


class _Pagina:
    def __init__(self):
        self.title, self.padding, self.route = "", 0, ""
        self.theme_mode = self.theme = self.dark_theme = self.navigation_bar = self.on_resized = self.on_route_change = None
        self.vertical_alignment = self.horizontal_alignment = None
        self.platform, self.width, self.web, self.fonts = ft.PagePlatform.LINUX, 1000, True, {}
        self.controles, self.overlay, self.abiertos = [], [], []

    def clean(self): self.controles = []
    def add(self, *c): self.controles += c
    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def set_clipboard(self, x): pass
    def launch_url(self, *a): pass


def _todos(control, tipo):
    out, pila = [], [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "tabs"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def _arrancar(monkeypatch, nivel="universitario"):
    from ui import state
    monkeypatch.setattr(i18n, "detectar_sistema", lambda: "es")      # el idioma del equipo de pruebas no debe influir
    p = _Pagina()
    original = state.AppState.__init__

    def init(self, page):
        original(self, page)
        for perfil in repo.perfiles(self.conn):
            self.conn.execute("UPDATE perfiles SET nivel=? WHERE id=?", (nivel, perfil["id"]))
        self.conn.commit()
        plan = repo.crear_plan(self.conn, "Biología", self.perfil_id)
        u = repo.agregar_unidad(self.conn, plan, "U1")
        self.tema_id = repo.agregar_tema(self.conn, u, "Células")
        self.plan_id = plan
    monkeypatch.setattr(state.AppState, "__init__", init)
    app.main(p)
    return p


def _cuerpo(p):
    return next(c for c in _todos(p.controles[0], ft.Container) if c.expand and c.alignment is not None)


@pytest.mark.parametrize("nivel,codigo", [("universitario", "es"), ("universitario", "en"), ("primaria", "es"), ("secundaria", "ja")])
def test_cada_opcion_del_menu_se_abre(monkeypatch, nivel, codigo):
    from engine import ai
    monkeypatch.setattr(ai, "cargar_config", lambda: {"idioma": codigo})
    p = _arrancar(monkeypatch, nivel)
    try:
        rail = next(c for c in _todos(p.controles[0], ft.NavigationRail))
        cuerpo = _cuerpo(p)
        rail.selected_index = 4                                   # «Más»
        rail.on_change(type("E", (), {"control": rail})())
        menu = cuerpo.content
        opciones = _todos(menu, ft.ListTile)
        assert len(opciones) == (16 if nivel == "universitario" else 15)      # sin «Lecturas (investigación)» en el colegio
        for i in range(len(opciones)):
            rail.on_change(type("E", (), {"control": rail})())       # volver al menú
            _todos(cuerpo.content, ft.ListTile)[i].on_click(None)
            assert cuerpo.content is not None
    finally:
        i18n.fijar_idioma("es")


@pytest.mark.parametrize("destino", range(4))
def test_las_cuatro_pestanas_principales_se_abren(monkeypatch, destino):
    p = _arrancar(monkeypatch)
    rail = next(c for c in _todos(p.controles[0], ft.NavigationRail))
    rail.selected_index = destino
    rail.on_change(type("E", (), {"control": rail})())
    assert _cuerpo(p).content is not None
