"""Versión del esquema y copias de seguridad automáticas."""
import sqlite3

from database import db, repo


def test_base_nueva_queda_con_la_version_actual_y_sin_respaldo(tmp_path):
    ruta = str(tmp_path / "e.db")
    conn = db.init_db(ruta)
    assert conn.execute("PRAGMA user_version").fetchone()[0] == db.VERSION_ESQUEMA
    assert not (tmp_path / "respaldos").exists()


def test_base_antigua_se_respalda_antes_de_migrar(tmp_path):
    ruta = str(tmp_path / "e.db")
    conn = db.init_db(ruta)
    repo.crear_plan(conn, "Mi plan", 1)
    conn.execute("PRAGMA user_version=0")      # como una base de antes de existir la versión
    conn.commit()
    conn.close()
    db.init_db(ruta).close()
    copias = list((tmp_path / "respaldos").glob("e-antes-de-v*.db"))
    assert len(copias) == 1
    r = sqlite3.connect(copias[0])
    assert r.execute("SELECT titulo FROM planes").fetchone()[0] == "Mi plan"
    r.close()


def test_abrir_otra_vez_no_vuelve_a_respaldar(tmp_path):
    ruta = str(tmp_path / "e.db")
    db.init_db(ruta).close()
    db.init_db(ruta).close()
    assert not (tmp_path / "respaldos").exists()


def test_rotacion_conserva_solo_las_ultimas(tmp_path):
    ruta = str(tmp_path / "e.db")
    conn = db.init_db(ruta)
    for _ in range(db.MAX_RESPALDOS + 3):
        db.respaldar(conn, ruta, "prueba")
    assert len(list((tmp_path / "respaldos").glob("e-prueba-*.db"))) == db.MAX_RESPALDOS


def test_en_memoria_no_respalda():
    conn = db.init_db(":memory:")
    assert db.respaldar(conn, ":memory:", "x") is None
