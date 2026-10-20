"""Copia de seguridad completa, restauración y resumen para la familia o el docente."""
import sqlite3
import zipfile
from datetime import date, timedelta

import flet as ft
import pytest

import i18n
from database import db, repo
from engine import material as mat
from engine import resumen as rs
from engine import respaldo as rb
from engine import retos as rt
from engine import sprints as sp


@pytest.fixture
def datos(tmp_path):
    ruta = str(tmp_path / "estudios.db")
    c = db.init_db(ruta)
    plan = repo.crear_plan(c, "Biología", 1)
    u = repo.agregar_unidad(c, plan, "U1")
    tema = repo.agregar_tema(c, u, "Células")
    repo.crear_tarjetas(c, tema, [("¿Qué es la célula?", "Unidad básica de la vida")], "manual")
    repo.agregar_lectura(c, plan, "Un artículo", autores="Ruiz, A", anio=2020)
    f = tmp_path / "libro.md"
    f.write_text("La célula es la unidad básica de la vida.\n" * 5, encoding="utf-8")
    h = mat.hash_archivo(str(f))
    repo.agregar_material(c, plan, "Libro", "md", h, "libro.md", mat.copiar_a_app(str(f), h), 10)
    return c, ruta, plan, tema, h


# ---------- copia de seguridad ----------
def test_copia_con_la_base_y_los_archivos(datos, tmp_path):
    c, ruta, plan, tema, h = datos
    r = rb.crear_copia(c, tmp_path / "copia.zip")
    assert r["archivos"] == 1 and r["bytes"] > 1000
    with zipfile.ZipFile(tmp_path / "copia.zip") as z:
        assert set(z.namelist()) == {"estudios.db", "info.json", f"materiales/{h}.md"}
    sin = rb.crear_copia(c, tmp_path / "ligera.zip", con_archivos=False)
    assert sin["archivos"] == 0 and sin["bytes"] < r["bytes"] + 1


def test_inspeccionar_describe_la_copia(datos, tmp_path):
    c, ruta, plan, tema, h = datos
    rb.crear_copia(c, tmp_path / "copia.zip")
    i = rb.inspeccionar(tmp_path / "copia.zip")
    assert i["planes"] == 1 and i["tarjetas"] == 1 and i["archivos"] == 1 and i["esquema"] == db.VERSION_ESQUEMA and i["fecha"][:4] == str(date.today().year)


@pytest.mark.parametrize("contenido", [b"no soy un zip", b""])
def test_inspeccionar_rechaza_lo_que_no_es_una_copia(tmp_path, contenido):
    (tmp_path / "x.zip").write_bytes(contenido)
    with pytest.raises(ValueError, match="no es una copia de seguridad"):
        rb.inspeccionar(tmp_path / "x.zip")
    with pytest.raises(ValueError):
        rb.inspeccionar(tmp_path / "no_existe.zip")


def test_inspeccionar_rechaza_zip_ajeno_y_base_ajena(tmp_path):
    with zipfile.ZipFile(tmp_path / "otro.zip", "w") as z:
        z.writestr("hola.txt", "hola")
    with pytest.raises(ValueError):
        rb.inspeccionar(tmp_path / "otro.zip")
    ajena = tmp_path / "a.db"
    sqlite3.connect(ajena).executescript("CREATE TABLE cosas(x); PRAGMA user_version=1;")
    with zipfile.ZipFile(tmp_path / "ajena.zip", "w") as z:
        z.write(ajena, "estudios.db")
    with pytest.raises(ValueError):
        rb.inspeccionar(tmp_path / "ajena.zip")


def test_no_se_restauran_copias_de_una_version_mas_nueva(datos, tmp_path):
    c, ruta, *_ = datos
    rb.crear_copia(c, tmp_path / "copia.zip", False)
    nueva = tmp_path / "n.db"
    with zipfile.ZipFile(tmp_path / "copia.zip") as z:
        nueva.write_bytes(z.read("estudios.db"))
    s = sqlite3.connect(nueva)
    s.execute(f"PRAGMA user_version={db.VERSION_ESQUEMA + 5}")
    s.commit(); s.close()
    with zipfile.ZipFile(tmp_path / "futura.zip", "w") as z:
        z.write(nueva, "estudios.db")
    with pytest.raises(ValueError, match="más nueva"):
        rb.inspeccionar(tmp_path / "futura.zip")


def test_restaurar_reemplaza_los_datos_guarda_lo_anterior_y_recupera_archivos(datos, tmp_path):
    c, ruta, plan, tema, h = datos
    rb.crear_copia(c, tmp_path / "copia.zip")
    repo.crear_plan(c, "Algo que se añadió después", 1)               # lo que NO estaba en la copia
    repo.borrar_plan(c, plan)
    (mat.CARPETA / f"{h}.md").unlink()                                 # y se perdió el archivo adjunto
    assert [p["titulo"] for p in repo.planes(c, 1)] == ["Algo que se añadió después"]
    r = rb.restaurar(c, ruta, tmp_path / "copia.zip")
    assert [p["titulo"] for p in repo.planes(c, 1)] == ["Biología"] and r["archivos_recuperados"] == 1
    m = repo.materiales(c, repo.planes(c, 1)[0]["id"])[0]
    assert m["ruta"] and (mat.CARPETA / f"{h}.md").exists() and m["ruta"].endswith(f"{h}.md")
    assert c.execute("SELECT COUNT(*) FROM tarjetas").fetchone()[0] == 1 and c.execute("SELECT COUNT(*) FROM lecturas").fetchone()[0] == 1
    assert r["copia_previa"] and list((tmp_path / "respaldos").glob("estudios-antes-de-restaurar-*.db"))
    previa = sqlite3.connect(r["copia_previa"])
    assert previa.execute("SELECT titulo FROM planes").fetchone()[0] == "Algo que se añadió después"      # lo de antes se puede recuperar


def test_restaurar_una_copia_de_un_equipo_sin_los_archivos_deja_la_ruta_vacia(datos, tmp_path):
    c, ruta, plan, tema, h = datos
    rb.crear_copia(c, tmp_path / "ligera.zip", con_archivos=False)
    (mat.CARPETA / f"{h}.md").unlink()
    rb.restaurar(c, ruta, tmp_path / "ligera.zip")
    assert repo.materiales(c, plan)[0]["ruta"] is None                 # el programa pedirá «vincular el archivo aquí»


def test_restaurar_no_cambia_nada_si_la_copia_es_invalida(datos, tmp_path):
    c, ruta, plan, *_ = datos
    (tmp_path / "mala.zip").write_bytes(b"basura")
    with pytest.raises(ValueError):
        rb.restaurar(c, ruta, tmp_path / "mala.zip")
    assert [p["titulo"] for p in repo.planes(c, 1)] == ["Biología"]


def test_una_copia_antigua_se_migra_al_restaurar(datos, tmp_path):
    c, ruta, plan, *_ = datos
    antigua = tmp_path / "vieja.db"
    rb.crear_copia(c, tmp_path / "base.zip", False)
    with zipfile.ZipFile(tmp_path / "base.zip") as z:
        antigua.write_bytes(z.read("estudios.db"))
    v = sqlite3.connect(antigua)
    v.execute("DROP TABLE retos"); v.execute("PRAGMA user_version=3"); v.commit(); v.close()
    with zipfile.ZipFile(tmp_path / "vieja.zip", "w") as z:
        z.write(antigua, "estudios.db")
    rb.restaurar(c, ruta, tmp_path / "vieja.zip")
    assert c.execute("SELECT COUNT(*) FROM retos").fetchone()[0] == 0          # la tabla vuelve a existir
    assert c.execute("PRAGMA user_version").fetchone()[0] == db.VERSION_ESQUEMA


# ---------- resumen ----------
@pytest.fixture
def semana(datos):
    c, ruta, plan, tema, h = datos
    t1 = c.execute("SELECT id FROM tarjetas").fetchone()[0]
    repo.repasar_tarjeta(c, t1, 4)
    repo.registrar_sesion(c, tema, 90)
    repo.agregar_entrega(c, plan, "Examen de células", date.today() + timedelta(days=3), "examen")
    repo.agregar_entrega(c, plan, "Proyecto lejano", date.today() + timedelta(days=60), "proyecto")
    r = rt.crear_reto(c, plan, tema)
    for i in range(4):
        rt.marcar_criterio(c, r, i, True)
    rt.completar(c, r, "listo")
    sp.crear_sprint(c, plan, tema)
    from engine import practica as pr
    pr.registrar(c, plan, "simulacro", 80, {}, None)
    return c, plan


def test_resumen_de_la_semana(semana):
    c, plan = semana
    r = rs.resumen(c, 1)
    assert r["nombre"] == "Yo" and r["racha"] >= 1 and r["horas"] == 1.5 and r["repasos"] == 1 and r["repasos_bien"] == 1
    assert r["retos_hechos"] == 1 and r["retos_abiertos"] == 0 and r["practicas"]["simulacro"] == {"n": 1, "media": 80}
    assert [e["titulo"] for e in r["entregas"]] == ["Examen de células"] and r["sprint"]["hechas"] == 0
    assert r["asignaturas"] == [{"titulo": "Biología", "progreso": 0}]


def test_el_resumen_no_incluye_el_contenido_privado(semana):
    c, plan = semana
    repo.agregar_nota_material(c, repo.materiales(c, plan)[0]["id"], 1, "SECRETO: mi conclusión privada", "conclusion")
    repo.agregar_lectura(c, plan, "Otra", hallazgos="HALLAZGO PRIVADO")
    for txt in (rs.a_texto(rs.resumen(c, 1)), rs.a_html(rs.resumen(c, 1))):
        assert "SECRETO" not in txt and "HALLAZGO" not in txt and "Unidad básica de la vida" not in txt and "¿Qué es la célula?" not in txt
        assert "Examen de células" in txt and "Biología" in txt


def test_resumen_en_texto_y_en_html(semana):
    c, plan = semana
    texto = rs.a_texto(rs.resumen(c, 1))
    assert texto.startswith("Resumen de estudio de Yo") and "ESTA SEMANA" in texto and "• Racha: 1 día seguido" in texto and "en 3 días" in texto
    html = rs.a_html(rs.resumen(c, 1))
    assert html.startswith("<!doctype html>") and "<li>" in html and "<h2>Próximas entregas y exámenes</h2>" in html
    i18n.fijar_idioma("en")
    assert "Study summary for Yo" in rs.a_texto(rs.resumen(c, 1))


def test_resumen_por_asignatura(semana):
    c, plan = semana
    otra = repo.crear_plan(c, "Historia", 1)
    repo.agregar_entrega(c, otra, "Dictado", date.today() + timedelta(days=1))
    assert [e["titulo"] for e in rs.resumen(c, 1, plan)["entregas"]] == ["Examen de células"]
    assert [e["titulo"] for e in rs.resumen(c, 1, otra)["entregas"]] == ["Dictado"]
    assert len(rs.resumen(c, 1)["asignaturas"]) == 2


# ---------- pantallas ----------
class _Pagina:
    def __init__(self):
        self.overlay, self.platform, self.width, self.web, self.portapapeles, self.abiertos = [], ft.PagePlatform.LINUX, 1000, True, None, []

    def update(self, *a): pass
    def open(self, x): self.abiertos.append(x)
    def close(self, *a): pass
    def set_clipboard(self, x): self.portapapeles = x
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


def _boton(c, texto):
    return next(b for b in _todos(c, (ft.ElevatedButton, ft.OutlinedButton, ft.TextButton)) if texto in str(b.text))


def test_metricas_copian_y_guardan_el_resumen(semana):
    from database.db import DATOS
    from ui.state import AppState
    from ui.views import stats
    c, plan = semana
    st = AppState(_Pagina())
    st.conn, st.plan_id = c, plan
    cuerpo = stats.build(st)
    _boton(cuerpo, "Copiar resumen").on_click(None)
    assert "Resumen de estudio de Yo" in st.page.portapapeles
    _boton(cuerpo, "Guardar resumen").on_click(None)
    ruta = next(x.value for x in _todos(cuerpo, ft.Text) if "Guardado en" in str(x.value)).split(": ", 1)[1]
    assert ruta.endswith(".html") and str(DATOS) in ruta and "Examen de células" in open(ruta, encoding="utf-8").read()


def test_ajustes_guarda_copia_y_restaura_con_confirmacion(datos, tmp_path, monkeypatch):
    from ui.state import AppState
    from ui.views import ajustes
    c, ruta, plan, tema, h = datos
    monkeypatch.setattr(ajustes, "DB_PATH", ruta)
    st = AppState(_Pagina())
    st.conn, st.plan_id = c, plan
    reconstruidos = []
    cuerpo = ajustes.build(st, lambda: None, lambda: reconstruidos.append(1))
    _boton(cuerpo, "Guardar copia de seguridad").on_click(None)
    zip_ = next(x.value for x in _todos(cuerpo, ft.Text) if "Copia guardada en" in str(x.value)).split(": ", 1)[1]
    assert zipfile.is_zipfile(zip_)
    repo.crear_plan(c, "Se perderá", 1)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if "Ruta de la copia" in (x.label or ""))
    campo.value = "/no/existe.zip"
    _boton(cuerpo, "Restaurar").on_click(None)
    assert "no es una copia" in " ".join(str(x.value) for x in _todos(cuerpo, ft.Text) if x.value) and len(repo.planes(c, 1)) == 2
    campo.value = zip_
    _boton(cuerpo, "Restaurar").on_click(None)
    dlg = st.page.abiertos[-1]
    assert "1 asignaturas" in dlg.title.value and "1 tarjetas" in dlg.title.value
    dlg.actions[-1].on_click(None)                                     # confirmar
    assert [p["titulo"] for p in repo.planes(c, 1)] == ["Biología"] and reconstruidos == [1]
