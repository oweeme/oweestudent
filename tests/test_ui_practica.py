"""Pantallas de Práctica activa y de Exportar a Anki (con una página falsa)."""
import threading
import zipfile

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import practica as pr


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.portapapeles = [], ft.PagePlatform.LINUX, 1000, None
        self.web = True          # sin diálogo «Guardar como…»: va a la carpeta de exportaciones

    def update(self, *a): pass
    def open(self, x): pass
    def close(self, *a): pass
    def set_clipboard(self, x): self.portapapeles = x
    def launch_url(self, *a): pass


class _Hilo:
    """Ejecuta los hilos al instante, salvo el cronómetro (que no termina nunca)."""
    def __init__(self, target=None, args=(), daemon=None):
        self.target, self.args = target, args

    def start(self):
        if self.target.__name__ != "cuenta":
            self.target(*self.args)


@pytest.fixture(autouse=True)
def _entorno(monkeypatch):
    i18n.fijar_idioma("es")
    monkeypatch.setattr(threading, "Thread", _Hilo)
    yield
    i18n.fijar_idioma("es")


@pytest.fixture
def st():
    from ui.state import AppState
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = repo.crear_plan(s.conn, "Biología", s.perfil_id)
    u = repo.agregar_unidad(s.conn, s.plan_id, "Módulo 1")
    s.tema = repo.agregar_tema(s.conn, u, "Fotosíntesis")
    repo.crear_tarjetas(s.conn, s.tema, [
        ("¿Qué es la fotosíntesis?", "Proceso que convierte luz en energía química"),
        ("¿Dónde ocurre?", "En los cloroplastos de las células vegetales"),
        ("¿Qué pigmento absorbe la luz?", "La clorofila, un pigmento verde"),
        ("¿Qué produce la respiración?", "Energía en forma de ATP"),
        ("¿Qué guarda el ADN?", "La información genética")], "manual")
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


def _boton(control, texto):
    return next(b for b in _todos(control, (ft.ElevatedButton, ft.OutlinedButton, ft.TextButton)) if texto in str(b.text))


@pytest.mark.parametrize("codigo", ["es", "en", "ru", "ja"])
def test_la_pantalla_de_practica_se_construye_en_todos_los_idiomas(st, codigo):
    from ui.views import practica
    i18n.fijar_idioma(codigo)
    cuerpo = practica.build(st)
    tabs = next(c for c in _todos(cuerpo, ft.Tabs))
    assert len(tabs.tabs) == 4


def test_sin_asignatura_o_sin_temas_avisa(st):
    from ui.views import practica
    st.plan_id = None
    assert isinstance(practica.build(st), ft.Text)
    st.plan_id = repo.crear_plan(st.conn, "Vacía", st.perfil_id)
    assert isinstance(practica.build(st), ft.Text)


def test_recuperacion_libre_compara_y_guarda_con_repaso(st):
    from ui.views import practica
    cuerpo = practica.build(st)
    tab = _todos(cuerpo, ft.Tabs)[0].tabs[0].content
    campo = next(c for c in _todos(tab, ft.TextField) if c.multiline and "recuerdas" in c.label)
    campo.value = "La fotosíntesis convierte la luz en energía en los cloroplastos con la clorofila"
    _boton(tab, "Comparar").on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "% de las palabras clave" in textos
    chips = _todos(tab, ft.Chip)
    assert chips and any(isinstance(c.leading, ft.Icon) and c.leading.name == ft.Icons.CHECK for c in chips)
    _boton(tab, "Guardar").on_click(None)
    assert st.conn.execute("SELECT COUNT(*) FROM notas WHERE tema_id=?", (st.tema,)).fetchone()[0] == 1
    p = pr.historial(st.conn, st.plan_id, "recuperacion")[0]
    assert p["puntaje"] == 60 and p["tema_id"] == st.tema                       # autoevaluación 3 de 5


def test_recuperacion_sin_texto_o_sin_referencia_avisa(st):
    from ui.views import practica
    cuerpo = practica.build(st)
    tab = _todos(cuerpo, ft.Tabs)[0].tabs[0].content
    _boton(tab, "Comparar").on_click(None)
    assert "Primero escribe" in cuerpo.controls[1].value
    st.conn.execute("DELETE FROM tarjetas"); st.conn.commit()
    campo = next(c for c in _todos(tab, ft.TextField) if c.multiline and "recuerdas" in c.label)
    campo.value = "algo"
    _boton(tab, "Comparar").on_click(None)
    assert "No tengo con qué comparar" in cuerpo.controls[1].value


def test_recuperacion_con_ia_muestra_lo_que_falta(st, monkeypatch):
    from engine import ai
    from ui.views import practica
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)
    monkeypatch.setattr(pr, "evaluar_recuperacion_ia", lambda r, x: {"correcto": ["Dijo la luz"], "falta": ["La glucosa"], "errores": []})
    cuerpo = practica.build(st)
    tab = _todos(cuerpo, ft.Tabs)[0].tabs[0].content
    next(c for c in _todos(tab, ft.TextField) if c.multiline and "recuerdas" in c.label).value = "la luz"
    _boton(tab, "Comparar").on_click(None)
    _boton(tab, "Evaluar con IA").on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "La glucosa" in textos and "Dijo la luz" in textos


def test_feynman_revisa_localmente_y_con_ia(st, monkeypatch):
    from engine import ai
    from ui.views import practica
    monkeypatch.setattr(ai, "ia_disponible", lambda: True)
    monkeypatch.setattr(pr, "revisar_explicacion_ia", lambda e, r, edad=12: {"claro": ["La idea de luz"], "huecos": ["¿Qué es clorofila?"], "preguntas": ["¿Y de noche?"]})
    cuerpo = practica.build(st)
    tab = _todos(cuerpo, ft.Tabs)[0].tabs[1].content
    campo = next(c for c in _todos(tab, ft.TextField) if c.multiline and "12 años" in c.label)
    campo.value = "Las plantas hacen fotosintetizacion extraordinariamente complicada."
    _boton(tab, "Revisar mi explicación").on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "muy corta" in textos and "Palabras técnicas" in textos and "extraordinariamente" in textos
    _boton(tab, "Revisar con la IA").on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "¿Y de noche?" in textos and "clorofila" in textos
    _boton(tab, "Guardar").on_click(None)
    assert pr.historial(st.conn, st.plan_id, "feynman")


def _simulacro(st, tipo="opciones", n="5"):
    from ui.views import practica
    cuerpo = practica.build(st)
    tab = _todos(cuerpo, ft.Tabs)[0].tabs[2].content
    for dd in _todos(tab, ft.Dropdown):
        if dd.label == "Tipo de preguntas":
            dd.value = tipo
        if dd.label == "Preguntas":
            dd.value = n
    return cuerpo, tab


def test_simulacro_de_opcion_multiple_de_principio_a_fin(st):
    cuerpo, tab = _simulacro(st, "opciones", "5")
    _boton(tab, "Empezar").on_click(None)
    for _ in range(5):
        grupo = next(g for g in _todos(tab, ft.RadioGroup))
        correcta = None
        pregunta = next(x for x in _todos(tab, ft.Text) if x.value and x.value.startswith("¿"))
        fila = st.conn.execute("SELECT respuesta FROM tarjetas WHERE pregunta=?", (pregunta.value,)).fetchone()
        correcta = fila["respuesta"]
        grupo.value = correcta
        grupo.on_change(type("E", (), {"control": grupo})())
        botones = [b for b in _todos(tab, (ft.ElevatedButton, ft.OutlinedButton)) if b.text in ("Siguiente", "Terminar")]
        botones[-1].on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "100%" in textos and "Sin errores" in textos
    assert pr.historial(st.conn, st.plan_id, "simulacro")[0]["puntaje"] == 100
    assert st.conn.execute("SELECT COUNT(*) FROM repasos_log").fetchone()[0] == 0


def test_simulacro_con_errores_reprograma_y_los_muestra(st):
    cuerpo, tab = _simulacro(st, "abierta", "5")
    _boton(tab, "Empezar").on_click(None)
    for _ in range(5):
        _boton(tab, "Mostrar respuesta").on_click(type("E", (), {"control": _boton(tab, "Mostrar respuesta")})())
        _boton(tab, "Fallé").on_click(None)
    textos = " ".join(str(x.value) for x in _todos(tab, ft.Text))
    assert "0%" in textos and "5 tarjetas falladas vuelven" in textos and "Correcta:" in textos
    assert st.conn.execute("SELECT COUNT(*) FROM repasos_log WHERE calidad=1").fetchone()[0] == 5


def test_simulacro_sin_tarjetas_avisa(st):
    st.conn.execute("DELETE FROM tarjetas"); st.conn.commit()
    cuerpo, tab = _simulacro(st)
    _boton(tab, "Empezar").on_click(None)
    assert "No hay tarjetas para examinarte" in cuerpo.controls[1].value


def test_exportar_apkg_y_csv(st):
    from database.db import DATOS
    from ui.views import exportar
    cuerpo = exportar.build(st)
    assert "5 tarjetas para exportar" in " ".join(str(x.value) for x in _todos(cuerpo, ft.Text))
    _boton(cuerpo, "Exportar").on_click(None)
    ruta = next(x.value for x in _todos(cuerpo, ft.Text) if "Exportado en" in str(x.value)).split(": ", 1)[1]
    assert ruta.endswith(".apkg") and zipfile.is_zipfile(ruta) and str(DATOS) in ruta
    formato = next(d for d in _todos(cuerpo, ft.Dropdown) if d.label == "Formato")
    formato.value = "csv"
    formato.on_change(None)
    _boton(cuerpo, "Exportar").on_click(None)
    ruta = next(x.value for x in _todos(cuerpo, ft.Text) if "Exportado en" in str(x.value)).split(": ", 1)[1]
    assert ruta.endswith(".tsv") and "¿Qué es la fotosíntesis?" in open(ruta, encoding="utf-8").read()


def test_exportar_sin_tarjetas_avisa(st):
    from ui.views import exportar
    st.conn.execute("DELETE FROM tarjetas"); st.conn.commit()
    cuerpo = exportar.build(st)
    _boton(cuerpo, "Exportar").on_click(None)
    assert any("No hay tarjetas que exportar" in str(x.value) for x in _todos(cuerpo, ft.Text))


def test_en_escritorio_pide_donde_guardar_y_escribe_donde_se_elige(st, tmp_path):
    from ui.views import exportar
    st.page.web = False
    pedidos = []

    class Selector:
        def __init__(self, on_result=None):
            self.on_result = on_result

        def save_file(self, **kw):
            pedidos.append(kw)
    import flet
    original, flet.FilePicker = flet.FilePicker, Selector
    try:
        cuerpo = exportar.build(st)
    finally:
        flet.FilePicker = original
    _boton(cuerpo, "Exportar").on_click(None)
    assert pedidos and pedidos[0]["file_name"].endswith(".apkg") and pedidos[0]["allowed_extensions"] == ["apkg"]
    elegido = tmp_path / "mis_tarjetas"                       # sin extensión: la app la añade
    st.page.overlay[-1].on_result(type("E", (), {"path": str(elegido)})())
    assert (tmp_path / "mis_tarjetas.apkg").exists() and zipfile.is_zipfile(tmp_path / "mis_tarjetas.apkg")
    st.page.overlay[-1].on_result(type("E", (), {"path": None})())      # cancelar: no pasa nada
