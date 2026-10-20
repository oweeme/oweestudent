"""Pantalla del escritor (con una página falsa)."""
import threading

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import ai
from engine import busqueda as bq
from engine import escritura as es
from engine import material as mat


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web = [], ft.PagePlatform.LINUX, 1000, True
        self.portapapeles, self.abiertos = None, []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def set_clipboard(self, x): self.portapapeles = x
    def launch_url(self, *a): pass


class _Hilo:
    def __init__(self, target=None, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        self.target(*self.args)


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    i18n.fijar_idioma("es")
    monkeypatch.setattr(threading, "Thread", _Hilo)
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def st(tmp_path):
    from ui.state import AppState
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = repo.crear_plan(s.conn, "Tesis", s.perfil_id)
    repo.importar_bibtex(s.conn, s.plan_id, "@article{ruiz2021, author={Ruiz, Ana}, title={Transporte escolar}, year=2021, journal={Rev}}")
    s.idx = bq.Indice(tmp_path / "indice.db")
    return s


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


def _textos(control):
    return " ".join(str(x.value) for x in _todos(control, ft.Text) if x.value)


def _boton(control, texto):
    return next(b for b in _todos(control, (ft.ElevatedButton, ft.OutlinedButton, ft.TextButton)) if texto in str(b.text))


def _abrir(st, cuerpo, i=0):
    _todos(cuerpo, ft.ListTile)[i].on_click(None)


@pytest.mark.parametrize("codigo", ["es", "en", "ja"])
def test_lista_escrito_y_secciones_en_varios_idiomas(st, codigo):
    from ui.views import escritor
    i18n.fijar_idioma(codigo)
    cuerpo = escritor.build(st, indice=st.idx)
    assert "empezado ningún escrito" in _textos(cuerpo) or codigo != "es"
    e = es.crear_escrito(st.conn, st.plan_id, "Mi monografía", "monografia", 3000, autor="Ana")
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)                                   # el escrito
    assert len(_todos(cuerpo, ft.ListTile)) == 5          # sus cinco secciones
    _abrir(st, cuerpo)                                   # la primera sección
    assert any(c.multiline and c.min_lines == 14 for c in _todos(cuerpo, ft.TextField))
    assert e


def test_escribir_citar_guardar_y_ver_el_avance(st):
    from ui.views import escritor
    e = es.crear_escrito(st.conn, st.plan_id, "Ensayo", "ensayo", 1000)
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)
    _abrir(st, cuerpo)
    texto = next(c for c in _todos(cuerpo, ft.TextField) if c.multiline and c.min_lines == 14)
    texto.value = "El transporte importa."
    texto.on_change(None)
    assert "3 de 150 palabras" in _textos(cuerpo)         # la meta de la sección sale del reparto de 1000 palabras
    _boton(cuerpo, "Insertar cita").on_click(None)
    assert texto.value.endswith("[@ruiz2021]")
    _boton(cuerpo, "Guardar").on_click(None)
    assert es.seccion(st.conn, es.secciones(st.conn, e)[0]["id"])["texto"] == "El transporte importa. [@ruiz2021]"
    _boton(cuerpo, "Revisar redacción").on_click(None)
    assert "Llevas" in _textos(cuerpo)
    next(b for b in _todos(cuerpo, ft.IconButton) if b.tooltip == "Volver al escrito").on_click(None)
    assert "(Ruiz, 2021)" not in _textos(cuerpo) and "palabras (" in _textos(cuerpo)


def test_vista_previa_exportar_y_copiar(st, tmp_path):
    from database.db import DATOS
    from ui.views import escritor
    e = es.crear_escrito(st.conn, st.plan_id, "Mi ensayo", "ensayo", 1000, autor="Ana")
    es.editar_seccion(st.conn, es.secciones(st.conn, e)[0]["id"], texto="Dato clave [@ruiz2021, p. 3].")
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)
    _boton(cuerpo, "Copiar texto").on_click(None)
    assert "Dato clave (Ruiz, 2021, p. 3)." in st.page.portapapeles and "## Referencias" in st.page.portapapeles
    _boton(cuerpo, "Vista previa").on_click(None)
    assert any(isinstance(d, ft.AlertDialog) for d in st.page.abiertos)
    formato = next(d for d in _todos(cuerpo, ft.Dropdown) if d.label == "Exportar como")
    for fmt in ("md", "html", "docx"):
        formato.value = fmt
        _boton(cuerpo, "Exportar").on_click(None)
        ruta = next(x.value for x in _todos(cuerpo, ft.Text) if "Exportado en" in str(x.value)).split(": ", 1)[1]
        assert ruta.endswith("." + fmt) and str(DATOS) in ruta and open(ruta, "rb").read(2)


def test_cambiar_el_estilo_de_cita_recompila(st):
    from ui.views import escritor
    e = es.crear_escrito(st.conn, st.plan_id, "Ensayo", "ensayo")
    es.editar_seccion(st.conn, es.secciones(st.conn, e)[0]["id"], texto="Algo [@ruiz2021].")
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)
    estilo = next(d for d in _todos(cuerpo, ft.Dropdown) if d.label == "Estilo de citas")
    estilo.value = "numerico"
    estilo.on_change(type("E", (), {"control": estilo})())
    assert es.escrito(st.conn, e)["estilo"] == "numerico" and "[1]" in es.a_markdown(es.compilar(st.conn, e))


def test_fuentes_y_borrador_con_ia(st, tmp_path, monkeypatch):
    from ui.views import escritor
    f = tmp_path / "informe.md"
    f.write_text("El transporte escolar reduce la deserción en un doce por ciento en el altiplano boliviano.\n" * 3, encoding="utf-8")
    h = mat.hash_archivo(str(f))
    mid = repo.agregar_material(st.conn, st.plan_id, "Informe", "md", h, "informe.md", str(f), 10)
    lid = repo.lecturas(st.conn, st.plan_id)[0]["id"]
    repo.editar_lectura(st.conn, lid, material_id=mid, hallazgos="El transporte escolar reduce la deserción")
    e = es.crear_escrito(st.conn, st.plan_id, "Transporte escolar y deserción", "ensayo")
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)
    _abrir(st, cuerpo)
    _boton(cuerpo, "Fuentes para esta sección").on_click(None)
    assert "Fuentes relacionadas" in _textos(cuerpo)
    _boton(cuerpo, "Citar").on_click(None)
    assert "[@ruiz2021]" in next(c for c in _todos(cuerpo, ft.TextField) if c.multiline and c.min_lines == 14).value
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)
    monkeypatch.setattr(es, "borrador_ia", lambda *a, **k: {"texto": "El transporte reduce la deserción [@ruiz2021].", "sin_registrar": ["Otro · p. 2"],
                                                           "sin_fuentes": False, "no_alcanza": False})
    _boton(cuerpo, "Borrador con IA").on_click(None)
    dlg = st.page.abiertos[-1]
    dlg.actions[-1].on_click(None)                       # «Redactar»
    assert "BORRADOR de la IA" in _textos(cuerpo) and "Otro · p. 2" in _textos(cuerpo)
    _boton(cuerpo, "Insertar al final").on_click(None)
    assert next(c for c in _todos(cuerpo, ft.TextField) if c.multiline and c.min_lines == 14).value.count("[@ruiz2021]") == 2
    assert e


def test_mover_y_borrar_secciones_desde_la_pantalla(st):
    from ui.views import escritor
    e = es.crear_escrito(st.conn, st.plan_id, "Ensayo", "ensayo")
    primera = es.secciones(st.conn, e)[0]["id"]
    cuerpo = escritor.build(st, indice=st.idx)
    _abrir(st, cuerpo)
    _abrir(st, cuerpo)
    _boton(cuerpo, "Bajar").on_click(None)
    assert es.secciones(st.conn, e)[1]["id"] == primera
    _abrir(st, cuerpo, 1)
    _boton(cuerpo, "Borrar sección").on_click(None)
    st.page.abiertos[-1].actions[-1].on_click(None)       # confirmar «Sí, borrar»
    assert len(es.secciones(st.conn, e)) == 5


def test_sin_asignatura_avisa(st):
    from ui.views import escritor
    st.plan_id = None
    assert isinstance(escritor.build(st), ft.Text)

