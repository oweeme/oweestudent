"""Sincronización por Wi-Fi local con QR: A muestra el QR, B se conecta, ambos quedan iguales (mezcla)."""
import base64
import io
import json
import os
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

from database.db import sin_triggers

PUERTO = 8765
MAX_FALLOS = 5  # intentos de PIN erróneos antes de cerrar el servidor
TABLAS_ESPERADAS = {"planes", "unidades", "temas", "notas"}


def nombre_equipo() -> str:
    from engine import ai
    return ai.cargar_config().get("nombre_equipo") or socket.gethostname() or "Mi equipo"


def ip_local() -> str:
    """IP de este equipo en la red local. Prueba varios destinos (en algunos Android el primero falla)."""
    for destino in ("8.8.8.8", "192.168.1.1", "10.0.0.1", "172.16.0.1", "10.255.255.255"):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect((destino, 1))  # UDP: no envía nada, solo elige la interfaz de red
            ip = s.getsockname()[0]
            if ip and not ip.startswith(("127.", "0.")):
                return ip
        except OSError:
            continue
        finally:
            s.close()
    return "127.0.0.1"


def diagnosticar(host: str, puerto: int = PUERTO) -> tuple[bool, str]:
    """Explica en palabras sencillas por qué no se puede conectar a otro equipo."""
    import errno
    yo = ip_local()
    if yo.startswith("127."):
        return False, "Este equipo no está conectado a ninguna red Wi-Fi/LAN."
    if host.rsplit(".", 1)[0] != yo.rsplit(".", 1)[0]:
        return False, (f"Los equipos parecen estar en redes distintas (este: {yo}, el otro: {host}). "
                       "Conecta ambos al mismo Wi-Fi (ojo con «red de invitados» o datos móviles).")
    try:
        with socket.create_connection((host, puerto), timeout=3):
            pass
    except socket.timeout:
        return False, ("El otro equipo no responde (tiempo agotado). Casi siempre es su CORTAFUEGOS bloqueando "
                       f"conexiones entrantes. En Linux: sudo ufw allow {puerto}/tcp  ·  En Deepin: Centro de control → "
                       f"Cortafuegos. O prueba al revés: pulsa «Permitir sincronización» en ESTE equipo y busca desde el otro.")
    except ConnectionRefusedError:
        return False, "El equipo está encendido pero la sincronización no está abierta: pulsa «Permitir sincronización» allí."
    except OSError as ex:
        if ex.errno in (errno.EHOSTUNREACH, errno.ENETUNREACH):
            return False, "No hay ruta hacia ese equipo: revisa que esté encendido y en el mismo Wi-Fi."
        return False, f"No se pudo conectar: {ex}"
    try:
        with urllib.request.urlopen(f"http://{host}:{puerto}/hola", timeout=3) as r:
            d = json.loads(r.read())
        return True, f"✅ Conectado con «{d.get('nombre', host)}». Falta el PIN."
    except Exception:
        return False, "Hay algo en ese puerto, pero no es OweeStudent."


def qr_base64(texto: str) -> str:
    import qrcode
    from qrcode.image.pure import PyPNGImage
    img = qrcode.make(texto, box_size=8, border=2, image_factory=PyPNGImage)
    buf = io.BytesIO()
    img.save(buf)
    return base64.b64encode(buf.getvalue()).decode()


def _snapshot(conn: sqlite3.Connection, carpeta_uid: str | None = None) -> bytes:
    """Copia de la base. Con `carpeta_uid` solo incluye esa carpeta (y sin claves ni lápidas de borrado),
    para compartir una carpeta sin exponer el resto de tu estudio."""
    with tempfile.TemporaryDirectory() as d:
        ruta = Path(d) / "s.db"
        dst = sqlite3.connect(ruta)
        conn.backup(dst)
        dst.execute("UPDATE _sync SET activo=1")      # sin triggers: quitar rutas locales no es una edición
        dst.execute("UPDATE materiales SET ruta=NULL")  # tus rutas de archivo no salen de tu equipo
        dst.execute("UPDATE _sync SET activo=0")
        dst.commit()
        if carpeta_uid:
            dst.execute("PRAGMA foreign_keys=ON")
            dst.execute("UPDATE _sync SET activo=1")  # sin triggers: estos borrados no son borrados reales
            c = dst.execute("SELECT id, perfil_id FROM carpetas WHERE uid=?", (carpeta_uid,)).fetchone()
            if c is None:
                dst.close()
                raise ValueError("Esa carpeta no existe")
            dst.execute("DELETE FROM planes WHERE carpeta_id IS NOT ?", (c[0],))
            dst.execute("DELETE FROM carpetas WHERE id != ?", (c[0],))
            dst.execute("DELETE FROM perfiles WHERE id != ?", (c[1],))
            dst.execute("UPDATE perfiles SET clave_hash=NULL, sal=NULL")
            dst.execute("DELETE FROM sesiones WHERE tema_id IS NULL")
            dst.execute("DELETE FROM repasos_log WHERE tema_id IS NULL OR tema_id NOT IN (SELECT id FROM temas)")
            dst.execute("DELETE FROM _tombstones")
            dst.execute("UPDATE _sync SET activo=0")
            dst.commit()
        dst.close()
        return ruta.read_bytes()


def _uid_carpeta(conn, carpeta_id):
    r = conn.execute("SELECT uid FROM carpetas WHERE id=?", (carpeta_id,)).fetchone() if carpeta_id else None
    return r[0] if r else None


class Compartir:
    """Sirve una copia de tu base y espera que el otro equipo devuelva la versión mezclada.

    Flujo: B descarga → B mezcla con lo suyo → B devuelve el resultado → A lo mezcla. Caduca a los `caduca` s.
    """

    def __init__(self, conn, caduca=300, carpeta_id=None):
        self.token = f"{secrets.randbelow(10 ** 6):06d}"   # PIN que el otro equipo debe escribir
        self.nombre = nombre_equipo()
        self.carpeta_uid = _uid_carpeta(conn, carpeta_id)
        self.carpeta_nombre = None
        if carpeta_id:
            r = conn.execute("SELECT nombre FROM carpetas WHERE id=?", (carpeta_id,)).fetchone()
            self.carpeta_nombre = r[0] if r else None
        self.url = None
        self.descargado = threading.Event()
        self.devuelto = threading.Event()
        self.bloqueado = False
        self._fallos = 0
        self._devuelto_bytes = None
        self._datos = _snapshot(conn, self.carpeta_uid)
        # archivos de material que este equipo puede ofrecer (hash -> ruta), solo de lo que se comparte
        filtro = "" if not self.carpeta_uid else (
            " AND plan_id IN (SELECT id FROM planes WHERE carpeta_id=(SELECT id FROM carpetas WHERE uid=?))")
        self._archivos = {r[0]: r[1] for r in conn.execute(
            "SELECT hash, ruta FROM materiales WHERE hash IS NOT NULL AND ruta IS NOT NULL" + filtro,
            (self.carpeta_uid,) if self.carpeta_uid else ())}
        token, datos, evento, yo = self.token, self._datos, self.descargado, self

        class H(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _pin_ok(self):
                q = parse_qs(urlparse(self.path).query)
                if secrets.compare_digest(q.get("t", [""])[0], token):
                    return True
                yo._fallos += 1
                if yo._fallos >= MAX_FALLOS:   # adivinar el PIN a la fuerza: se cierra el servidor
                    yo.bloqueado = True
                    threading.Thread(target=yo.parar, daemon=True).start()
                return False

            def do_POST(self):
                if urlparse(self.path).path != "/devolver" or not evento.is_set() or not self._pin_ok():
                    self.send_response(403); self.end_headers(); return
                n = int(self.headers.get("Content-Length", 0))
                if n <= 0 or n > 500_000_000:
                    self.send_response(400); self.end_headers(); return
                yo._devuelto_bytes = self.rfile.read(n)
                self.send_response(200); self.end_headers(); self.wfile.write(b"ok")
                yo.devuelto.set()

            def do_GET(self):
                ruta = urlparse(self.path).path
                if ruta == "/hola":   # descubrimiento: sin datos sensibles ni PIN
                    cuerpo = json.dumps({"app": "OweeStudent", "nombre": yo.nombre,
                                         "carpeta": yo.carpeta_nombre}).encode()
                    self.send_response(200); self.send_header("Content-Type", "application/json")
                    self.end_headers(); self.wfile.write(cuerpo); return
                if not self._pin_ok():
                    self.send_response(403); self.end_headers(); return
                if ruta.startswith("/material/"):
                    f = yo._archivos.get(ruta.rsplit("/", 1)[-1])
                    if not f or not os.path.exists(f):
                        self.send_response(404); self.end_headers(); return
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(os.path.getsize(f)))
                    self.end_headers()
                    with open(f, "rb") as fh:
                        shutil.copyfileobj(fh, self.wfile)
                    return
                if ruta == "/db":
                    self.send_response(200)
                    if yo.carpeta_uid:
                        self.send_header("X-Carpeta-Uid", yo.carpeta_uid)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(datos)))
                    self.end_headers(); self.wfile.write(datos)
                    evento.set()
                else:
                    html = ("<meta name=viewport content='width=device-width'><h2>OweeStudent</h2>"
                            "<p>Abre la app OweeStudent en el otro equipo, ve a <b>Ajustes → Sincronizar</b>, "
                            f"elige <b>{yo.nombre}</b> y escribe el PIN.</p>").encode()
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


def traer_material(conn, base: str, token: str) -> int:
    """Descarga del otro equipo los archivos de material que aquí faltan (se identifican por huella, sin duplicar)."""
    from engine import material
    n = 0
    for m in conn.execute("SELECT id, hash, ruta FROM materiales WHERE hash IS NOT NULL").fetchall():
        if m["ruta"] and os.path.exists(m["ruta"]):
            continue
        ya = conn.execute("SELECT ruta FROM materiales WHERE hash=? AND ruta IS NOT NULL", (m["hash"],)).fetchone()
        if ya and os.path.exists(ya["ruta"]):   # mismo archivo ya presente por otra asignatura
            with sin_triggers(conn):
                conn.execute("UPDATE materiales SET ruta=? WHERE id=?", (ya["ruta"], m["id"]))
            continue
        try:
            with tempfile.TemporaryDirectory() as d:
                tmp = Path(d) / "m.bin"
                with urllib.request.urlopen(f"{base}/material/{m['hash']}?t={token}", timeout=60) as r, open(tmp, "wb") as out:
                    shutil.copyfileobj(r, out)
                if material.hash_archivo(str(tmp)) != m["hash"]:
                    continue  # llegó corrupto: no se guarda
                ext = Path(conn.execute("SELECT nombre_archivo FROM materiales WHERE id=?", (m["id"],)).fetchone()[0] or "").suffix
                final = tmp.with_suffix(ext or ".bin")
                tmp.rename(final)
                with sin_triggers(conn):
                    conn.execute("UPDATE materiales SET ruta=? WHERE hash=?", (material.copiar_a_app(str(final), m["hash"]), m["hash"]))
                n += 1
        except Exception:
            continue  # el otro equipo no lo tiene o no pudo enviarlo: queda «vincular el archivo aquí»
    conn.commit()
    return n


def _validar(ruta):
    c = sqlite3.connect(ruta)
    try:
        tablas = {r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        c.close()
    if not TABLAS_ESPERADAS <= tablas:
        raise ValueError("El archivo recibido no es una base de OweeStudent")


def recibir(conn, enlace: str, db_path: str, pin: str | None = None) -> str:
    """Se conecta al otro equipo, mezcla su base con la tuya y le devuelve el resultado (quedan iguales)."""
    from engine.merge import es_virgen, fusionar
    enlace = enlace.strip()
    if not enlace.startswith("http"):
        enlace = "http://" + enlace
    u = urlparse(enlace)
    token = (pin or "").strip() or parse_qs(u.query).get("t", [""])[0]
    if not token:
        raise ValueError("Falta el PIN del otro equipo")
    base = f"{u.scheme}://{u.netloc}"
    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d) / "remota.db"
        try:
            with urllib.request.urlopen(f"{base}/db?t={token}", timeout=30) as r:
                tmp.write_bytes(r.read())
                carpeta_uid = r.headers.get("X-Carpeta-Uid")
        except urllib.error.HTTPError as ex:
            raise ValueError("PIN incorrecto" if ex.code == 403 else f"El otro equipo respondió {ex.code}") from ex
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
    n_arch = traer_material(conn, base, token)
    if n_arch:
        resumen += f"; {n_arch} archivos de material copiados"
    req = urllib.request.Request(f"{base}/devolver?t={token}", _snapshot(conn, carpeta_uid), method="POST",
                                 headers={"Content-Type": "application/octet-stream"})
    try:
        urllib.request.urlopen(req, timeout=60).read()
        return resumen + ". El otro equipo también quedó actualizado."
    except Exception as ex:
        return resumen + f". Pero no pude devolverlo al otro equipo ({ex})."


def buscar_equipos(puerto: int = PUERTO, incluir_propio: bool = False) -> list[dict]:
    """Busca en tu red (mismo /24) equipos OweeStudent con la sincronización abierta.
    Devuelve [{nombre, carpeta, url}]; no hace falta saber ninguna IP."""
    import json as _json
    from concurrent.futures import ThreadPoolExecutor
    yo = ip_local()
    base = yo.rsplit(".", 1)[0]

    def sonda(host):
        try:
            with socket.create_connection((host, puerto), timeout=0.5):
                pass
            with urllib.request.urlopen(f"http://{host}:{puerto}/hola", timeout=1.5) as r:
                d = _json.loads(r.read())
            if d.get("app") == "OweeStudent":
                return {"nombre": d.get("nombre", host), "carpeta": d.get("carpeta"), "url": f"http://{host}:{puerto}"}
        except Exception:
            return None

    hosts = [f"{base}.{i}" for i in range(1, 255) if incluir_propio or f"{base}.{i}" != yo]
    if incluir_propio and yo.startswith("127."):
        hosts = ["127.0.0.1"]
    with ThreadPoolExecutor(64) as ex:
        return [r for r in ex.map(sonda, hosts) if r]


def app_por_wifi_url(puerto=8550) -> str:
    return f"http://{ip_local()}:{puerto}"
