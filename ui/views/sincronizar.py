import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from database import repo
from database.db import DB_PATH
from engine import ai, sync
from ui.components.widgets import dialogo, tarjeta

_RAIZ = Path(__file__).resolve().parents[2]
_web = {"proc": None}


def build(st, recargar):
    aviso = ft.Text("")
    c = st.conn

    def msg(t, error=False):
        aviso.value, aviso.color = t, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- nombre de este equipo ----------
    nombre = ft.TextField(label="Nombre de este equipo", value=sync.nombre_equipo(), width=280)

    def guardar_nombre(_):
        ai.guardar_config(nombre_equipo=nombre.value.strip())
        msg("Nombre guardado")

    # ---------- dar permiso (mostrar PIN y QR) ----------
    opciones = [ft.dropdown.Option("todo", "Todo mi estudio")] + [
        ft.dropdown.Option(str(k["id"]), f"Solo la carpeta «{k['nombre']}»") for k in repo.carpetas(c, st.perfil_id)]
    que = ft.Dropdown(label="Qué compartir", value="todo", options=opciones)
    zona_pin = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    compartir = {"s": None}

    def esperar(s):
        try:
            r = s.esperar_y_mezclar(c)
        except Exception as ex:
            msg(f"Error al mezclar: {ex}", True)
            return
        if s.bloqueado:
            zona_pin.controls = [ft.Text("Se cerró por demasiados PIN incorrectos. Vuelve a empezar.", color=ft.Colors.RED_300)]
        elif r is not None:
            st.elegir_perfil(st.perfil_id)
            zona_pin.controls = [ft.Text(f"✅ Sincronizado: {r['nuevos']} nuevos, {r['actualizados']} actualizados, "
                                         f"{r['borrados']} borrados.", size=16)]
        else:
            zona_pin.controls = [ft.Text("El tiempo terminó sin sincronizar. Puedes volver a intentarlo.")]
        st.page.update()

    def permitir(_):
        if compartir["s"]:
            compartir["s"].parar()
        try:
            carpeta = None if que.value == "todo" else int(que.value)
            s = compartir["s"] = sync.Compartir(c, carpeta_id=carpeta)
        except Exception as ex:
            msg(f"No se pudo abrir la sincronización: {ex}", True)
            return
        zona_pin.controls = [
            ft.Text(f"Este equipo aparece como «{s.nombre}»", size=14),
            ft.Text("PIN", size=12),
            ft.Text(" ".join(s.token), size=44, weight=ft.FontWeight.BOLD, selectable=True),
            ft.Text("En el otro equipo: Sincronizar → Buscar equipos → elige este → escribe el PIN.", size=12,
                    text_align=ft.TextAlign.CENTER),
            ft.ExpansionTile(title=ft.Text("Otras formas de conectar (IP / QR)"), controls=[
                ft.Text(f"IP: {s.url.split('/?')[0].replace('http://', '')}", selectable=True),
                ft.Image(src_base64=sync.qr_base64(s.url), width=180, height=180)]),
            ft.Text("Válido 5 minutos. Mientras tanto, deja esta pantalla abierta.", size=12)]
        zona_pin.visible = True
        st.page.update()
        threading.Thread(target=esperar, args=(s,), daemon=True).start()

    # ---------- buscar equipos y conectar ----------
    lista = ft.Column()
    espera = ft.ProgressRing(visible=False, width=22, height=22)

    def conectar(base, etiqueta):
        pin = ft.TextField(label="PIN que muestra el otro equipo", keyboard_type=ft.KeyboardType.NUMBER,
                           max_length=6, autofocus=True)

        def ok(v):
            def hacer():
                try:
                    msg(f"Sincronizando con {etiqueta}…")
                    r = sync.recibir(c, base, DB_PATH, pin=v[0])
                    st.elegir_perfil(st.perfil_id)
                    msg("✅ " + r)
                except Exception as ex:
                    msg(f"No se pudo sincronizar: {ex}", True)
            threading.Thread(target=hacer, daemon=True).start()
        dialogo(st.page, f"Sincronizar con {etiqueta}", [pin], ok, "Sincronizar")

    def buscar(_):
        lista.controls = [ft.Text("Buscando equipos en tu Wi-Fi…")]
        espera.visible = True
        st.page.update()

        def hacer():
            try:
                hallados = sync.buscar_equipos()
            except Exception as ex:
                hallados = []
                msg(f"Error buscando: {ex}", True)
            if hallados:
                lista.controls = [ft.ListTile(
                    leading=ft.Icon(ft.Icons.COMPUTER), title=ft.Text(h["nombre"]),
                    subtitle=ft.Text(("Carpeta: " + h["carpeta"]) if h["carpeta"] else "Todo su estudio"),
                    trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                    on_click=lambda _, h=h: conectar(h["url"], h["nombre"])) for h in hallados]
            else:
                lista.controls = [ft.Text("No encontré equipos. En el otro equipo abre Sincronizar → «Permitir "
                                          "sincronización» y vuelve a buscar. Ambos deben estar en el mismo Wi-Fi.")]
            espera.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    ip = ft.TextField(label="IP del otro equipo (ej. 192.168.1.50)", width=240)
    pin_ip = ft.TextField(label="PIN", width=120, max_length=6, keyboard_type=ft.KeyboardType.NUMBER)

    def por_ip(_):
        host = ip.value.strip()
        if not host:
            msg("Escribe la IP", True)
            return
        if ":" not in host:
            host += f":{sync.PUERTO}"

        def hacer():
            try:
                msg("Sincronizando…")
                r = sync.recibir(c, host, DB_PATH, pin=pin_ip.value)
                st.elegir_perfil(st.perfil_id)
                msg("✅ " + r)
            except Exception as ex:
                msg(f"No se pudo sincronizar: {ex}", True)
        threading.Thread(target=hacer, daemon=True).start()

    # ---------- app del PC en el móvil (solo escritorio) ----------
    zona_web = ft.Column()

    def alternar_web(_):
        p = _web["proc"]
        if p and p.poll() is None:
            p.terminate()
            _web["proc"] = None
            zona_web.controls = [ft.Text("Detenido")]
        else:
            _web["proc"] = subprocess.Popen([sys.executable, str(_RAIZ / "main.py"), "--web"], cwd=_RAIZ)
            u = sync.app_por_wifi_url()
            zona_web.controls = [ft.Image(src_base64=sync.qr_base64(u), width=200, height=200),
                                 ft.Text(u, selectable=True),
                                 ft.Text("Escanea con la cámara del móvil: abre OweeStudent en el navegador, con los datos "
                                         "de este equipo en vivo.", size=12)]
        st.page.update()

    movil = st.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    return ft.Column([
        ft.Text("Sincronizar", style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
        ft.Text("Estudia en cualquier equipo y sincroniza: se mezclan los cambios de los dos (gana el más reciente "
                "en cada elemento) y ambos quedan iguales. Se guarda un respaldo antes de mezclar.", size=13),
        tarjeta("1 · Este equipo", ft.Row([nombre, ft.OutlinedButton("Guardar", on_click=guardar_nombre)], wrap=True)),
        tarjeta("2 · Dar permiso a otro equipo", que,
                ft.ElevatedButton("Permitir sincronización", icon=ft.Icons.LOCK_OPEN, on_click=permitir), zona_pin),
        tarjeta("3 · Buscar equipos cercanos",
                ft.Row([ft.ElevatedButton("Buscar equipos", icon=ft.Icons.SEARCH, on_click=buscar), espera]), lista,
                ft.ExpansionTile(title=ft.Text("¿No aparece? Conectar por IP"), controls=[
                    ft.Row([ip, pin_ip], wrap=True), ft.ElevatedButton("Sincronizar", icon=ft.Icons.SYNC, on_click=por_ip)])),
        *([] if movil else [tarjeta(
            "Usar en el móvil sin instalar nada",
            ft.Text("Mientras este equipo esté encendido, tu móvil o tablet usa la app por Wi-Fi."),
            ft.ElevatedButton("Activar / desactivar", icon=ft.Icons.QR_CODE_2, on_click=alternar_web), zona_web)]),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
