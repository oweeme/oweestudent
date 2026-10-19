import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from database import repo
from database.db import DB_PATH
from engine import ai, enlace, sync
from i18n import t
from ui.components.widgets import dialogo, tarjeta

_RAIZ = Path(__file__).resolve().parents[2]
_web = {"proc": None}


def build(st, recargar):
    aviso = ft.Text("")
    c = st.conn

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- nombre de este equipo ----------
    nombre = ft.TextField(label=t("Nombre de este equipo"), value=sync.nombre_equipo(), width=280)

    def guardar_nombre(_):
        ai.guardar_config(nombre_equipo=nombre.value.strip())
        msg(t("Nombre guardado"))

    # ---------- dar permiso (mostrar PIN y QR) ----------
    opciones = [ft.dropdown.Option("todo", t("Todo mi estudio"))] + [
        ft.dropdown.Option(str(k["id"]), t("Solo la carpeta «{nombre}»", nombre=k["nombre"])) for k in repo.carpetas(c, st.perfil_id)]
    que = ft.Dropdown(label=t("Qué compartir"), value="todo", options=opciones)
    zona_pin = ft.Column(visible=False, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    compartir = {"s": None}

    def esperar(s):
        try:
            r = s.esperar_y_mezclar(c)
        except Exception as ex:
            msg(t("Error al mezclar: {ex}", ex=ex), True)
            return
        if s.bloqueado:
            zona_pin.controls = [ft.Text(t("Se cerró por demasiados PIN incorrectos. Vuelve a empezar."), color=ft.Colors.RED_300)]
        elif r is not None:
            st.elegir_perfil(st.perfil_id)
            zona_pin.controls = [ft.Text(t("✅ Sincronizado: {nuevos} nuevos, {actualizados} actualizados, {borrados} borrados.",
                                         nuevos=r["nuevos"], actualizados=r["actualizados"], borrados=r["borrados"]), size=16)]
        else:
            zona_pin.controls = [ft.Text(t("El tiempo terminó sin sincronizar. Puedes volver a intentarlo."))]
        st.page.update()

    def permitir(_):
        if compartir["s"]:
            compartir["s"].parar()
        try:
            carpeta = None if que.value == "todo" else int(que.value)
            s = compartir["s"] = sync.Compartir(c, carpeta_id=carpeta)
        except Exception as ex:
            msg(t("No se pudo abrir la sincronización: {ex}", ex=ex), True)
            return
        zona_pin.controls = [
            ft.Text(t("Este equipo aparece como «{nombre}»", nombre=s.nombre), size=14),
            ft.Text("PIN", size=12),
            ft.Text(" ".join(s.token), size=44, weight=ft.FontWeight.BOLD, selectable=True),
            ft.Text(t("En el otro equipo: Sincronizar → Buscar equipos → elige este → escribe el PIN."), size=12,
                    text_align=ft.TextAlign.CENTER),
            ft.ExpansionTile(title=ft.Text(t("Otras formas de conectar (IP / QR)")), controls=[
                ft.Text(t("IP de este equipo: {ip}", ip=s.url.split("/?")[0].replace("http://", "")), selectable=True),
                ft.Image(src_base64=sync.qr_base64(enlace.crear(sync.ip_local(), sync.PUERTO, s.token)), width=180, height=180),
                ft.Text(t("QR con enlace propio: al escanearlo con la cámara del móvil, Android debería abrir OweeStudent y conectar solo (experimental). Si solo ves texto, cópialo en «Conectar por IP»."), size=11)]),
            ft.Text(t("Válido 5 minutos. Mientras tanto, deja esta pantalla abierta."), size=12)]
        zona_pin.visible = True
        st.page.update()
        threading.Thread(target=esperar, args=(s,), daemon=True).start()

    # ---------- buscar equipos y conectar ----------
    lista = ft.Column()
    espera = ft.ProgressRing(visible=False, width=22, height=22)

    def conectar(base, etiqueta):
        pin = ft.TextField(label=t("PIN que muestra el otro equipo"), keyboard_type=ft.KeyboardType.NUMBER,
                           max_length=6, autofocus=True)

        def ok(v):
            def hacer():
                try:
                    msg(t("Sincronizando con {equipo}…", equipo=etiqueta))
                    r = sync.recibir(c, base, DB_PATH, pin=v[0])
                    st.elegir_perfil(st.perfil_id)
                    msg("✅ " + r)
                except Exception as ex:
                    msg(t("No se pudo sincronizar: {ex}", ex=ex), True)
            threading.Thread(target=hacer, daemon=True).start()
        dialogo(st.page, t("Sincronizar con {equipo}", equipo=etiqueta), [pin], ok, t("Sincronizar"))

    def buscar(_):
        lista.controls = [ft.Text(t("Buscando equipos en tu Wi-Fi…"))]
        espera.visible = True
        st.page.update()

        def hacer():
            try:
                hallados = sync.buscar_equipos()
            except Exception as ex:
                hallados = []
                msg(t("Error buscando: {ex}", ex=ex), True)
            if hallados:
                lista.controls = [ft.ListTile(
                    leading=ft.Icon(ft.Icons.COMPUTER), title=ft.Text(h["nombre"]),
                    subtitle=ft.Text(t("Carpeta: {nombre}", nombre=h["carpeta"]) if h["carpeta"] else t("Todo su estudio")),
                    trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                    on_click=lambda _, h=h: conectar(h["url"], h["nombre"])) for h in hallados]
            else:
                yo = sync.ip_local()
                lista.controls = [
                    ft.Text(t("No encontré equipos en {red}.x (tu IP: {ip}).", red=yo.rsplit(".", 1)[0], ip=yo), weight=ft.FontWeight.BOLD),
                    ft.Text(t("1) En el otro equipo abre Sincronizar → «Permitir sincronización».  2) Ambos en el mismo Wi-Fi.  3) Si sigue sin aparecer, su cortafuegos puede estar bloqueando: prueba AL REVÉS (permite aquí y busca desde el otro) o usa «Conectar por IP» → «Probar conexión» para saber el motivo."), size=13)]
            espera.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    ip = ft.TextField(label=t("IP del otro equipo, o el enlace del QR"), width=300)
    resultado_diag = ft.Text("", size=13)

    def probar_conexion(_):
        pegado = enlace.leer(ip.value)
        host = (pegado[0].replace("http://", "") if pegado else ip.value.strip()).split(":")[0]
        if not host:
            resultado_diag.value = t("Escribe primero la IP del otro equipo.")
            st.page.update()
            return
        resultado_diag.value = t("Probando…")
        st.page.update()

        def hacer():
            ok, texto = sync.diagnosticar(host)
            resultado_diag.value, resultado_diag.color = texto, (ft.Colors.GREEN_400 if ok else ft.Colors.RED_300)
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()
    pin_ip = ft.TextField(label=t("PIN"), width=120, max_length=6, keyboard_type=ft.KeyboardType.NUMBER)

    def por_ip(_):
        host = ip.value.strip()
        if not host:
            msg(t("Escribe la IP"), True)
            return
        pegado = enlace.leer(host)                 # también vale el texto del QR: oweestudent://sync/IP:8765/PIN
        if pegado:
            host, pin_ip.value = pegado[0].replace("http://", ""), pegado[1]
        elif ":" not in host:
            host += f":{sync.PUERTO}"

        def hacer():
            try:
                msg(t("Sincronizando…"))
                r = sync.recibir(c, host, DB_PATH, pin=pin_ip.value)
                st.elegir_perfil(st.perfil_id)
                msg("✅ " + r)
            except Exception as ex:
                msg(t("No se pudo sincronizar: {ex}", ex=ex), True)
        threading.Thread(target=hacer, daemon=True).start()

    # ---------- app del PC en el móvil (solo escritorio) ----------
    zona_web = ft.Column()

    def alternar_web(_):
        p = _web["proc"]
        if p and p.poll() is None:
            p.terminate()
            _web["proc"] = None
            zona_web.controls = [ft.Text(t("Detenido"))]
        else:
            _web["proc"] = subprocess.Popen([sys.executable, str(_RAIZ / "main.py"), "--web"], cwd=_RAIZ)
            u = sync.app_por_wifi_url()
            zona_web.controls = [ft.Image(src_base64=sync.qr_base64(u), width=200, height=200),
                                 ft.Text(u, selectable=True),
                                 ft.Text(t("Escanea con la cámara del móvil: abre OweeStudent en el navegador, con los datos de este equipo en vivo."), size=12)]
        st.page.update()

    movil = st.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    return ft.Column([
        ft.Text(t("Sincronizar"), style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
        ft.Text(t("Estudia en cualquier equipo y sincroniza: se mezclan los cambios de los dos (gana el más reciente en cada elemento) y ambos quedan iguales. Se guarda un respaldo antes de mezclar."), size=13),
        tarjeta(t("1 · Este equipo"), ft.Row([nombre, ft.OutlinedButton(t("Guardar"), on_click=guardar_nombre)], wrap=True)),
        tarjeta(t("2 · Dar permiso a otro equipo"), que,
                ft.ElevatedButton(t("Permitir sincronización"), icon=ft.Icons.LOCK_OPEN, on_click=permitir), zona_pin),
        tarjeta(t("3 · Buscar equipos cercanos"),
                ft.Row([ft.ElevatedButton(t("Buscar equipos"), icon=ft.Icons.SEARCH, on_click=buscar), espera]), lista,
                ft.ExpansionTile(title=ft.Text(t("¿No aparece? Conectar por IP")), controls=[
                    ft.Row([ip, pin_ip], wrap=True),
                    ft.Row([ft.OutlinedButton(t("Probar conexión"), icon=ft.Icons.NETWORK_CHECK, on_click=probar_conexion),
                            ft.ElevatedButton(t("Sincronizar"), icon=ft.Icons.SYNC, on_click=por_ip)], wrap=True),
                    resultado_diag])),
        *([] if movil else [tarjeta(
            t("Usar en el móvil sin instalar nada"),
            ft.Text(t("Mientras este equipo esté encendido, tu móvil o tablet usa la app por Wi-Fi.")),
            ft.ElevatedButton(t("Activar / desactivar"), icon=ft.Icons.QR_CODE_2, on_click=alternar_web), zona_web)]),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
