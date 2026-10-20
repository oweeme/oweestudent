"""«Mis estudios» (carpetas → planes → temario), convertir un archivo en plan, y activar la IA con un botón."""
import flet as ft
import pytest

from database import db, repo
from engine import ai, estudios, ia_auto, ia_local
from owee_curso import curso
from ui.state import AppState
from ui.views import estudios as vista_estudios
from ui.views import material as vista_material
from ui.views import plan as vista_plan

PLAN_MD = """# Global Master
## SEMESTRE 1: BASE
### 🔹 Módulo 1: Estrategia (Meses 1 - 2)
* **Temas Clave:**
  * Geopolítica
  * Competencia global
### 🔹 Módulo 2: Finanzas (Meses 3 - 4)
* **Temas Clave:**
  * Divisas
"""


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
    s.plan_id = None
    return s


def test_arbol_agrupa_por_carpeta_y_deja_owee_al_final(st):
    k = repo.crear_carpeta(st.conn, "Máster", st.perfil_id)
    a = repo.crear_plan(st.conn, "Global Master", st.perfil_id, carpeta_id=k)
    curso.crear_plan_del_curso(st.conn, st.perfil_id)
    suelto = repo.crear_plan(st.conn, "Suelto", st.perfil_id)
    grupos = estudios.arbol(st.conn, st.perfil_id)
    assert [g[0]["nombre"] if g[0] else None for g in grupos] == ["Máster", None, "Owee"]
    assert [p["id"] for p in grupos[0][1]] == [a]
    assert [p["id"] for p in grupos[1][1]] == [suelto]
    assert grupos[2][1][0]["opcional"] is True


def test_resumen_cuenta_temas_y_da_el_siguiente(st):
    pid = repo.importar_texto(st.conn, PLAN_MD, "x.md", None, st.perfil_id)
    r = estudios.resumen(st.conn, pid)
    assert (r["temas"], r["hechos"]) == (3, 0) and r["siguiente"]["titulo"] == "Geopolítica"
    repo.marcar_tema(st.conn, r["siguiente"]["id"], "completado")
    r = estudios.resumen(st.conn, pid)
    assert r["hechos"] == 1 and r["siguiente"]["titulo"] == "Competencia global"


def test_la_lista_muestra_carpetas_y_planes_y_abre_el_plan_elegido(st):
    k = repo.crear_carpeta(st.conn, "Máster", st.perfil_id)
    pid = repo.importar_texto(st.conn, PLAN_MD, "x.md", None, st.perfil_id, carpeta_id=k)
    abiertos, estudiados = [], []
    cuerpo = vista_estudios.build(st, abiertos.append, lambda *a: estudiados.append(a), lambda: None)
    texto = _textos(cuerpo)
    assert "Mis estudios" in texto and "📁 Máster" in texto and "Global Master" in texto and "0 de 3 temas" in texto
    botones = {b.text: b for b in _todos(cuerpo, (ft.ElevatedButton, ft.OutlinedButton))}
    botones["Abrir plan completo"].on_click(None)
    botones["Seguir estudiando"].on_click(None)
    assert abiertos == [pid] and estudiados[0][0] == pid and estudiados[0][2] == "Geopolítica"


def test_el_plan_abierto_tiene_boton_para_volver_a_mis_estudios(st):
    k = repo.crear_carpeta(st.conn, "Máster", st.perfil_id)
    st.plan_id = repo.importar_texto(st.conn, PLAN_MD, "x.md", None, st.perfil_id, carpeta_id=k)
    st.plan_abierto = True
    recargas = []
    cuerpo = vista_plan.build(st, lambda: None, lambda: recargas.append(1))
    assert "📁 Máster" in _textos(cuerpo) and "Módulo 1: Estrategia" in _textos(cuerpo)
    volver = next(b for b in _todos(cuerpo, ft.IconButton) if b.tooltip == "Mis estudios")
    volver.on_click(None)
    assert st.plan_abierto is False and recargas == [1]


def test_un_archivo_con_modulos_se_convierte_en_plan_en_la_misma_carpeta(st, tmp_path):
    k = repo.crear_carpeta(st.conn, "Máster", st.perfil_id)
    base = repo.crear_plan(st.conn, "Material suelto", st.perfil_id, carpeta_id=k)
    f = tmp_path / "gm.md"
    f.write_text(PLAN_MD, encoding="utf-8")
    assert estudios.parece_plan(str(f))
    m = {"ruta": str(f)}
    pid = estudios.plan_desde_material(st.conn, m, st.perfil_id, k)
    assert pid != base
    fila = st.conn.execute("SELECT carpeta_id FROM planes WHERE id=?", (pid,)).fetchone()
    assert fila["carpeta_id"] == k and estudios.resumen(st.conn, pid)["temas"] == 3


def test_un_archivo_sin_estructura_no_deja_un_plan_vacio(st, tmp_path):
    f = tmp_path / "nota.txt"
    f.write_text("hola, esto no es un plan", encoding="utf-8")
    assert not estudios.parece_plan(str(f))
    antes = len(repo.planes(st.conn, st.perfil_id))
    with pytest.raises(ValueError):
        estudios.plan_desde_material(st.conn, {"ruta": str(f)}, st.perfil_id)
    assert len(repo.planes(st.conn, st.perfil_id)) == antes


def test_adjuntar_un_plan_en_material_ofrece_convertirlo(st, tmp_path):
    st.plan_id = repo.crear_plan(st.conn, "Aprende Owee", st.perfil_id)
    f = tmp_path / "gm.md"
    f.write_text(PLAN_MD, encoding="utf-8")
    saltos = []
    cuerpo = vista_material.build(st, lambda: None, saltos.append)
    campo = next(x for x in _todos(cuerpo, ft.TextField) if "ruta" in (x.label or ""))
    campo.value = str(f)
    next(b for b in _todos(cuerpo, ft.OutlinedButton) if b.text == "Adjuntar").on_click(None)
    assert "parece un plan de estudios" in _textos(cuerpo)
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Crear el plan").on_click(None)
    assert len(saltos) == 1 and estudios.resumen(st.conn, saltos[0])["temas"] == 3


# ---------- IA con un botón ----------
@pytest.fixture
def sin_ia(monkeypatch, tmp_path):
    monkeypatch.setattr(ai, "CONFIG", tmp_path / "config.json")
    monkeypatch.setattr(ia_local, "instalado", lambda: False)
    monkeypatch.setattr(ia_local, "disponible_en_plataforma", lambda: True)
    monkeypatch.setattr(ai, "detectar_local", lambda: None)
    monkeypatch.setattr(ia_auto.shutil, "which", lambda _: None)


def test_sin_nada_instalado_el_boton_instala_la_ia_integrada(sin_ia, monkeypatch):
    llamadas = []
    monkeypatch.setattr(ia_local, "instalar", lambda clave, prog: llamadas.append(clave))
    assert ia_auto.diagnostico()["accion"] == "instalar_integrada"
    ia_auto.activar(lambda f, x: None)
    assert len(llamadas) == 1 and llamadas[0] in ia_local.MODELOS


def test_si_ya_hay_un_servidor_con_modelos_lo_usa_sin_descargar(sin_ia, monkeypatch):
    monkeypatch.setattr(ai, "detectar_local", lambda: ("http://localhost:11434", ["llama3:8b", "qwen2.5:1.5b"]))
    monkeypatch.setattr(ia_local, "instalar", lambda *a: pytest.fail("no debía descargar"))
    assert ia_auto.diagnostico()["accion"] == "usar_servidor"
    ia_auto.activar(lambda f, x: None)
    cfg = ai.cargar_config()
    assert cfg["local_url"] == "http://localhost:11434" and cfg["local_modelo"] == "qwen2.5:1.5b"   # el más ligero conocido


def test_con_ollama_apagado_lo_enciende_y_baja_un_modelo_ligero(sin_ia, monkeypatch):
    monkeypatch.setattr(ia_auto.shutil, "which", lambda _: "/usr/bin/ollama")
    monkeypatch.setattr(ia_auto, "_encender_ollama", lambda *a, **k: "http://localhost:11434")
    monkeypatch.setattr(ai, "modelos_locales", lambda url: [])
    bajados = []
    monkeypatch.setattr(ia_auto.recursos, "descargar_modelo", lambda url, m, prog: bajados.append(m))
    assert ia_auto.diagnostico()["accion"] == "arrancar_ollama"
    ia_auto.activar(lambda f, x: None)
    assert len(bajados) == 1 and ai.cargar_config()["local_modelo"] == bajados[0]


def test_si_la_ia_integrada_ya_esta_no_hace_nada(sin_ia, monkeypatch):
    monkeypatch.setattr(ia_local, "instalado", lambda: True)
    assert ia_auto.diagnostico()["accion"] == "lista"
    assert "lista" in ia_auto.activar(lambda f, x: None)


def test_en_un_dispositivo_sin_motor_explica_que_use_la_ia_del_pc(sin_ia, monkeypatch):
    monkeypatch.setattr(ia_local, "disponible_en_plataforma", lambda: False)
    assert ia_auto.diagnostico()["accion"] == "ninguna"
    with pytest.raises(RuntimeError, match="PC"):
        ia_auto.activar(lambda f, x: None)


def test_importar_aqui_crea_un_plan_nuevo_en_la_carpeta_y_no_suma_al_plan_activo(st, tmp_path):
    from ui.views import importar
    k = repo.crear_carpeta(st.conn, "master", st.perfil_id)
    activo = curso.crear_plan_del_curso(st.conn, st.perfil_id)
    st.plan_id, st.carpeta_destino = activo, k
    f = tmp_path / "gm.md"
    f.write_text(PLAN_MD, encoding="utf-8")
    vistos = []
    cuerpo = importar.build(st, lambda: vistos.append(st.plan_id))
    ruta = next(x for x in _todos(cuerpo, ft.TextField) if "ruta" in (x.label or ""))
    ruta.value = str(f)
    next(b for b in _todos(cuerpo, ft.ElevatedButton) if b.text == "Importar").on_click(None)
    nuevo = vistos[0]
    assert nuevo != activo
    assert st.conn.execute("SELECT carpeta_id FROM planes WHERE id=?", (nuevo,)).fetchone()["carpeta_id"] == k
    assert estudios.resumen(st.conn, nuevo)["temas"] == 3


PDF_TEXTO = """🎓  Global Master in International
Management & Language Mastery
Modalidad: Autodidacta
Duración Total: 18 Meses (3 Semestres)
📚  SEMESTRE 1: FUNDAMENTOS DIRECTIVOS,
FINANZAS E IDIOMAS BASE (Meses 1 - 6)
🔹  Módulo 1: Estrategia Empresarial Global
(Meses 1 - 2)
Temas Clave:
Marco de ventaja competitiva internacional (Diamante de Porter).
Estrategias de entrada a mercados: Exportación, Licencias,
Joint Ventures y Filiales propias.
Bibliografía Principal:
Global Strategy – Mike W. Peng.
📝  Caso de Estudio Práctico (Tarea 1):
Entregable: Elaborar un informe de viabilidad
de expansión internacional.
🔹  Módulo 2: Finanzas Internacionales
(Meses 3 - 4)
Temas Clave:
Incoterms 2020 en la práctica.
🌐  Idiomas - Fase 1 (Meses 1 - 6)
Inglés (Objetivo C1 - Profesional Avanzado):
Tarea semanal: Leer 2 artículos y
redactar un resumen.
"""


def test_un_pdf_con_la_forma_del_plan_recupera_modulos_temas_libros_y_entregables(st):
    from parsers.pdf_plan import a_markdown
    md = a_markdown(PDF_TEXTO)
    pid = repo.importar_texto(st.conn, md, "x.pdf", None, st.perfil_id)
    us = repo.unidades(st.conn, pid)
    assert [u["titulo"] for u in us] == ["Módulo 1: Estrategia Empresarial Global", "Módulo 2: Finanzas Internacionales", "Idiomas - Fase 1"]
    assert us[0]["semestre"].startswith("SEMESTRE 1") and us[0]["mes_ini"] == 1 and us[0]["mes_fin"] == 2
    assert [t_["titulo"] for t_ in repo.temas(st.conn, us[0]["id"])][1].endswith("Filiales propias.")   # línea partida, un solo tema
    assert repo.recursos(st.conn, us[0]["id"])[0]["contenido"] == "Global Strategy"
    assert st.conn.execute("SELECT COUNT(*) FROM entregables").fetchone()[0] == 1
    assert st.conn.execute("SELECT COUNT(*) FROM metas_idioma").fetchone()[0] == 1


def test_un_pdf_sin_modulos_se_deja_igual():
    from parsers.pdf_plan import a_markdown
    assert a_markdown("solo una nota\nsin estructura") == "solo una nota\nsin estructura"
