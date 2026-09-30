import shutil
import threading
import time
import urllib.error
import urllib.request
from datetime import date

import pytest

from conftest import EJEMPLO
from database import repo
from database.db import init_db
from engine import fsrs, recursos, sync, tarjetas
from engine.merge import es_virgen, fusionar
from parsers.file_parser import extract_text
from parsers.plan_parser import parse_plan


@pytest.fixture
def bd():
    return init_db(":memory:")


def _plan(c):
    return repo.importar_archivo(c, str(EJEMPLO))


# ---------- parser / importación ----------
def test_parser_estructura():
    p = parse_plan(extract_text(str(EJEMPLO)))
    assert p["titulo"].startswith("Introducción a Redes")
    assert [u["titulo"][:8] for u in p["unidades"]] == ["Módulo 1", "Módulo 2"]
    assert len(p["unidades"][0]["temas"]) == 3
    assert p["unidades"][0]["libros"][0]["autor"].startswith("Kurose")
    assert p["unidades"][0]["entregable"]
    assert len(p["cronograma"]) == 2


def test_texto_plano_cae_a_modo_generico():
    p = parse_plan("Plan X\nAprender cosas importantes\nOtra cosa más")
    assert p["unidades"] and p["unidades"][0]["temas"]


def test_importar_agrega_al_plan_existente(bd):
    pid = _plan(bd)
    n = len(repo.unidades(bd, pid))
    assert repo.importar_texto(bd, "# IT\n### Módulo A\n* **Temas Clave:**\n  * DNS\n", plan_id=pid) == pid
    assert len(repo.unidades(bd, pid)) == n + 1


# ---------- tarjetas sin IA ----------
def test_tarjetas_desde_apuntes():
    t = tarjetas.desde_apuntes("**Forward**: contrato para fijar hoy un tipo de cambio futuro acordado.\n"
                               "El **Swap** intercambia flujos de pago entre dos partes en el tiempo.")
    assert len(t) == 2 and any("Forward" in p for p, _ in t)


def test_tarjetas_sin_duplicados(bd):
    _plan(bd)
    assert repo.crear_tarjetas(bd, 1, [("¿A?", "a"), ("¿A?", "b"), ("¿B?", "c")], "t") == 2


# ---------- FSRS ----------
def test_fsrs_primera_revision_y_orden():
    hoy = date(2026, 1, 1)
    dias = {q: fsrs.revisar(None, None, None, q, hoy)["intervalo"] for q in (1, 3, 4, 5)}
    assert dias[1] == 1 and dias[3] < dias[4] < dias[5]


def test_fsrs_crece_y_falla_reinicia():
    e = fsrs.revisar(None, None, None, 4, date(2026, 1, 1))
    previos = [e["intervalo"]]
    for _ in range(3):
        e = fsrs.revisar(e["estabilidad"], e["dificultad"], e["ultimo"], 4, date.fromisoformat(e["proximo"]))
        previos.append(e["intervalo"])
    assert previos == sorted(previos) and previos[-1] > previos[0]
    f = fsrs.revisar(e["estabilidad"], e["dificultad"], e["ultimo"], 0, date.fromisoformat(e["proximo"]))
    assert f["intervalo"] == 1 and f["estabilidad"] < e["estabilidad"]
    assert max(previos) <= 365


def test_repaso_actualiza_bd(bd):
    _plan(bd)
    repo.crear_tarjeta(bd, 1, "¿P?", "R")
    k = repo.tarjetas_pendientes(bd, 1)[0]["id"]
    repo.repasar_tarjeta(bd, k, 4)
    assert not repo.tarjetas_pendientes(bd, 1)
    assert repo.retencion(bd, 1)[0] == 1.0


# ---------- claves ----------
def test_claves(bd):
    assert not repo.hay_claves(bd) and repo.verificar_clave(bd, 1, "")
    repo.fijar_clave(bd, 1, "secreta")
    assert repo.verificar_clave(bd, 1, "secreta") and not repo.verificar_clave(bd, 1, "otra")
    fila = bd.execute("SELECT clave_hash, sal FROM perfiles WHERE id=1").fetchone()
    assert "secreta" not in "".join(fila)
    repo.fijar_clave(bd, 1, None)
    assert not repo.tiene_clave(bd, 1)


# ---------- RAM / modelos ----------
def test_recomendacion_por_ram():
    assert recursos.recomendar(4)[0] == "qwen2.5:0.5b"
    assert recursos.recomendar(16)[0] == "qwen2.5:1.5b"
    assert recursos.recomendar(32)[0] == "qwen2.5:3b"
    assert recursos.recomendar(16, 40)[0] == "qwen2.5:7b"


# ---------- sincronización ----------
def _foto(c):
    q = lambda s: sorted(tuple(r) for r in c.execute(s))
    return [q("select uid,titulo,estado from temas"), q("select uid,pregunta from tarjetas"),
            q("select uid,nombre from perfiles"), q("select uid,titulo from unidades")]


def test_triggers_uid_fecha_y_lapida(bd):
    _plan(bd)
    uid = bd.execute("select uid from temas where id=1").fetchone()[0]
    assert uid and not uid.startswith("legacy")
    antes = bd.execute("select modificado from temas where id=1").fetchone()[0]
    time.sleep(0.01)
    repo.marcar_tema(bd, 1, "completado")
    assert bd.execute("select modificado from temas where id=1").fetchone()[0] > antes
    repo.borrar_tema(bd, 1)
    assert bd.execute("select 1 from _tombstones where uid=?", (uid,)).fetchone()


def test_mezcla_bidireccional(tmp_path):
    A = init_db(str(tmp_path / "A.db"))
    _plan(A)
    shutil.copy(tmp_path / "A.db", tmp_path / "B.db")
    B = init_db(str(tmp_path / "B.db"))
    assert _foto(A) == _foto(B)
    time.sleep(0.02)
    repo.marcar_tema(A, 1, "completado"); repo.crear_tarjeta(A, 1, "deA", "x")
    repo.editar_tema(A, 3, "editado en A", None, None)
    time.sleep(0.02)
    repo.editar_tema(B, 3, "editado en B (más reciente)", None, None)
    repo.borrar_tema(B, 2); repo.crear_perfil(B, "Otro"); repo.agregar_tema(B, 1, "nuevo B")
    fusionar(B, str(tmp_path / "A.db")); B.commit()
    fusionar(A, str(tmp_path / "B.db")); A.commit()
    assert _foto(A) == _foto(B)
    assert A.execute("select titulo from temas where id=3").fetchone()[0].startswith("editado en B")
    assert A.execute("select count(*) from temas where id=2").fetchone()[0] == 0
    assert A.execute("select estado from temas where id=1").fetchone()[0] == "completado"
    assert fusionar(A, str(tmp_path / "B.db")) == {"nuevos": 0, "actualizados": 0, "borrados": 0}  # idempotente
    assert A.execute("pragma foreign_key_check").fetchall() == []


def test_edicion_posterior_gana_al_borrado(tmp_path):
    A = init_db(str(tmp_path / "A.db")); _plan(A)
    shutil.copy(tmp_path / "A.db", tmp_path / "B.db"); B = init_db(str(tmp_path / "B.db"))
    time.sleep(0.02); repo.borrar_tema(A, 5)
    time.sleep(0.02); repo.editar_tema(B, 5, "sigo vivo", None, None)  # editado DESPUÉS del borrado
    fusionar(A, str(tmp_path / "B.db"))
    assert A.execute("select count(*) from temas where titulo='sigo vivo'").fetchone()[0] == 1


def test_transporte_qr_equipo_nuevo_y_seguridad(tmp_path):
    A = init_db(str(tmp_path / "A.db")); _plan(A)
    N = init_db(str(tmp_path / "N.db"))
    assert es_virgen(N) and not es_virgen(A)
    s = sync.Compartir(A)
    try:
        for url, datos in ((s.url.split("/?")[0] + "/db", None), (s.url.split("/?")[0] + "/db?t=malo", None),
                           (s.url.split("/?")[0] + f"/devolver?t={s.token}", b"x")):
            with pytest.raises(urllib.error.HTTPError) as e:
                urllib.request.urlopen(urllib.request.Request(url, datos, method="POST" if datos else "GET"), timeout=3)
            assert e.value.code == 403
        res = []
        th = threading.Thread(target=lambda: res.append(s.esperar_y_mezclar(A, 20))); th.start()
        msg = sync.recibir(N, s.url, str(tmp_path / "N.db"))
        th.join()
        assert "copia completa" in msg and res and res[0]["nuevos"] == 0
        assert N.execute("select count(*) from temas").fetchone()[0] == A.execute("select count(*) from temas").fetchone()[0]
    finally:
        s.parar()


def test_qr_es_png():
    assert __import__("base64").b64decode(sync.qr_base64("http://192.168.1.5:8765/?t=abc"))[:4] == b"\x89PNG"


# ---------- IA (sin servidor real) ----------
def test_ia_cadena_y_validacion(monkeypatch, tmp_path):
    from engine import ai
    monkeypatch.setattr(ai, "CONFIG", tmp_path / "c.json")
    assert not ai.ia_disponible()
    ai.guardar_config(local_url="http://localhost:9", local_modelo="x", remoto_url="http://localhost:8", remoto_modelo="y")
    with pytest.raises(RuntimeError, match="Ninguna IA respondió"):
        ai._llm("hola", "s", 10)
    monkeypatch.setattr(ai, "_local", lambda p, s, m, url, mod: f"ok:{url}")
    assert ai._llm("hola", "s", 10) == "ok:http://localhost:9"   # primero este equipo
    calls = []
    def falla_primero(p, s, m, url, mod):
        calls.append(url)
        if "9" in url.rsplit(":", 1)[1]:
            raise OSError("caído")
        return "ok:remoto"
    monkeypatch.setattr(ai, "_local", falla_primero)
    assert ai._llm("hola", "s", 10) == "ok:remoto"              # cae al otro equipo
    assert len(calls) == 2


def test_datos_del_proyecto():
    import app_info
    assert app_info.AUTOR == "Hector Martinez" and app_info.EMAIL == "hector@oweeme.com"
    assert app_info.DONACIONES.startswith("https://www.paypal.com/paypalme/")
    assert app_info.WEB.startswith("https://www.oweeme.com")


def test_entorno_empaquetado_restaura_ld_library_path():
    from engine.entorno import restaurar_librerias
    env = {"LD_LIBRARY_PATH": "/opt/app/_internal:/mi/lib", "LD_LIBRARY_PATH_ORIG": "/mi/lib"}
    assert restaurar_librerias(env, empaquetado=True) and env["LD_LIBRARY_PATH"] == "/mi/lib"
    env = {"LD_LIBRARY_PATH": "/opt/app/_internal", "LD_LIBRARY_PATH_ORIG": ""}
    assert restaurar_librerias(env, empaquetado=True) and "LD_LIBRARY_PATH" not in env
    env = {"LD_LIBRARY_PATH": "/x"}
    assert not restaurar_librerias(env, empaquetado=False) and env["LD_LIBRARY_PATH"] == "/x"  # desarrollo: no toca
