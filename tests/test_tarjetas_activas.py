"""Tarjetas con huecos y de producción, y el registro de qué tarjeta se falla."""
import flet as ft
import pytest

from database import db, repo
from engine import tarjetas as tj


def test_cloze_una_tarjeta_por_hueco():
    r = tj.cloze("La {{fotosíntesis}} ocurre en los {{cloroplastos}} de las plantas.")
    assert r == [("Completa: La _____ ocurre en los cloroplastos de las plantas.", "fotosíntesis"),
                 ("Completa: La fotosíntesis ocurre en los _____ de las plantas.", "cloroplastos")]
    assert tj.cloze("Sin huecos en esta frase larga.") == [] and tj.cloze("{{a}} b") == []        # frase demasiado corta


def test_desde_apuntes_acepta_llaves_y_las_demas_formas():
    texto = "La {{mitosis}} produce dos células hijas idénticas.\nÁtomo: unidad básica de la materia ordinaria.\nEl **ADN** guarda la información genética de cada ser vivo."
    p = [x[0] for x in tj.desde_apuntes(texto)]
    assert any("_____ produce dos células" in x for x in p) and any("«Átomo»" in x for x in p) and any("Completa: El _____ guarda" in x for x in p)


def test_huecos_automaticos_tapan_una_palabra_clave_por_frase():
    texto = ("La fotosíntesis es el proceso por el cual las plantas convierten la luz solar en energía química. "
             "La clorofila absorbe la luz y el proceso ocurre en los cloroplastos. La fotosíntesis produce glucosa y oxígeno.")
    r = tj.huecos_automaticos(texto, 5)
    assert len(r) >= 2 and all(p.startswith("Completa: ") and "_____" in p and respuesta.lower() not in p.lower() for p, respuesta in r)
    assert len({p for p, _ in r}) == len(r)                       # sin repetidas
    assert tj.huecos_automaticos("Frase corta.") == []


@pytest.mark.parametrize("escrita,correcta,esperado", [
    ("Cloroplastos", "cloroplastos", "correcta"), ("  la CLOROFILA! ", "La clorofila", "correcta"), ("Café", "cafe", "correcta"),
    ("clorplastos", "cloroplastos", "casi"), ("cloroplasto", "cloroplastos", "casi"),
    ("mitocondria", "cloroplastos", "fallo"), ("", "cloroplastos", "fallo"), ("ka", "[owee]ka", "correcta"), ("[glifo]ka", "ka", "correcta")])
def test_comparar_respuestas_escritas(escrita, correcta, esperado):
    r = tj.comparar(escrita, correcta)
    assert ("correcta" if r["correcta"] else "casi" if r["casi"] else "fallo") == esperado
    assert tj.sugerencia_de_nota(r) == {"correcta": 4, "casi": 3, "fallo": 1}[esperado]


def test_cada_repaso_guarda_su_tarjeta_para_el_diario_de_errores():
    c = db.init_db(":memory:")
    t = repo.tema_para_tarjetas(c, repo.crear_plan(c, "X", 1))
    repo.crear_tarjetas(c, t, [("a?", "a"), ("b?", "b")], "manual")
    a, b = [r["id"] for r in c.execute("SELECT id FROM tarjetas ORDER BY id")]
    repo.repasar_tarjeta(c, a, 1)
    repo.repasar_tarjeta(c, a, 4)
    repo.repasar_tarjeta(c, b, 0)
    assert [r[:] for r in c.execute("SELECT tarjeta_id, calidad FROM repasos_log ORDER BY id")] == [(a, 1), (a, 4), (b, 0)]


def test_una_base_anterior_recibe_la_columna_sin_perder_datos(tmp_path):
    ruta = str(tmp_path / "v5.db")
    c = db.init_db(ruta)
    t = repo.tema_para_tarjetas(c, repo.crear_plan(c, "X", 1))
    repo.crear_tarjetas(c, t, [("a?", "a")], "manual")
    c.execute("INSERT INTO repasos_log(tema_id,tipo,calidad) VALUES (?,?,?)", (t, "tarjeta", 2))
    c.execute("ALTER TABLE repasos_log DROP COLUMN tarjeta_id")
    c.execute("PRAGMA user_version=5")
    c.commit()
    c.close()
    c = db.init_db(ruta)
    assert "tarjeta_id" in [r["name"] for r in c.execute("PRAGMA table_info(repasos_log)")]
    assert c.execute("SELECT COUNT(*) FROM repasos_log").fetchone()[0] == 1 and c.execute("PRAGMA user_version").fetchone()[0] == db.VERSION_ESQUEMA


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web = [], ft.PagePlatform.LINUX, 1000, True

    def update(self, *a): pass
    def open(self, x): pass
    def close(self, *a): pass


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


@pytest.fixture
def st():
    from ui.state import AppState
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = repo.crear_plan(s.conn, "Idiomas", s.perfil_id)
    s.tema = repo.tema_para_tarjetas(s.conn, s.plan_id)
    return s


def test_repaso_de_produccion_pide_escribir_y_destaca_la_nota(st):
    from ui.views import repaso
    repo.crear_tarjetas(st.conn, st.tema, [("casa", "Haus")], "produccion")
    cuerpo = repaso.build(st)
    campo = next(c for c in _todos(cuerpo, ft.TextField) if c.label == "Escribe la respuesta")
    assert not any("Mostrar respuesta" in str(b.text) for b in _todos(cuerpo, ft.TextButton))      # no se puede mirar sin intentar
    campo.value = "haus"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Comprobar").on_click(None)
    assert any("Correcto" in str(x.value) for x in _todos(cuerpo, ft.Text))
    destacada = [b.text for b in _todos(cuerpo, ft.OutlinedButton) if b.style is not None]
    assert destacada == ["4"]


def test_repaso_de_produccion_con_fallo_sugiere_una_nota_baja(st):
    from ui.views import repaso
    repo.crear_tarjetas(st.conn, st.tema, [("casa", "Haus")], "produccion")
    cuerpo = repaso.build(st)
    next(c for c in _todos(cuerpo, ft.TextField) if c.label == "Escribe la respuesta").value = "maus"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Comprobar").on_click(None)
    assert [b.text for b in _todos(cuerpo, ft.OutlinedButton) if b.style is not None] in (["1"], ["3"])
    next(b for b in _todos(cuerpo, ft.OutlinedButton) if b.text == "1").on_click(None)             # el estudiante decide
    assert st.conn.execute("SELECT calidad FROM repasos_log").fetchone()[0] == 1


def test_las_tarjetas_normales_siguen_con_mostrar_respuesta(st):
    from ui.views import repaso
    repo.crear_tarjetas(st.conn, st.tema, [("¿Capital de Bolivia?", "Sucre y La Paz")], "manual")
    cuerpo = repaso.build(st)
    assert any("Mostrar respuesta" in str(b.text) for b in _todos(cuerpo, ft.TextButton))
    assert not any(c.label == "Escribe la respuesta" for c in _todos(cuerpo, ft.TextField) if c.visible)

