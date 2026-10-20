"""Pantallas de Lecturas y de Preguntar a mis documentos (con una página falsa, sin abrir ventana)."""
import threading

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import busqueda as bq
from engine import material as mat


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.portapapeles, self.abiertos = [], ft.PagePlatform.LINUX, 1000, None, []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def set_clipboard(self, x): self.portapapeles = x
    def launch_url(self, *a): pass


class _HiloInmediato:
    def __init__(self, target=None, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@pytest.fixture(autouse=True)
def _espanol():
    i18n.fijar_idioma("es")
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def st(tmp_path):
    from ui.state import AppState
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = repo.crear_plan(s.conn, "Tesis", s.perfil_id)
    return s


def _todos(control, tipo):
    out = []
    pila = [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)          # en orden de aparición en la pantalla
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


@pytest.mark.parametrize("codigo", ["es", "en", "ru", "ja"])
def test_lecturas_lista_ficha_y_exportar(st, codigo):
    from ui.views import lecturas
    i18n.fijar_idioma(codigo)
    repo.importar_bibtex(st.conn, st.plan_id, "@article{a, author={Ruiz, Ana}, title={Redes y escuela}, year=2021, journal={Rev}}")
    cuerpo = lecturas.build(st, lambda: None)
    assert len(_todos(cuerpo, ft.ListTile)) == 1
    botones = {b.text: b for b in _todos(cuerpo, ft.OutlinedButton)}
    # copiar BibTeX
    next(b for b in botones.values() if b.icon == ft.Icons.COPY).on_click(None)
    assert "@article{" in st.page.portapapeles and "Redes y escuela" in st.page.portapapeles
    # abrir la ficha, rellenarla, guardar y crear tarjetas
    _todos(cuerpo, ft.ListTile)[0].on_click(None)
    campos = [c for c in _todos(cuerpo, ft.TextField) if c.multiline]
    campos[0].value, campos[2].value = "¿Mejora la asistencia?", "Sí, un 8 %"
    guardar = next(b for b in _todos(cuerpo, ft.ElevatedButton))
    guardar.on_click(None)
    l = repo.lecturas(st.conn, st.plan_id)[0]
    assert l["pregunta"] == "¿Mejora la asistencia?" and l["hallazgos"] == "Sí, un 8 %"
    next(b for b in _todos(cuerpo, ft.OutlinedButton) if b.icon == ft.Icons.STYLE).on_click(None)
    assert st.conn.execute("SELECT COUNT(*) FROM tarjetas WHERE origen='lectura'").fetchone()[0] == 2


def test_lecturas_cambiar_estado_desde_la_lista(st):
    from ui.views import lecturas
    repo.agregar_lectura(st.conn, st.plan_id, "Uno")
    cuerpo = lecturas.build(st, lambda: None)
    _todos(cuerpo, ft.IconButton)[0].on_click(None)
    assert repo.lecturas(st.conn, st.plan_id)[0]["estado"] == "leyendo"


def test_lecturas_sin_asignatura_avisa(st):
    from ui.views import lecturas
    st.plan_id = None
    assert isinstance(lecturas.build(st, lambda: None), ft.Text)


def test_lecturas_se_abre_directamente_en_una_ficha_si_viene_de_una_cita(st):
    from ui.views import lecturas
    lid = repo.agregar_lectura(st.conn, st.plan_id, "Con cita", hallazgos="x")
    st.abrir_lectura = lid
    cuerpo = lecturas.build(st, lambda: None)
    assert st.abrir_lectura is None and any(c.label and "Hallazgos" in c.label for c in _todos(cuerpo, ft.TextField))


@pytest.fixture
def con_libro(st, tmp_path, monkeypatch):
    f = tmp_path / "libro.md"
    f.write_text("La fotosíntesis es el proceso por el cual las plantas convierten la luz solar en energía química.\n" * 3, encoding="utf-8")
    h = mat.hash_archivo(str(f))
    mid = repo.agregar_material(st.conn, st.plan_id, "Biología básica", "md", h, "libro.md", str(f), 10)
    monkeypatch.setattr(threading, "Thread", _HiloInmediato)
    return st, mid, bq.Indice(tmp_path / "indice.db")


def _preguntar(st, idx, texto, ir_material=lambda: None, ir_lecturas=lambda: None):
    from ui.views import preguntar
    cuerpo = preguntar.build(st, ir_material, ir_lecturas, indice=idx)
    campo = next(c for c in _todos(cuerpo, ft.TextField))
    campo.value = texto
    next(b for b in _todos(cuerpo, ft.ElevatedButton)).on_click(None)
    zona = next(c for c in cuerpo.controls if isinstance(c, ft.Column))
    return cuerpo, zona


@pytest.mark.parametrize("codigo", ["es", "en", "ja"])
def test_preguntar_sin_ia_muestra_pasajes_con_su_fuente_y_abre_la_pagina(con_libro, monkeypatch, codigo):
    st, mid, idx = con_libro
    from engine import ai
    monkeypatch.setattr(ai, "ia_disponible", lambda: False)
    i18n.fijar_idioma(codigo)
    saltos = []
    _, zona = _preguntar(st, idx, "¿Qué es la fotosíntesis?", ir_material=lambda: saltos.append("material"))
    textos = [c.value for c in _todos(zona, ft.Text)]
    assert any("Biología básica" in x for x in textos)
    assert not any(isinstance(c, ft.Container) and False for c in zona.controls)
    abrir = next(b for b in _todos(zona, ft.TextButton))
    abrir.on_click(None)
    assert saltos == ["material"] and st.abrir_material == (mid, 1)


def test_preguntar_con_ia_muestra_respuesta_con_citas_revisadas(con_libro, monkeypatch):
    st, mid, idx = con_libro
    from engine import ai
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)
    monkeypatch.setattr(bq, "responder", lambda q, f: bq.revisar_respuesta("Las plantas convierten la luz en energía [1] [8].", len(f)))
    _, zona = _preguntar(st, idx, "¿Qué es la fotosíntesis?")
    textos = " ".join(c.value for c in _todos(zona, ft.Text))
    assert "Las plantas convierten la luz en energía [1]" in textos and "[8]" not in textos
    copiar = next(b for b in _todos(zona, ft.OutlinedButton))
    copiar.on_click(None)
    assert "[1] Biología básica" in st.page.portapapeles


def test_preguntar_sin_resultados_da_una_pista(con_libro, monkeypatch):
    st, mid, idx = con_libro
    from engine import ai
    monkeypatch.setattr(ai, "ia_disponible", lambda: False)
    _, zona = _preguntar(st, idx, "criptomonedas y blockchain")
    assert "No encontré nada parecido" in zona.controls[0].value


def test_preguntar_avisa_si_la_ia_falla_pero_muestra_los_pasajes(con_libro, monkeypatch):
    st, mid, idx = con_libro
    from engine import ai
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)

    def falla(q, f):
        raise RuntimeError("sin conexión")
    monkeypatch.setattr(bq, "responder", falla)
    _, zona = _preguntar(st, idx, "fotosíntesis plantas")
    textos = " ".join(c.value for c in _todos(zona, ft.Text))
    assert "sin conexión" in textos and "Biología básica" in textos


def test_material_se_abre_en_la_pagina_de_la_cita(con_libro):
    st, mid, idx = con_libro
    from ui.views import material
    st.abrir_material = (mid, 1)
    cuerpo = material.build(st, lambda: None)
    assert st.abrir_material is None
    assert any(isinstance(c, ft.IconButton) and c.icon == ft.Icons.ARROW_BACK for c in _todos(cuerpo, ft.IconButton))
