"""Pomodoro global, «Tu sesión de hoy», enlaces/imágenes en Material y el botón Atrás."""
import base64
from datetime import date

import flet as ft
import pytest

from database import db, repo
from engine import estudios, material as mat
from ui.state import AppState
from ui.views import estudio, hoy
from ui.views import material as vista_material
from tests.test_menu import _arrancar, _cuerpo, _todos as _todos_menu


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web = [], ft.PagePlatform.LINUX, 1000, True
        self.abiertos, self.urls = [], []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def launch_url(self, url, *a, **k): self.urls.append(url)


def _todos(control, tipo):
    out, pila = [], [control]
    while pila:
        x = pila.pop()
        if isinstance(x, tipo):
            out.append(x)
        for atr in ("controls", "content", "leading", "trailing", "title", "subtitle", "items"):
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
    s.plan_id = repo.crear_plan(s.conn, "Máster", s.perfil_id)
    u = repo.agregar_unidad(s.conn, s.plan_id, "Módulo 1")
    s.t1 = repo.agregar_tema(s.conn, u, "Competencia global")
    repo.agregar_tema(s.conn, u, "Finanzas")
    return s


def test_el_pomodoro_vive_en_el_estado_y_registra_la_sesion(st, monkeypatch):
    monkeypatch.setattr(AppState, "_arrancar_ticker", lambda self: None)          # sin hilo: se avanza a mano
    st.iniciar_pomodoro(st.t1, "Competencia global")
    assert st.pomodoro.activo and st.tema_id == st.t1
    st.pomodoro._fin -= 10_000                                                    # «pasa el tiempo»
    for ev in st.pomodoro.avanzar():
        repo.registrar_sesion(st.conn, ev[1], ev[2])
    assert st.conn.execute("SELECT SUM(minutos) FROM sesiones").fetchone()[0] > 0


def test_la_pantalla_estudiar_refleja_el_pomodoro_en_marcha_aunque_se_reconstruya(st, monkeypatch):
    monkeypatch.setattr(AppState, "_arrancar_ticker", lambda self: None)
    st.iniciar_pomodoro(st.t1, "Competencia global")
    cuerpo = estudio.build(st)                      # el usuario vuelve a la pantalla después de navegar
    assert "Competencia global" in _textos(cuerpo)
    assert any(c.value and c.value.count(":") == 1 and c.size == 48 and c.value != "00:00" for c in _todos(cuerpo, ft.Text))
    pausa = next(b for b in _todos(cuerpo, ft.OutlinedButton) if b.text == "Pausar")
    pausa.on_click(None)
    assert st.pomodoro.pausado
    st.al_tick[-1]()
    assert any(b.text == "Reanudar" for b in _todos(cuerpo, ft.OutlinedButton))


def test_hoy_ofrece_la_sesion_y_empezar_arranca_el_pomodoro(st, monkeypatch):
    monkeypatch.setattr(AppState, "_arrancar_ticker", lambda self: None)
    saltos = []
    cuerpo = hoy.build(st, lambda: saltos.append("estudiar"), lambda: None, ir_material=lambda: saltos.append("material"))
    txt = _textos(cuerpo)
    assert "Tu sesión de hoy" in txt and "Estudia: Competencia global" in txt
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if (b.text or "").startswith("▶ Empezar ahora")).on_click(None)
    assert st.pomodoro.activo and st.pomodoro.titulo == "Competencia global" and saltos == ["estudiar"]
    assert "Sesión en curso" in _textos(hoy.build(st, lambda: None, lambda: None))


def test_hoy_propone_seguir_leyendo_el_documento_a_medias(st, tmp_path):
    f = tmp_path / "libro.txt"
    f.write_text("\n\n".join(f"Párrafo {i} " + "palabra " * 300 for i in range(6)), encoding="utf-8")
    h = mat.hash_archivo(str(f))
    mid = repo.agregar_material(st.conn, st.plan_id, "Libro", "txt", h, "libro.txt", str(f), f.stat().st_size)
    repo.progreso_lectura(st.conn, mid, 2, 5)
    assert estudios.lectura_pendiente(st.conn, st.plan_id)["id"] == mid
    saltos = []
    cuerpo = hoy.build(st, lambda: None, lambda: None, ir_material=lambda: saltos.append(1))
    fila = next(x for x in _todos(cuerpo, ft.ListTile) if "Sigue leyendo: Libro" in str(getattr(x.title, "value", "")))
    fila.on_click(None)
    assert st.abrir_material == (mid, 2) and saltos == [1]


def test_proximo_tema_prefiere_lo_atrasado(st):
    ayer = "2020-01-01"
    st.conn.execute("UPDATE temas SET fecha_programada=? WHERE titulo='Finanzas'", (ayer,))
    st.conn.commit()
    assert estudios.proximo_tema(st.conn, st.plan_id, date.today().isoformat())["titulo"] == "Finanzas"


def test_un_enlace_se_guarda_y_al_tocarlo_se_abre_en_el_navegador(st):
    cuerpo = vista_material.build(st, lambda: None)
    campos = {x.label: x for x in _todos(cuerpo, ft.TextField)}
    campos["Enlace (página web, vídeo, documento en línea…)"].value = "ejemplo.com/articulo"
    campos["Nombre (opcional)"].value = "Artículo clave"
    next(b for b in _todos(cuerpo, ft.OutlinedButton) if "Añadir enlace" in (b.text or "")).on_click(None)
    m = repo.materiales(st.conn, st.plan_id)[0]
    assert m["tipo"] == "enlace" and m["titulo"] == "Artículo clave" and m["nombre_archivo"] == "https://ejemplo.com/articulo"
    fila = next(x for x in _todos(cuerpo, ft.ListTile) if getattr(x.title, "value", "") == "Artículo clave")
    fila.on_click(None)
    assert st.page.urls == ["https://ejemplo.com/articulo"]


def test_un_texto_que_no_es_enlace_se_rechaza_y_los_duplicados_no_se_repiten(st):
    cuerpo = vista_material.build(st, lambda: None)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if x.label.startswith("Enlace"))
    boton = next(b for b in _todos(cuerpo, ft.OutlinedButton) if "Añadir enlace" in (b.text or ""))
    campo.value = "hola mundo"
    boton.on_click(None)
    assert repo.materiales(st.conn, st.plan_id) == []
    for _ in range(2):
        campo.value = "https://x.org/a"
        boton.on_click(None)
    assert len(repo.materiales(st.conn, st.plan_id)) == 1


def test_una_imagen_se_lee_dentro_de_la_app(st, tmp_path):
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")
    f = tmp_path / "esquema.png"
    f.write_bytes(png)
    assert mat.tipo_de(str(f)) == "imagen"
    mid = repo.agregar_material(st.conn, st.plan_id, "Esquema", "imagen", mat.hash_archivo(str(f)), "esquema.png", str(f), len(png))
    st.abrir_material = (mid, 1)
    cuerpo = vista_material.build(st, lambda: None)
    assert _todos(cuerpo, ft.Image)
    assert not any("Con IA" in (b.text or "") for b in _todos(cuerpo, ft.OutlinedButton))


def test_url_normalizar():
    assert mat.normalizar_url("ejemplo.com/a") == "https://ejemplo.com/a"
    assert mat.normalizar_url("http://x.org") == "http://x.org"
    assert mat.normalizar_url("hola mundo") is None and mat.normalizar_url("archivo.pdf") is None


def test_el_boton_atras_vuelve_a_donde_estabas(monkeypatch):
    p = _arrancar(monkeypatch)
    rail = next(c for c in _todos_menu(p.controles[0], ft.NavigationRail))
    cuerpo = _cuerpo(p)
    atras = next(b for b in _todos_menu(p.controles[0], ft.IconButton) if b.tooltip == "Atrás")
    assert not atras.visible
    rail.selected_index = 3
    rail.on_change(type("E", (), {"control": rail})())            # Más
    menu = cuerpo.content
    _todos_menu(menu, ft.ListTile)[0].on_click(None)              # una opción del menú
    assert atras.visible and cuerpo.content is not menu
    atras.on_click(None)                                          # volver
    assert [x.title.value for x in _todos_menu(cuerpo.content, ft.ListTile)][:1] == [x.title.value for x in _todos_menu(menu, ft.ListTile)][:1]
    assert not atras.visible


def test_un_archivo_se_adjunta_a_una_unidad_y_aparece_en_sus_recursos(st, tmp_path, monkeypatch):
    from ui.views import plan as vista_plan
    st.page.overlay = []
    monkeypatch.setattr(ft.FilePicker, "pick_files", lambda self, **k: None)      # la ventana del sistema no existe en la prueba
    f = tmp_path / "temario.txt"
    f.write_text("Contenido del temario " * 50, encoding="utf-8")
    recargas, saltos = [], []
    cuerpo = vista_plan.build(st, lambda: None, lambda: recargas.append(1), lambda: saltos.append(1))
    boton = next(b for b in _todos(cuerpo, ft.TextButton) if b.text == "＋ Archivo")
    boton.on_click(None)
    picker = st.page.overlay[-1]
    picker.on_result(type("E", (), {"files": [type("F", (), {"path": str(f)})()]})())
    unidad = repo.unidades(st.conn, st.plan_id)[0]
    m = st.conn.execute("SELECT * FROM materiales WHERE unidad_id=?", (unidad["id"],)).fetchone()
    assert m["titulo"] == "temario" and recargas
    cuerpo = vista_plan.build(st, lambda: None, lambda: None, lambda: saltos.append(1))      # el plan se redibuja con el archivo
    fila = next(x for x in _todos(cuerpo, ft.ListTile) if getattr(x.title, "value", "") == "temario")
    fila.on_click(None)
    assert st.abrir_material == (m["id"], 1) and saltos == [1]


def _pulsa(p, cuerpo, texto):
    b = next(b for b in _todos_menu(cuerpo.content, (ft.ElevatedButton, ft.OutlinedButton, ft.FilledButton)) if b.text == texto)
    b.on_click(None)


def test_flujo_completo_carpeta_estudio_y_sus_pestanas(monkeypatch):
    p = _arrancar(monkeypatch)
    rail = next(c for c in _todos_menu(p.controles[0], ft.NavigationRail))
    cuerpo = _cuerpo(p)
    assert [d.label for d in rail.destinations] == ["Hoy", "Estudios", "Repaso", "Más"]
    rail.selected_index = 1
    rail.on_change(type("E", (), {"control": rail})())               # lista «Mis estudios»
    _pulsa(p, cuerpo, "Abrir plan completo")                          # entra al estudio «Biología»
    assert rail.selected_index == 1                                   # dentro de un estudio sigue marcada «Estudios»
    for pestana, esperado in (("Material", "Adjunta tus libros"), ("Estudiar", "Estudiar"), ("Repaso", "Repaso"), ("Temario", "U1")):
        _pulsa(p, cuerpo, pestana)
        assert any(esperado in str(getattr(x, "value", "") or getattr(x, "title", "")) or esperado in str(getattr(getattr(x, "title", None), "value", ""))
                   for x in _todos_menu(cuerpo.content, (ft.Text, ft.ExpansionTile))), pestana
    next(b for b in _todos_menu(cuerpo.content, ft.IconButton) if b.tooltip == "Mis estudios").on_click(None)    # salir del estudio
    assert any("Abrir plan completo" == getattr(b, "text", None) for b in _todos_menu(cuerpo.content, (ft.ElevatedButton, ft.OutlinedButton)))
