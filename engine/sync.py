"""Sincronización por Wi-Fi local con QR: A muestra el QR, B se conecta, ambos quedan iguales (mezcla)."""
import base64
import io
import json
import secrets
import shutil
import socket
import sqlite3
import tempfile
import threading
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

PUERTO = 8765
TABLAS_ESPERADAS = {"planes", "unidades", "temas", "notas"}


def ip_local() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.255.255.255", 1))  # no envía nada; solo elige la interfaz LAN
        return s.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        s.close()


def qr_base64(texto: str) -> str:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    img = qrcode.make(texto, box_size=8, border=2, image_factory=PyPNGImage)
    buf = io.BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def _snapshot(conn: sqlite3.Connection) -> bytes:
    with tempfile.TemporaryDirectory() as d:
        dst = sqlite3.connect(Path(d) / "s.db")
        conn.backup(dst)
        dst.close()
        return (Path(d) / "s.db").read_bytes()


class Compartir:
    """Sirve una copia de tu base y espera que el otro equipo devuelva la versión mezclada.

    Flujo: B descarga → B mezcla con lo suyo → B devuelve el resultado → A lo mezcla. Caduca a los `caduca` s.
    """

    def __init__(self, conn, caduca=300):
        self.token = secrets.token_urlsafe(9)
        self.url = None
        self.descargado = threading.Event()
        self.devuelto = threading.Event()
        self._devuelto_bytes = None
        self._datos = _snapshot(conn)
        token, datos, evento, yo = self.token, self._datos, self.descargado, self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                q = parse_qs(urlparse(self.path).query)
                if q.get("t", [""])[0] != token or urlparse(self.path).path != "/devolver" or not evento.is_set():
                    self.send_response(403); self.end_headers(); return
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > 500_000_000:
                    self.send_response(400); self.end_headers(); return
                yo._devuelto_bytes = self.rfile.read(n)
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
                yo.devuelto.set()

            def do_GET(self):
                q = parse_qs(urlparse(self.path).query)
                if q.get("t", [""])[0] != token:
                    self.send_response(403); self.end_headers(); return
                if urlparse(self.path).path == "/db":
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(datos)))
                    self.end_headers(); self.wfile.write(datos)
                    evento.set()
                else:
                    html = ("<meta name=viewport content='width=device-width'><h2>OweeStudent</h2>"
                            "<p>Abre la app OweeStudent, ve a <b>Ajustes → Recibir</b> y pega este enlace:</p>"
                            f"<p><code>{self.headers.get('Host')}/?t={token}</code></p>").encode()
                    self.send_response(200); self.send_header("Content-Type", "text/html")
                    self.end_headers(); self.wfile.write(html)

        self._srv = HTTPServer(("0.0.0.0", PUERTO), H)
        self.url = f"http://{ip_local()}:{PUERTO}/?t={token}"
        threading.Thread(target=self._srv.serve_forever, daemon=True).start()
        threading.Thread(target=lambda: (self.devuelto.wait(caduca), self.parar()), daemon=True).start()

    def esperar_y_mezclar(self, conn, espera=300) -> dict | None:
        """Espera la versión mezclada del otro equipo y la mezcla en `conn`. None si no llegó a tiempo."""
        from engine.merge import fusionar
        if not self.devuelto.wait(espera):
            return None
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "d.db"
            f.write_bytes(self._devuelto_bytes)
            _validar(f)
            return fusionar(conn, str(f))

    def parar(self):
        try:
            self._srv.shutdown(); self._srv.server_close()
        except Exception:
            pass


def _validar(ruta):
    c = sqlite3.connect(ruta)
    try:
        tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        c.close()
    if not TABLAS_ESPERADAS <= tablas:
        raise ValueError("El archivo recibido no es una base de OweeStudent")


def recibir(conn, enlace: str, db_path: str) -> str:
    """Se conecta al otro equipo, mezcla su base con la tuya y le devuelve el resultado (quedan iguales)."""
    from engine.merge import es_virgen, fusionar
    enlace = enlace.strip()
    if not enlace.startswith("http"):
        enlace = "http://" + enlace
    u = urlparse(enlace)
    token = parse_qs(u.query).get("t", [""])[0]
    if not token:
        raise ValueError("El enlace no incluye la clave (?t=...)")
    base = f"{u.scheme}://{u.netloc}"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / "remota.db"
        with urllib.request.urlopen(f"{base}/db?t={token}", timeout=30) as r:
            tmp.write_bytes(r.read())
        _validar(tmp)
        if db_path != ":memory:" and Path(db_path).exists():
            shutil.copy(db_path, str(db_path) + ".respaldo")
        if es_virgen(conn):  # equipo nuevo: copia completa (conserva identidades)
            src = sqlite3.connect(tmp)
            try:
                src.backup(conn)
            finally:
                src.close()
            conn.commit()
            resumen = "Equipo nuevo: recibiste una copia completa"
        else:
            st = fusionar(conn, str(tmp))
            resumen = f"Mezclado: {st['nuevos']} nuevos, {st['actualizados']} actualizados, {st['borrados']} borrados"
    req = urllib.request.Request(f"{base}/devolver?t={token}", _snapshot(conn), method="POST",
                                 headers={"Content-Type": "application/octet-stream"})
    try:
        urllib.request.urlopen(req, timeout=60).read()
        return resumen + ". El otro equipo también quedó actualizado."
    except Exception as ex:
        return resumen + f". Pero no pude devolverlo al otro equipo ({ex})."


def app_por_wifi_url(puerto=8550) -> str:
    return f"http://{ip_local()}:{puerto}"
