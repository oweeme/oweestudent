"""Simulacros de la certificación de Owee: datos, corrección y criterios de aprobado."""
import pytest

from database import db
from engine import certificacion_owee as cert
from i18n import owee
from owee_curso import curso
from owee_curso.examenes import EXAMENES, ORDEN


@pytest.fixture
def conn():
    return db.init_db(":memory:")


def test_los_puntos_de_cada_examen_coinciden_con_los_oficiales():
    totales = {k: sum(p["puntos"] for p in e["partes"]) for k, e in EXAMENES.items()}
    assert totales == {"semilla": 25, "brote": 25, "arbol": 50, "nivel0": 20, "nivel1": 50, "nivel2": 60, "nivel3": 70, "nivel4": 100}
    assert ORDEN == list(EXAMENES)


def test_toda_clave_automatica_es_owee_valido_y_todo_texto_a_leer_tambien():
    """La app no inventa Owee: lo que pide escribir y lo que muestra debe ser válido (o un número, letra o cifra)."""
    for e in EXAMENES.values():
        for p in e["partes"]:
            for it in p["items"]:
                for linea in it["owee"] + it["glifos"]:
                    for tok in linea.replace(",", " ").split():
                        assert tok.isdigit() or all(owee.valida(x) for x in tok.split("-")), (e["titulo"], tok)
                for auto in it["auto"] or []:
                    for tok in auto.replace(",", " ").split():
                        assert tok.isdigit() or len(tok) == 1 or all(owee.valida(x) for x in tok.split("-")), (e["titulo"], auto, tok)


def test_cada_item_automatico_se_corrige_y_cada_otro_tiene_clave():
    for e in EXAMENES.values():
        for p in e["partes"]:
            for it in p["items"]:
                if it["auto"]:
                    assert cert.acierta(it, it["auto"][0]) and not cert.acierta(it, "zzz")
                else:
                    assert it["clave"] or it["voz"] or it["valorar"], (e["titulo"], it["enunciado"])


def test_acierta_ignora_mayusculas_espacios_y_guiones():
    it = EXAMENES["nivel1"]["partes"][2]["items"][2]          # «Mi casa es grande»
    assert cert.acierta(it, "Me Kuma Gore-Pa") and cert.acierta(it, "me kuma gorepa") and not cert.acierta(it, "me kuma gore")
    assert not cert.acierta(it, "")


def test_aprobar_adultos_pide_70_por_ciento_y_50_por_parte():
    r = cert.evaluar("nivel1", {"A": 10, "B": 10, "C": 10, "D": 10, "E": 0})
    assert r["pct"] == 0.8 and not r["aprobado"] and r["flojas"] == ["Hablar"]          # 80 % pero una parte en 0
    r = cert.evaluar("nivel1", {"A": 7, "B": 7, "C": 7, "D": 7, "E": 7})
    assert r["pct"] == 0.7 and r["aprobado"]
    r = cert.evaluar("nivel1", {"A": 5, "B": 5, "C": 5, "D": 5, "E": 5})
    assert not r["aprobado"] and r["pct"] == 0.5                                          # 50 % en cada parte, pero no llega al 70 % total
    r = cert.evaluar("nivel1", {"A": 99, "B": 99, "C": 99, "D": 99, "E": 99})
    assert r["total"] == 50                                                               # no pasa del máximo


def test_aprobar_infantil_es_logrado_en_cada_parte():
    assert cert.evaluar("semilla", {"A": 3, "B": 3, "C": 3, "E": 3, "F": 3})["aprobado"]
    r = cert.evaluar("semilla", {"A": 3, "B": 2, "C": 3, "E": 3, "F": 3})
    assert not r["aprobado"] and r["flojas"] == ["Leer"]
    assert cert.evaluar("arbol", {"A": 6, "B": 6, "C": 6, "E": 6, "F": 6})["aprobado"]
    assert not cert.evaluar("arbol", {"A": 6, "B": 6, "C": 6, "E": 6, "F": 5})["aprobado"]


def test_guardar_y_recuperar_el_ultimo_resultado(conn):
    plan = curso.crear_plan_del_curso(conn, 1)
    cert.guardar(conn, plan, cert.evaluar("nivel0", {"A": 4, "B": 3, "C": 4, "D": 3, "F": 3}))
    cert.guardar(conn, plan, cert.evaluar("nivel0", {"A": 1, "B": 1, "C": 1, "D": 1, "F": 1}))
    u = cert.ultimos(conn, plan)
    assert u["nivel0"]["aprobado"] is False and u["nivel0"]["pct"] == 25 and "nivel1" not in u


def test_la_preparacion_sube_al_completar_lecciones(conn):
    plan = curso.crear_plan_del_curso(conn, 1)
    assert cert.preparacion(conn, plan, "nivel0") == 0
    for l in curso.lecciones():
        if l["nivel"] == 0:
            curso.marcar_leccion(conn, plan, l["id"], True)
    assert cert.preparacion(conn, plan, "nivel0") == 1
    assert 0 < cert.preparacion(conn, plan, "nivel1") < 1


def test_la_solicitud_de_examen_es_un_correo_para_revisar_y_enviar():
    m = cert.solicitud_mailto("nivel2")
    assert m.startswith("mailto:hector@oweeme.com?subject=Idioma%20Owee%3A%20examen%20de%20nivel") and "Nivel%202" in m


def test_revisar_articulo_para_maestro():
    texto = "me ga sade-kelo pe tase. te-fusu me tase nobe, balo-ke pu-fusu me pu tase ko ximi"
    r = cert.revisar_articulo(texto, 300)
    assert not r["extension_ok"] and not r["sin_errores"] and r["compuestos"] == ["balo-ke", "pu-fusu", "sade-kelo", "te-fusu"]
    assert r["pasado"] and r["futuro"] and "balo-ke" in r["enlaces"] and not r["listo"]
    largo = " ".join(["me tase suna"] * 110)
    assert cert.revisar_articulo(largo, 300)["listo"]


# ---------- pantalla ----------
import flet as ft

from database import repo
from ui.state import AppState
from ui.views import certificacion_owee as vista


class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web, self.urls = [], ft.PagePlatform.LINUX, 1000, True, []

    def update(self, *a): pass
    def open(self, x): pass
    def close(self, *a): pass
    def launch_url(self, u, *a, **k): self.urls.append(u)


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


def _txt(c):
    return " ".join(str(x.value) for x in _todos(c, ft.Text) if x.value)


@pytest.fixture
def st():
    s = AppState(_Pagina())
    s.conn = db.init_db(":memory:")
    s.plan_id = curso.crear_plan_del_curso(s.conn, s.perfil_id)
    return s


def _b(cuerpo, texto, nth=0):
    return [b for b in _todos(cuerpo, (ft.ElevatedButton, ft.OutlinedButton)) if b.text == texto][nth]


def test_la_ruta_muestra_los_ocho_examenes_y_pide_el_oficial_por_correo(st):
    cuerpo = vista.build(st)
    txt = _txt(cuerpo)
    for e in EXAMENES.values():
        assert e["titulo"] in txt
    assert "Certificación de Owee" in txt and "Maestro y examinador" in txt
    _b(cuerpo, "Pedir el examen oficial").on_click(None)
    assert st.page.urls[-1].startswith("mailto:hector@oweeme.com")
    next(b for b in _todos(cuerpo, ft.TextButton) if b.text == "Registro público").on_click(None)
    assert st.page.urls[-1].endswith("certificados.html")


def test_hacer_un_simulacro_completo_corrige_lo_automatico_y_guarda_el_resultado(st):
    cuerpo = vista.build(st)
    _b(cuerpo, "Hacer el simulacro", 3).on_click(None)                     # el cuarto examen de la ruta: Nivel 0
    assert "Nivel 0" in _txt(cuerpo) and "Parte A de 5" in _txt(cuerpo)
    e = EXAMENES["nivel0"]
    for i, parte in enumerate(e["partes"]):
        campos = _todos(cuerpo, ft.TextField)
        botones = [b for b in _todos(cuerpo, ft.OutlinedButton) if b.text in ("Comprobar", "Ver la clave")]
        assert len(botones) == len(parte["items"])
        for it, b in zip(parte["items"], botones):
            if it["auto"]:
                campos.pop(0).value = it["auto"][0]
            elif not it["voz"]:
                campos.pop(0)
            b.on_click(None)
        for fichas in [f for f in _todos(cuerpo, ft.Row) if f.visible and f.controls and all(isinstance(x, ft.OutlinedButton) and x.data for x in f.controls)]:
            fichas.controls[-1].on_click(None)                            # te das el máximo
        _b(cuerpo, "Terminar el simulacro" if i == len(e["partes"]) - 1 else "Siguiente parte").on_click(None)
    txt = _txt(cuerpo)
    assert "Resultado: 100 % (20 de 20 puntos)" in txt and "Aprobado en el simulacro" in txt
    assert cert.ultimos(st.conn, st.plan_id)["nivel0"] == {"pct": 100, "aprobado": True, "fecha": cert.ultimos(st.conn, st.plan_id)["nivel0"]["fecha"]}


def test_un_simulacro_en_blanco_no_aprueba_y_dice_que_repasar(st):
    cuerpo = vista.build(st)
    _b(cuerpo, "Hacer el simulacro", 4).on_click(None)                     # Nivel 1
    for _ in EXAMENES["nivel1"]["partes"]:
        boton = next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text in ("Siguiente parte", "Terminar el simulacro"))
        boton.on_click(None)
    txt = _txt(cuerpo)
    assert "Resultado: 0 %" in txt and "Aún no llegas" in txt and "Escuchar" in txt
    assert cert.ultimos(st.conn, st.plan_id)["nivel1"]["aprobado"] is False
    assert repo.tarjetas_pendientes(st.conn, st.perfil_id) == []           # un simulacro no ensucia el repaso


def test_el_articulo_de_maestro_se_revisa_con_la_lista_del_certificado(st):
    from ui.views import escribir_owee
    cuerpo = escribir_owee.build(st)
    seg = next(x for x in _todos(cuerpo, ft.SegmentedButton))
    seg.on_change(type("E", (), {"control": type("C", (), {"selected": {"articulo"}})()})())
    next(x for x in _todos(cuerpo, ft.TextField) if x.label == "Título del artículo").value = "Lo que aprendí"
    objetivo = next(x for x in _todos(cuerpo, ft.Dropdown) if x.label == "Objetivo")
    objetivo.value = "maestro_infantil"
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if "Nuevo artículo" in (b.text or "")).on_click(None)
    assert "0 de 300 palabras" in _txt(cuerpo)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if x.multiline)
    campo.value = "me ga sade-kelo pe tase. te-fusu me tase nobe, balo-ke pu-fusu me pu tase ximi"
    campo.on_change(None)
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Valorar mi texto").on_click(None)
    txt = _txt(cuerpo)
    assert "Revisión para el certificado" in txt and "⬜ Extensión: 14 de 300 palabras" in txt and "⬜ Solo palabras válidas en Owee" in txt
    assert "✅ Tiempos" in txt and "Compuestos: 4" in txt
