"""Escribir en Owee Script dentro de la app: teclado de sílabas, taller libre y práctica por rondas."""
import random

import flet as ft
import pytest

from database import db, repo
from engine import escritura_owee as motor
from i18n import owee
from owee_curso import curso
from ui.state import AppState
from ui.views import escribir_owee


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web, self.copiado = [], ft.PagePlatform.LINUX, 1000, True, None

    def update(self, *a): pass
    def open(self, x): pass
    def close(self, *a): pass
    def set_clipboard(self, x): self.copiado = x


def _todos(control, tipo):
    out, pila = [], [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "items", "label"):
            h = getattr(x, atr, None)
            if isinstance(h, list):
                pila += reversed(h)
            elif isinstance(h, ft.Control):
                pila.append(h)
    return out


def _textos(c):
    return " ".join(str(x.value) for x in _todos(c, ft.Text) if x.value)


@pytest.fixture
def st():
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = curso.crear_plan_del_curso(s.conn, s.perfil_id)
    return s


def tecla(cuerpo, romano):
    """La tecla del teclado de sílabas con ese romano."""
    return next(c for c in _todos(cuerpo, ft.Container) if c.on_click and isinstance(c.content, ft.Column)
                and any(getattr(x, "value", None) == romano for x in c.content.controls))


def boton(cuerpo, texto):
    return next(b for b in _todos(cuerpo, (ft.ElevatedButton, ft.OutlinedButton)) if b.text == texto)


# ---------- motor ----------
def test_las_palabras_de_practica_tienen_significado_y_son_owee_valido():
    pool = motor.palabras()
    assert len(pool) > 100 and ("suna", "agua") in pool
    assert all(owee.valida(w.replace("-", "")) and s for w, s in pool)
    assert len(motor.palabras("0.3")) < len(pool)           # solo hasta la lección indicada


def test_la_ronda_mezcla_los_tres_modos_sin_repetir_palabras():
    r = motor.ronda(motor.palabras(), 5, random.Random(1))
    assert len(r) == 5 and len({q["palabra"] for q in r}) == 5
    assert [q["modo"] for q in r] == ["es_a_owee", "glifo_a_owee", "glifo_a_romano", "es_a_owee", "glifo_a_owee"]


def test_comprobar_ignora_mayusculas_espacios_y_guiones():
    assert motor.comprobar("Sade-Kelo", "sadekelo") and motor.comprobar(" suna ", "suna")
    assert not motor.comprobar("sune", "suna") and not motor.comprobar("", "suna")


def test_el_teclado_tiene_las_56_silabas_las_vocales_y_los_digitos():
    k = motor.teclas()
    assert sum(len(f) for f in k["silabas"]) == 56 and k["vocales"] == list("aeou") and len(k["digitos"]) == 10


# ---------- taller libre ----------
def test_el_taller_convierte_lo_que_tecleas_en_glifos_y_lo_copia(st):
    cuerpo = escribir_owee.build(st)
    for s in ("su", "na"):
        tecla(cuerpo, s).on_click(None)
    visor = next(x for x in _todos(cuerpo, ft.Text) if x.font_family and x.size == 44)
    assert visor.value == owee.a_escritura("suna") and owee.tiene_glifos(visor.value)
    assert "suna" in _textos(cuerpo)
    boton(cuerpo, "⌫ Borrar").on_click(None)
    assert visor.value == owee.a_escritura("su")
    boton(cuerpo, "Copiar en escritura Owee").on_click(None)
    assert st.page.copiado == owee.a_escritura("su")
    boton(cuerpo, "Limpiar").on_click(None)
    assert visor.value == ""


def test_escribir_en_romano_tambien_dibuja_los_glifos(st):
    cuerpo = escribir_owee.build(st)
    campo = next(x for x in _todos(cuerpo, ft.TextField))
    campo.value = "mune"
    campo.on_change(None)
    visor = next(x for x in _todos(cuerpo, ft.Text) if x.font_family and x.size == 44)
    assert visor.value == owee.a_escritura("mune")


# ---------- práctica ----------
def _practica(st, monkeypatch, preguntas):
    monkeypatch.setattr(motor, "ronda", lambda pool, n=5, rng=None: preguntas)
    cuerpo = escribir_owee.build(st)
    seg = next(x for x in _todos(cuerpo, ft.SegmentedButton))
    seg.on_change(type("E", (), {"control": type("C", (), {"selected": {"practica"}})()})())
    return cuerpo


def test_la_practica_acepta_la_palabra_bien_escrita_y_cuenta_el_resultado(st, monkeypatch):
    q = [{"palabra": "suna", "significado": "agua", "modo": "es_a_owee"}]
    cuerpo = _practica(st, monkeypatch, q)
    assert "Escribe en Owee: «agua»" in _textos(cuerpo)
    tecla(cuerpo, "su").on_click(None)
    tecla(cuerpo, "na").on_click(None)
    boton(cuerpo, "Comprobar").on_click(None)
    assert "✅ Correcto" in _textos(cuerpo)
    boton(cuerpo, "Siguiente").on_click(None)
    assert "Resultado: 1 de 1" in _textos(cuerpo)


def test_un_fallo_muestra_la_respuesta_y_vuelve_en_el_repaso(st, monkeypatch):
    q = [{"palabra": "suna", "significado": "agua", "modo": "glifo_a_owee"}]
    cuerpo = _practica(st, monkeypatch, q)
    tecla(cuerpo, "ka").on_click(None)
    boton(cuerpo, "Comprobar").on_click(None)
    assert "❌ Era: suna" in _textos(cuerpo)
    boton(cuerpo, "Siguiente").on_click(None)
    assert "Resultado: 0 de 1" in _textos(cuerpo) and "«Repaso»" in _textos(cuerpo)
    pendientes = repo.tarjetas_pendientes(st.conn, st.perfil_id, st.plan_id)
    assert {k["respuesta"] for k in pendientes} >= {"agua", curso.MARCA_OWEE + "suna"}


def test_leer_el_glifo_se_responde_en_romano_sin_teclado(st, monkeypatch):
    q = [{"palabra": "mune", "significado": "luna", "modo": "glifo_a_romano"}]
    cuerpo = _practica(st, monkeypatch, q)
    assert "Lee y escribe en romano" in _textos(cuerpo)
    assert not any(c.on_click and isinstance(c.content, ft.Column) and any(getattr(x, "value", None) == "ka" for x in c.content.controls)
                   for c in _todos(cuerpo, ft.Container))                      # esta modalidad no lleva teclado
    campo = next(x for x in _todos(cuerpo, ft.TextField))
    campo.value = "mune"
    campo.on_change(None)
    boton(cuerpo, "Comprobar").on_click(None)
    assert "✅ Correcto" in _textos(cuerpo)


# ---------- artículo ----------
def _vista_articulo(st):
    cuerpo = escribir_owee.build(st)
    seg = next(x for x in _todos(cuerpo, ft.SegmentedButton))
    seg.on_change(type("E", (), {"control": type("C", (), {"selected": {"articulo"}})()})())
    return cuerpo


def test_valorar_detecta_palabras_imposibles_desconocidas_y_nombres():
    v = motor.valorar("Ana sade-kelo suna. Mune pore ximi! kuma kuma bado-kopa-meka? Sade suna nara.")
    assert v["invalidas"] == ["ximi"] and v["nombres"] == 1 and v["oraciones"] == 4
    assert v["cobertura"] == 1.0 and v["nivel"] is not None and 0 < v["variedad"] < 1
    v = motor.valorar("suna pupupupu")
    assert v["desconocidas"] == ["pupupupu"] and v["cobertura"] == 0.5
    assert motor.valorar("")["palabras"] == 0


def test_crear_un_articulo_escribir_y_valorarlo(st):
    cuerpo = _vista_articulo(st)
    assert "Aún no tienes artículos" in _textos(cuerpo)
    next(x for x in _todos(cuerpo, ft.TextField) if x.label == "Título del artículo").value = "Mi primer texto"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if "Nuevo artículo" in (b.text or "")).on_click(None)
    assert "Mi primer texto" in _textos(cuerpo) and "Introducción y tesis" in " ".join(b.text for b in _todos(cuerpo, (ft.FilledButton, ft.OutlinedButton)))
    campo = next(x for x in _todos(cuerpo, ft.TextField) if x.multiline)
    campo.value = "sade suna. mune pore ximi"
    campo.on_change(None)
    art = escritor_articulos(st)[0]
    assert escritor_texto(st, art["id"]) == "sade suna. mune pore ximi"           # se guarda al escribir
    assert any(x.font_family and owee.a_escritura("sade") in (x.value or "") for x in _todos(cuerpo, ft.Text))   # y se ve en glifos
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Valorar mi texto").on_click(None)
    txt = _textos(cuerpo)
    assert "ximi" in txt and "No se pueden escribir en Owee" in txt and "5 palabras" in txt.replace("Tu texto: 5 palabras", "5 palabras")


def test_el_teclado_inserta_silabas_en_el_texto_del_articulo(st):
    cuerpo = _vista_articulo(st)
    next(x for x in _todos(cuerpo, ft.TextField) if x.label == "Título del artículo").value = "T"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if "Nuevo artículo" in (b.text or "")).on_click(None)
    tecla(cuerpo, "su").on_click(None)
    tecla(cuerpo, "na").on_click(None)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if x.multiline)
    assert campo.value == "suna"


def test_un_texto_limpio_recibe_el_visto_bueno_y_se_puede_copiar(st):
    cuerpo = _vista_articulo(st)
    next(x for x in _todos(cuerpo, ft.TextField) if x.label == "Título del artículo").value = "T"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if "Nuevo artículo" in (b.text or "")).on_click(None)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if x.multiline)
    campo.value = "sade suna. mune pore."
    campo.on_change(None)
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Valorar mi texto").on_click(None)
    assert "Sin errores de escritura" in _textos(cuerpo)
    boton(cuerpo, "Copiar en escritura Owee").on_click(None)
    assert owee.a_escritura("sade suna. mune pore.") in st.page.copiado


def escritor_articulos(st):
    from engine import escritura
    return escritura.escritos(st.conn, curso.plan_del_curso(st.conn, st.perfil_id))


def escritor_texto(st, art_id):
    from engine import escritura
    return escritura.secciones(st.conn, art_id)[0]["texto"]
