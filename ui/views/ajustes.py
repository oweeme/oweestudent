import subprocess
import sys
import threading
from pathlib import Path

import flet as ft

from database.db import DB_PATH
from engine import ai, recursos, sync
from ui.components.widgets import tarjeta

_RAIZ = Path(__file__).resolve().parents[2]
_web = {"proc": None}


def build(st, recargar):
    aviso = ft.Text("")

    def msg(t, error=False):
        aviso.value, aviso.color = t, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- IA ----------
    cfg = ai.cargar_config()
    url = ft.TextField(label="Servidor local", value=cfg.get("local_url", "http://localhost:11434"))
    modelo_l = ft.Dropdown(label="Modelo local", value=cfg.get("local_modelo"),
                           options=[ft.dropdown.Option(cfg["local_modelo"])] if cfg.get("local_modelo") else [])
    remoto = ft.TextField(label="IA de otro equipo (opcional, ej. http://192.168.1.50:11434)",
                          value=cfg.get("remoto_url", ""))
    modelo_r = ft.Dropdown(label="Modelo del otro equipo", value=cfg.get("remoto_modelo"),
                           options=[ft.dropdown.Option(cfg["remoto_modelo"])] if cfg.get("remoto_modelo") else [])
    def detectar(_):
        try:
            hallado = ai.detectar_local() if not url.value.strip() else (url.value.strip(), ai.modelos_locales(url.value.strip()))
            if hallado is None:
                raise RuntimeError("No encontré ningún servidor. ¿Está Ollama/LM Studio abierto?")
            url.value, ms = hallado
            modelo_l.options = [ft.dropdown.Option(m) for m in ms]
            modelo_l.value = modelo_l.value if modelo_l.value in ms else ms[0]
            msg(f"Encontrados {len(ms)} modelos en {url.value}")
        except Exception as ex:
            msg(f"No se pudo conectar: {ex}", True)

    def autodetectar(_):
        url.value = ""
        detectar(_)

    def buscar_red(_):
        msg("Buscando IA en tu red…")

        def hacer():
            try:
                hallados = ai.buscar_en_red()
                if not hallados:
                    msg("No encontré ninguna. En el otro equipo inicia Ollama así: OLLAMA_HOST=0.0.0.0 ollama serve", True)
                    return
                remoto.value, ms = hallados[0]
                modelo_r.options = [ft.dropdown.Option(m) for m in ms]
                modelo_r.value = ms[0]
                msg(f"Encontrada: {remoto.value} ({len(ms)} modelos). Pulsa Guardar.")
            except Exception as ex:
                msg(f"Error buscando: {ex}", True)
        threading.Thread(target=hacer, daemon=True).start()

    def guardar_ia(_):
        ai.guardar_config(remoto_url=remoto.value.strip(), remoto_modelo=modelo_r.value or "",
                          local_url=url.value.strip(), local_modelo=modelo_l.value or "")
        msg("IA configurada (se guarda solo en este equipo, no se sincroniza)")

    def probar(_):
        def hacer():
            try:
                msg("Probando…")
                msg("Respuesta: " + ai._llm("Responde solo: listo", "Eres un asistente.", 20).strip()[:120])
            except Exception as ex:
                msg(f"Falló: {ex}", True)
        threading.Thread(target=hacer, daemon=True).start()

    total, libre = recursos.ram_gb()
    pct = ft.Slider(min=5, max=30, divisions=25, value=cfg.get("ram_pct", 10), label="{value}%")
    info_ram = ft.Text("")
    barra = ft.ProgressBar(value=0, visible=False)
    estado_pull = ft.Text("", size=12)

    def actualizar_reco(_=None):
        m, gb, desc, pres = recursos.recomendar(total, pct.value)
        aviso_min = "" if gb <= pres else "  ⚠ el presupuesto es menor que el modelo mínimo"
        info_ram.value = (f"RAM: {total:.1f} GB ({libre:.1f} libres). Presupuesto para la IA ({pct.value:.0f}%): "
                          f"{pres:.1f} GB → modelo recomendado: {m} (~{gb} GB, {desc}).{aviso_min}")
        info_ram.data = m
        st.page.update()

    pct.on_change = actualizar_reco
    m0, gb0, d0, pres0 = recursos.recomendar(total, pct.value)
    info_ram.value = (f"RAM: {total:.1f} GB ({libre:.1f} libres). Presupuesto para la IA ({pct.value:.0f}%): "
                      f"{pres0:.1f} GB → modelo recomendado: {m0} (~{gb0} GB, {d0}).")
    info_ram.data = m0

    def instalar_ia(_):
        modelo = info_ram.data
        base = url.value.strip() or "http://localhost:11434"
        barra.visible, barra.value = True, 0

        def prog(f, txt):
            barra.value, estado_pull.value = f, f"{txt} {f:.0%}" if f else txt
            st.page.update()

        def hacer():
            try:
                recursos.descargar_modelo(base, modelo, prog)
                url.value = base
                modelo_l.options = [ft.dropdown.Option(m) for m in ai.modelos_locales(base)]
                modelo_l.value = modelo
                ai.guardar_config(local_url=base, local_modelo=modelo, ram_pct=pct.value)
                msg(f"Modelo {modelo} instalado y configurado")
            except Exception as ex:
                msg("No se pudo descargar. ¿Está Ollama instalado y abierto? (ollama.com/download) "
                    f"Detalle: {ex}", True)
            barra.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    tarj_ia = tarjeta(
        "Inteligencia artificial (opcional)",
        ft.Text("Sin IA la app ya reprograma atrasados y proyecta tu fin. Con IA añade: generar un plan desde un "
                "objetivo (Importar) y evaluar tus resúmenes (Estudiar). En modo local nada sale de tu equipo."),
        info_ram, pct,
        ft.ElevatedButton("⬇ Instalar IA recomendada para mi RAM", icon=ft.Icons.MEMORY, on_click=instalar_ia),
        barra, estado_pull,
        ft.Row([url, ft.OutlinedButton("Detectar", on_click=autodetectar)]), modelo_l,
        ft.Text("Si este equipo no puede con la IA, usa la de otro (tu PC, por Wi-Fi). Si hay varias, la app "
                "prueba en orden: este equipo → otro equipo.", size=12),
        ft.Row([remoto, ft.OutlinedButton("Buscar en mi red", on_click=buscar_red)], wrap=True), modelo_r,
        ft.Row([ft.ElevatedButton("Guardar", on_click=guardar_ia), ft.OutlinedButton("Probar", on_click=probar)]))

    # ---------- Enviar por QR ----------
    zona_qr = ft.Column()
    compartir = {"s": None}

    def enviar(_):
        if compartir["s"]:
            compartir["s"].parar()
        try:
            s = compartir["s"] = sync.Compartir(st.conn)
            zona_qr.controls = [
                ft.Image(src_base64=sync.qr_base64(s.url), width=220, height=220),
                ft.Text(s.url, selectable=True, size=12),
                ft.Text("Válido 5 min. Ambos equipos en la misma Wi-Fi. Ve al otro equipo, «Recibir», y pega este enlace.", size=12)]
        except Exception as ex:
            msg(f"No se pudo compartir: {ex}", True)
            return
        st.page.update()

    def esperar_fin():
        s = compartir["s"]
        try:
            r = s.esperar_y_mezclar(st.conn) if s else None
        except Exception as ex:
            r = None
            msg(f"Error al mezclar: {ex}", True)
        if r is not None:
            st.elegir_perfil(st.perfil_id)
            zona_qr.controls = [ft.Text(f"✅ Sincronizado ({r['nuevos']} nuevos, {r['actualizados']} actualizados, "
                                        f"{r['borrados']} borrados). Vuelve a abrir la vista para ver los cambios.")]
            st.page.update()

    def enviar_y_vigilar(_):
        enviar(_)
        threading.Thread(target=esperar_fin, daemon=True).start()

    # ---------- Recibir ----------
    enlace = ft.TextField(label="Pega el enlace del otro equipo", hint_text="http://192.168.1.84:8765/?t=...")

    def recibir(_):
        def hacer():
            try:
                r = sync.recibir(st.conn, enlace.value, DB_PATH)
                st.elegir_perfil(st.perfil_id)
                msg(r)
                recargar()
            except Exception as ex:
                msg(f"Error al recibir: {ex}", True)
        threading.Thread(target=hacer, daemon=True).start()

    # ---------- App completa por Wi-Fi ----------
    zona_web = ft.Column()

    def alternar_web(_):
        p = _web["proc"]
        if p and p.poll() is None:
            p.terminate()
            _web["proc"] = None
            zona_web.controls = [ft.Text("Detenido")]
        else:
            _web["proc"] = subprocess.Popen([sys.executable, str(_RAIZ / "main.py"), "--web"], cwd=_RAIZ)
            url = sync.app_por_wifi_url()
            zona_web.controls = [ft.Image(src_base64=sync.qr_base64(url), width=220, height=220),
                                 ft.Text(url, selectable=True),
                                 ft.Text("Escanea con la cámara del móvil/tablet: abre OweeStudent en el navegador "
                                         "usando ESTA base de datos en vivo.", size=12)]
        st.page.update()

    movil = st.page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)
    return ft.Column([
        ft.Text("Ajustes", style=ft.TextThemeStyle.HEADLINE_SMALL), aviso, tarj_ia,
        *([] if movil else [tarjeta(
            "Usar en el móvil o tablet (sin instalar nada)",
            ft.Text("Mientras este equipo esté encendido, tu otro dispositivo usa la app por Wi-Fi."),
            ft.ElevatedButton("Activar / desactivar", icon=ft.Icons.QR_CODE_2, on_click=alternar_web), zona_web)]),
        tarjeta("Sincronizar con otro equipo",
                ft.Text("Estudia en cualquiera y sincroniza: se mezclan los cambios de los dos (gana el más reciente "
                        "en cada elemento) y ambos quedan iguales. Un equipo nuevo recibe una copia completa. "
                        "Se guarda un respaldo antes de mezclar."),
                ft.ElevatedButton("1) Mostrar QR en este equipo", icon=ft.Icons.QR_CODE, on_click=enviar_y_vigilar), zona_qr,
                ft.Divider(), enlace,
                ft.ElevatedButton("2) Sincronizar con el equipo del enlace", icon=ft.Icons.SYNC, on_click=recibir)),
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
