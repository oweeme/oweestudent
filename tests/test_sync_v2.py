import json
import threading
import urllib.error
import urllib.request

import pytest

from database import repo
from database.db import init_db
from engine import sync


def _get(url):
    return urllib.request.urlopen(url, timeout=3).read()


@pytest.fixture
def equipo(tmp_path, monkeypatch):
    from engine import ai
    monkeypatch.setattr(ai, "CONFIG", tmp_path / "c.json")
    ai.guardar_config(nombre_equipo="PC de Hector")
    return tmp_path


def test_hola_anuncia_nombre_sin_pin(equipo):
    A = init_db(str(equipo / "A.db"))
    s = sync.Compartir(A)
    try:
        d = json.loads(_get(s.url.split("/?")[0] + "/hola"))
        assert d == {"app": "OweeStudent", "nombre": "PC de Hector", "carpeta": None}
        assert len(s.token) == 6 and s.token.isdigit()
    finally:
        s.parar()


def test_buscar_equipos_encuentra_por_nombre(equipo):
    A = init_db(str(equipo / "A.db"))
    s = sync.Compartir(A)
    try:
        hallados = sync.buscar_equipos(incluir_propio=True)
        assert any(h["nombre"] == "PC de Hector" for h in hallados)
    finally:
        s.parar()
    assert sync.buscar_equipos(incluir_propio=True) == []   # cerrado: ya no aparece


def test_pin_incorrecto_y_bloqueo(equipo):
    A = init_db(str(equipo / "A.db")); N = init_db(str(equipo / "N.db"))
    s = sync.Compartir(A)
    base = s.url.split("/?")[0]
    try:
        with pytest.raises(ValueError, match="PIN incorrecto"):
            sync.recibir(N, base, str(equipo / "N.db"), pin="000000" if s.token != "000000" else "111111")
        for _ in range(sync.MAX_FALLOS):   # fuerza bruta: se cierra el servidor
            try:
                _get(f"{base}/db?t=xxxxxx")
            except Exception:
                pass
        s._srv.socket  # sigue siendo objeto válido
        assert s.bloqueado
        with pytest.raises(Exception):
            _get(f"{base}/db?t={s.token}")   # ni con el PIN correcto: ya cerrado
    finally:
        s.parar()


def test_sincronizar_solo_una_carpeta(equipo):
    A = init_db(str(equipo / "A.db"))
    repo.fijar_clave(A, 1, "secreta")
    c1 = repo.crear_carpeta(A, "Máster"); c2 = repo.crear_carpeta(A, "Privado")
    p1 = repo.crear_plan(A, "Management", 1, carpeta_id=c1); repo.agregar_tema(A, repo.agregar_unidad(A, p1, "U1"), "t1")
    p2 = repo.crear_plan(A, "Diario personal", 1, carpeta_id=c2); repo.agregar_tema(A, repo.agregar_unidad(A, p2, "U2"), "secreto")
    N = init_db(str(equipo / "N.db"))
    s = sync.Compartir(A, carpeta_id=c1)
    try:
        assert json.loads(_get(s.url.split("/?")[0] + "/hola"))["carpeta"] == "Máster"
        res = []
        th = threading.Thread(target=lambda: res.append(s.esperar_y_mezclar(A, 20))); th.start()
        sync.recibir(N, s.url.split("/?")[0], str(equipo / "N.db"), pin=s.token)
        th.join()
    finally:
        s.parar()
    assert [r[0] for r in N.execute("select nombre from carpetas")] == ["Máster"]
    assert [r[0] for r in N.execute("select titulo from planes")] == ["Management"]
    assert N.execute("select count(*) from temas where titulo='secreto'").fetchone()[0] == 0
    assert not repo.tiene_clave(N, 1)                       # la clave de acceso no se comparte
    assert A.execute("select count(*) from carpetas").fetchone()[0] == 2   # A conserva todo
    assert res[0] is not None


def test_carpeta_inexistente(equipo):
    A = init_db(str(equipo / "A.db"))
    s = None
    with pytest.raises(ValueError):
        sync._snapshot(A, "no-existe")


def test_copia_completa_conserva_clave_en_equipo_nuevo(equipo):
    A = init_db(str(equipo / "A.db")); repo.fijar_clave(A, 1, "secreta")
    N = init_db(str(equipo / "N.db"))
    s = sync.Compartir(A)
    try:
        th = threading.Thread(target=lambda: s.esperar_y_mezclar(A, 20)); th.start()
        sync.recibir(N, s.url.split("/?")[0], str(equipo / "N.db"), pin=s.token); th.join()
    finally:
        s.parar()
    assert repo.verificar_clave(N, 1, "secreta")            # tus propios equipos: misma clave


def test_transferencia_de_archivos_de_material(equipo, monkeypatch):
    from engine import material
    monkeypatch.setattr(material, "CARPETA", equipo / "matA")
    A = init_db(str(equipo / "A.db")); pid = repo.crear_plan(A, "Alemán", 1)
    libro = equipo / "libro.txt"; libro.write_text("Kapitel eins. " * 200)
    h = material.hash_archivo(str(libro))
    repo.agregar_material(A, pid, "Libro", "txt", h, "libro.txt", material.copiar_a_app(str(libro), h), libro.stat().st_size)
    # un segundo material con la misma huella (otra asignatura): una sola copia física en el destino
    pid2 = repo.crear_plan(A, "Gramática", 1)
    repo.agregar_material(A, pid2, "Libro (copia)", "txt", h, "libro.txt", material.copiar_a_app(str(libro), h), libro.stat().st_size)
    N = init_db(str(equipo / "N.db"))
    monkeypatch.setattr(material, "CARPETA", equipo / "matN")   # el equipo destino guarda en SU carpeta
    s = sync.Compartir(A)
    try:
        th = threading.Thread(target=lambda: s.esperar_y_mezclar(A, 20)); th.start()
        msg = sync.recibir(N, s.url.split("/?")[0], str(equipo / "N.db"), pin=s.token); th.join()
    finally:
        s.parar()
    assert "archivos de material copiados" in msg
    rutas = {r[0] for r in N.execute("select ruta from materiales")}
    assert len(rutas) == 1 and all(str(equipo / "matN") in r for r in rutas)   # ruta propia de N, una sola copia
    assert material.hash_archivo(rutas.pop()) == h and len(list((equipo / "matN").iterdir())) == 1
    # la ruta de A no viajó en el snapshot
    assert sync._snapshot(A) and sqlite_sin_rutas(sync._snapshot(A), equipo)


def sqlite_sin_rutas(datos, tmp):
    import sqlite3
    f = tmp / "snap.db"; f.write_bytes(datos)
    return sqlite3.connect(f).execute("select count(*) from materiales where ruta is not null").fetchone()[0] == 0


def test_la_ruta_local_no_se_pisa_al_mezclar(equipo, monkeypatch):
    import shutil
    from engine.merge import fusionar
    from engine import material
    monkeypatch.setattr(material, "CARPETA", equipo / "m")
    A = init_db(str(equipo / "A.db")); pid = repo.crear_plan(A, "X", 1)
    mid = repo.agregar_material(A, pid, "M", "txt", "h1", "m.txt", "/ruta/de/A.txt", 1)
    shutil.copy(equipo / "A.db", equipo / "B.db"); B = init_db(str(equipo / "B.db"))
    repo.vincular_archivo(B, mid, "/ruta/de/B.txt")
    import time; time.sleep(0.02)
    repo.progreso_lectura(A, mid, 9, 50)                 # A edita otra cosa después
    fusionar(B, str(equipo / "A.db"))
    fila = B.execute("select ruta, pagina_actual from materiales").fetchone()
    assert fila["ruta"] == "/ruta/de/B.txt" and fila["pagina_actual"] == 9


def test_diagnostico_en_palabras_sencillas(equipo):
    A = init_db(str(equipo / "A.db"))
    s = sync.Compartir(A)
    try:
        ok, txt = sync.diagnosticar(sync.ip_local())
        assert ok and "Conectado" in txt
    finally:
        s.parar()
    ok, txt = sync.diagnosticar(sync.ip_local())            # cerrado: rechazado, no «cortafuegos»
    assert not ok and "Permitir sincronización" in txt
    ok, txt = sync.diagnosticar("203.0.113.9")              # otra red
    assert not ok and "redes distintas" in txt


def test_ip_local_no_es_loopback_si_hay_red():
    assert sync.ip_local().count(".") == 3


def test_enlace_propio_ida_y_vuelta():
    from engine import enlace
    e = enlace.crear("192.168.1.76", 8765, "123456")
    assert e == "oweestudent://sync/192.168.1.76:8765/123456"
    assert enlace.leer(e) == ("http://192.168.1.76:8765", "123456")
    assert enlace.leer("/192.168.1.76:8765/123456") == ("http://192.168.1.76:8765", "123456")   # ruta de Flet
    assert enlace.leer("sync 10.0.0.5 654321") == ("http://10.0.0.5:8765", "654321")
    assert enlace.leer("http://999.1.1.1:8765/123456") is None and enlace.leer("hola") is None
