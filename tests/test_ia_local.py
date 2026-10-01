import io
import os
import re
import sys
import tarfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from engine import ai, ia_local

SERVIDOR_FALSO = f"""#!{sys.executable}
import sys, json
from http.server import BaseHTTPRequestHandler, HTTPServer
puerto = int(sys.argv[sys.argv.index("--port") + 1])
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _j(self, o, c=200):
        self.send_response(c); self.send_header("content-type", "application/json"); self.end_headers(); self.wfile.write(json.dumps(o).encode())
    def do_GET(self): self._j({{"status": "ok"}}) if self.path == "/health" else self._j({{}}, 404)
    def do_POST(self):
        self.rfile.read(int(self.headers["content-length"]))
        self._j({{"choices": [{{"message": {{"content": "respuesta-integrada"}}}}]}}) if self.path == "/v1/chat/completions" else self._j({{}}, 404)
HTTPServer(("127.0.0.1", puerto), H).serve_forever()
"""
MODELO = b"GGUF" + os.urandom(4000)


def _servidor_de_archivos(archivos: dict):
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def do_GET(self):
            datos = archivos.get(self.path.lstrip("/"))
            if datos is None:
                self.send_response(404); self.end_headers(); return
            m = re.match(r"bytes=(\d+)-", self.headers.get("Range", ""))
            ini = int(m.group(1)) if m else 0
            self.send_response(206 if m else 200)
            self.send_header("Content-Length", str(len(datos) - ini)); self.end_headers()
            self.wfile.write(datos[ini:])
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture
def instalador(tmp_path, monkeypatch):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo("llama-bFAKE/llama-server"); datos = SERVIDOR_FALSO.encode(); info.size = len(datos); info.mode = 0o644
        t.addfile(info, io.BytesIO(datos))
    srv = _servidor_de_archivos({"fake.tar.gz": buf.getvalue(), "modelo.gguf": MODELO})
    base = f"http://127.0.0.1:{srv.server_port}/"
    monkeypatch.setattr(ia_local, "DIR", tmp_path / "ia")
    monkeypatch.setattr(ia_local, "paquete_motor", lambda: ("fake.tar.gz", base + "fake.tar.gz"))
    monkeypatch.setitem(ia_local.MODELOS, "0.5b", ("modelo.gguf", base + "modelo.gguf", 1, 0.6))
    s = HTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler); puerto = s.server_port; s.server_close()
    monkeypatch.setattr(ia_local, "PUERTO", puerto)
    monkeypatch.setattr(ia_local, "INACTIVIDAD", 2)
    monkeypatch.setattr(ai, "CONFIG", tmp_path / "c.json")
    yield srv
    ia_local.parar(); srv.shutdown()


def test_instalar_arrancar_responder_y_apagar(instalador):
    assert not ia_local.instalado() and not ai.ia_disponible()
    progreso = []
    ia_local.instalar("0.5b", lambda f, t: progreso.append(f))
    assert ia_local.instalado() and progreso[-1] == 1.0 and progreso == sorted(progreso)
    assert ai.ia_disponible()
    assert ai._llm("hola", "s", 10) == "respuesta-integrada"      # arranca solo, cae al protocolo OpenAI
    assert ia_local._vivo()
    import time
    time.sleep(3.5)                                                # inactividad -> libera la RAM
    assert not ia_local._vivo()
    assert ai._llm("otra vez", "s", 10) == "respuesta-integrada"   # vuelve a arrancar solo


def test_instalar_dos_veces_reutiliza_lo_descargado(instalador):
    ia_local.instalar("0.5b", lambda f, t: None)
    n = len(list((ia_local.DIR).rglob("*")))
    ia_local.instalar("0.5b", lambda f, t: None)
    assert len(list((ia_local.DIR).rglob("*"))) == n


def test_descarga_se_reanuda(instalador, tmp_path):
    destino = tmp_path / "x" / "modelo.gguf"
    destino.parent.mkdir()
    (tmp_path / "x" / "modelo.gguf.part").write_bytes(MODELO[:1500])    # quedó a medias
    ia_local.descargar(f"http://127.0.0.1:{instalador.server_port}/modelo.gguf", destino, lambda f, t: None)
    assert destino.read_bytes() == MODELO


def test_desinstalar_libera_todo(instalador):
    ia_local.instalar("0.5b", lambda f, t: None)
    ia_local.desinstalar()
    assert not ia_local.DIR.exists() and not ia_local.instalado()


def test_archivo_comprimido_malicioso_rechazado(tmp_path):
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        info = tarfile.TarInfo("../fuera.txt"); info.size = 1; t.addfile(info, io.BytesIO(b"x"))
    f = tmp_path / "mal.tar.gz"; f.write_bytes(buf.getvalue())
    with pytest.raises(ValueError):
        ia_local._extraer(f, tmp_path / "d")
    assert not (tmp_path / "fuera.txt").exists()


def test_eleccion_de_modelo_por_ram():
    assert ia_local.clave_modelo_para(4) == "0.5b" and ia_local.clave_modelo_para(16) == "1.5b"
    assert ia_local.clave_modelo_para(32) == "3b"


def test_plataforma_movil_no_soportada(monkeypatch):
    monkeypatch.setattr(sys, "platform", "android")
    assert ia_local.paquete_motor() is None and not ia_local.disponible_en_plataforma()


def test_error_de_libreria_se_explica(instalador, monkeypatch):
    ia_local.instalar("0.5b", lambda f, t: None)
    (ia_local.DIR / "servidor.log").write_text("x: error while loading shared libraries: libgomp.so.1: cannot open shared object file")
    texto = ia_local._explicar_fallo()
    assert "libgomp1" in texto and "sudo apt install" in texto
