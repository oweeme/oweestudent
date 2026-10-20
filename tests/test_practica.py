"""Práctica activa: cobertura, revisión de explicaciones, simulacros e historial."""
import json

import pytest

from database import db, repo
from engine import practica as pr

TEXTO = ("La fotosíntesis es el proceso por el cual las plantas convierten la luz solar en energía química. "
         "La clorofila absorbe la luz y el proceso ocurre en los cloroplastos. La fotosíntesis produce glucosa y oxígeno.")


class _Con:
    """Conexión con atajos a la asignatura y el tema de prueba (sqlite3.Connection no admite atributos nuevos)."""

    def __init__(self, c, plan, tema):
        self._c, self.plan, self.tema = c, plan, tema

    def __getattr__(self, nombre):
        return getattr(self._c, nombre)



@pytest.fixture
def conn():
    c = db.init_db(":memory:")
    plan = repo.crear_plan(c, "Biología", 1)
    tema = repo.tema_para_tarjetas(c, plan, "Célula")
    pares = [("¿Qué es la fotosíntesis?", "Proceso que convierte luz en energía química"),
             ("¿Dónde ocurre la fotosíntesis?", "En los cloroplastos de las células vegetales"),
             ("¿Qué pigmento absorbe la luz?", "La clorofila, un pigmento verde"),
             ("¿Qué produce la respiración celular?", "Energía en forma de ATP en la mitocondria"),
             ("¿Qué es el ADN?", "La molécula que guarda la información genética"),
             ("¿Qué hace el ribosoma?", "Fabrica proteínas a partir del ARN mensajero")]
    repo.crear_tarjetas(c, tema, pares, "manual")
    return _Con(c, plan, tema)


def test_terminos_clave_son_las_palabras_que_mas_pesan():
    clave = pr.terminos_clave(TEXTO, 5)
    assert "fotosíntesis" in clave and "luz" not in clave[:0]       # «luz» tiene 3 letras: se ignora
    assert len(clave) == 5 and len(set(clave)) == 5


def test_cobertura_distingue_lo_recordado_de_lo_olvidado():
    r = pr.cobertura(TEXTO, "Las plantas hacen la fotosíntesis con la clorofila")
    assert "fotosíntesis" in r["cubiertos"] and "clorofila" in r["cubiertos"]
    assert "glucosa" in r["faltan"] and 0 < r["porcentaje"] < 100
    assert pr.cobertura(TEXTO, TEXTO)["porcentaje"] == 100
    assert pr.cobertura(TEXTO, "")["porcentaje"] == 0
    assert pr.cobertura("", "algo")["porcentaje"] == 0


def test_cobertura_ignora_acentos_y_plurales():
    assert "fotosíntesis" in pr.cobertura(TEXTO, "FOTOSINTESIS")["cubiertos"]
    assert "plantas" in pr.cobertura(TEXTO, "una planta")["cubiertos"]


def test_revision_local_de_la_explicacion():
    corta = pr.revisar_explicacion_local("Es cosa de plantas.")
    assert corta["muy_corta"] and corta["frases"] == 1
    larga = pr.revisar_explicacion_local(" ".join(["palabra"] * 40) + ". Y la electroquimiotaxis es complicada " + "de explicar " * 5 + ".", TEXTO)
    assert len(larga["largas"]) == 1 and "electroquimiotaxis" in larga["tecnicas"]
    assert larga["cobertura"] is not None and not larga["muy_corta"]
    assert pr.revisar_explicacion_local("hola " * 30)["cobertura"] is None


def test_parse_de_la_evaluacion_de_la_ia():
    txt = "CORRECTO:\n- Dijo que usa luz\n- Mencionó la clorofila\nFALTA:\n- La glucosa\n* El oxígeno\nERRORES:\n- ninguno\n"
    r = pr.parse_evaluacion(txt)
    assert r == {"correcto": ["Dijo que usa luz", "Mencionó la clorofila"], "falta": ["La glucosa", "El oxígeno"], "errores": []}
    inline = pr.parse_evaluacion("Correcto: bien\nFalta: nada\nErrores: confundió ATP con ADN")
    assert inline["correcto"] == ["bien"] and inline["falta"] == [] and inline["errores"] == ["confundió ATP con ADN"]


def test_evaluar_y_feynman_con_ia_inyectada():
    vistos = []

    def falso(prompt, sistema, tokens):
        vistos.append((prompt, sistema))
        return "CLARO:\n- Explicó la luz\nHUECOS:\n- No dijo qué es la clorofila\nPREGUNTAS:\n- ¿Y de noche?\n- ¿Qué comen?\n- ¿Por qué verdes?"
    r = pr.revisar_explicacion_ia("Las plantas comen luz", TEXTO, llm=falso)
    assert r["huecos"] == ["No dijo qué es la clorofila"] and len(r["preguntas"]) == 3
    assert "TEXTO DE REFERENCIA" in vistos[0][0] and "SOLO" in vistos[0][1]
    pr.revisar_explicacion_ia("Las plantas comen luz", "", llm=falso)
    assert "NO verifiques datos" in vistos[1][0]                      # sin referencia: solo claridad
    e = pr.evaluar_recuperacion_ia(TEXTO, "algo", llm=lambda *a: "CORRECTO:\n- x\nFALTA:\n- y\nERRORES:\n- z")
    assert e == {"correcto": ["x"], "falta": ["y"], "errores": ["z"]}


def test_simulacro_de_opcion_multiple_con_distractores_validos(conn):
    ps = pr.preparar_simulacro(conn, 1, conn.plan, n=5, tipo="opciones", semilla=1)
    assert len(ps) == 5
    for p in ps:
        assert p.opciones and len(p.opciones) == 4 and len(set(p.opciones)) == 4 and p.correcta in p.opciones
    assert pr.preparar_simulacro(conn, 1, conn.plan, n=5, semilla=1)[0].enunciado == ps[0].enunciado    # reproducible


def test_simulacro_abierto_mixto_y_pocos_datos(conn):
    assert all(p.opciones is None for p in pr.preparar_simulacro(conn, 1, conn.plan, n=4, tipo="abierta"))
    mixto = pr.preparar_simulacro(conn, 1, conn.plan, n=6, tipo="mixto", semilla=3)
    assert any(p.opciones for p in mixto) and any(not p.opciones for p in mixto)
    poca = db.init_db(":memory:")
    t = repo.tema_para_tarjetas(poca, repo.crear_plan(poca, "X", 1))
    repo.crear_tarjetas(poca, t, [("a?", "a"), ("b?", "b")], "manual")
    assert pr.preparar_simulacro(poca, 1, tipo="opciones")[0].opciones is None      # sin distractores: abierta
    assert pr.preparar_simulacro(db.init_db(":memory:"), 1) == []


def test_alcance_por_tema_y_por_asignatura(conn):
    otro = repo.tema_para_tarjetas(conn, conn.plan, "Genética")
    repo.crear_tarjetas(conn, otro, [("¿Qué es un gen?", "Unidad de herencia")], "manual")
    assert len(pr.preparar_simulacro(conn, 1, conn.plan, n=50)) == 7
    assert [p.enunciado for p in pr.preparar_simulacro(conn, 1, tema_id=otro, n=50)] == ["¿Qué es un gen?"]


def test_correccion_y_reprogramacion_de_errores(conn):
    ps = pr.preparar_simulacro(conn, 1, conn.plan, n=4, tipo="opciones", semilla=5)
    respuestas = {ps[0].tarjeta_id: ps[0].correcta, ps[1].tarjeta_id: ps[1].opciones[0] if ps[1].opciones[0] != ps[1].correcta else ps[1].opciones[1]}
    r = pr.corregir(ps, respuestas)       # 1 bien, 1 mal, 2 sin responder
    assert r["total"] == 4 and r["correctas"] == 1 and r["porcentaje"] == 25 and len(r["errores"]) == 3
    antes = conn.execute("SELECT repeticiones FROM tarjetas WHERE id=?", (r["errores"][0].tarjeta_id,)).fetchone()[0]
    assert pr.reprogramar_errores(conn, r["errores"]) == 3
    assert conn.execute("SELECT repeticiones FROM tarjetas WHERE id=?", (r["errores"][0].tarjeta_id,)).fetchone()[0] == antes + 1
    assert conn.execute("SELECT COUNT(*) FROM repasos_log WHERE calidad=1").fetchone()[0] == 3
    ok = conn.execute("SELECT repeticiones FROM tarjetas WHERE id=?", (ps[0].tarjeta_id,)).fetchone()[0]
    assert ok == 0                          # lo que acertaste no se toca


def test_correccion_de_preguntas_abiertas():
    ps = [pr.Pregunta(1, "a", "A"), pr.Pregunta(2, "b", "B")]
    r = pr.corregir(ps, {1: True, 2: False})
    assert r["correctas"] == 1 and [e.tarjeta_id for e in r["errores"]] == [2]
    assert pr.corregir([], {})["porcentaje"] == 0


def test_plano_quita_las_marcas_de_glifos():
    assert pr.plano("[glifo]ka") == "ka" and pr.plano("[owee]suna") == "suna" and pr.plano("normal") == "normal"


def test_historial_y_resumen(conn):
    pr.registrar(conn, conn.plan, "simulacro", 80, {"n": 10})
    pr.registrar(conn, conn.plan, "simulacro", 60, {"n": 10})
    pr.registrar(conn, conn.plan, "recuperacion", 45, {"clave": 12}, tema_id=conn.tema)
    h = pr.historial(conn, conn.plan)
    assert [x["tipo"] for x in h] == ["recuperacion", "simulacro", "simulacro"] and json.loads(h[0]["detalle"]) == {"clave": 12}
    assert len(pr.historial(conn, conn.plan, "simulacro")) == 2
    r = pr.resumen(conn, conn.plan)
    assert r["simulacro"] == {"n": 2, "media": 70} and r["feynman"] == {"n": 0, "media": None}
    with pytest.raises(ValueError):
        pr.registrar(conn, conn.plan, "otra", 1)


def test_referencias_de_tema_y_de_lectura(conn):
    assert "clorofila" in pr.referencia_de_tema(conn, conn.tema)
    l = repo.agregar_lectura(conn, conn.plan, "Estudio", hallazgos="Hallazgo importante", notas="Nota")
    assert pr.referencia_de_lectura(conn, l) == "Hallazgo importante\nNota"


def test_las_practicas_se_sincronizan(tmp_path):
    from engine.merge import fusionar
    a, b = db.init_db(str(tmp_path / "a.db")), db.init_db(str(tmp_path / "b.db"))
    p = repo.crear_plan(a, "Tesis", 1)
    pr.registrar(a, p, "simulacro", 90, {"n": 5})
    a.close()
    fusionar(b, str(tmp_path / "a.db"))
    assert b.execute("SELECT tipo, puntaje FROM practicas").fetchone()[:] == ("simulacro", 90.0)
