import threading

import flet as ft

import app_info
from engine import ai, recursos
from ui.components.logo import logo
from ui.components.widgets import tarjeta


def build(st, recargar):
    aviso = ft.Text("")

    def msg(t, error=False):
        aviso.value, aviso.color = t, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- IA ----------
    cfg = ai.cargar_config()
    url = ft.TextField(label="Servidor local", value=cfg.get("local_url", "http://localhost:11434"), width=280)
    modelo_l = ft.Dropdown(label="Modelo local", width=320, value=cfg.get("local_modelo"),
                           options=[ft.dropdown.Option(cfg["local_modelo"])] if cfg.get("local_modelo") else [])
    remoto = ft.TextField(label="IA de otro equipo (opcional, ej. http://192.168.1.50:11434)",
                          value=cfg.get("remoto_url", ""), width=280)
    modelo_r = ft.Dropdown(label="Modelo del otro equipo", width=320, value=cfg.get("remoto_modelo"),
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
        ft.Row([url, ft.OutlinedButton("Detectar", on_click=autodetectar)], wrap=True), modelo_l,
        ft.Text("Si este equipo no puede con la IA, usa la de otro (tu PC, por Wi-Fi). Si hay varias, la app "
                "prueba en orden: este equipo → otro equipo.", size=12),
        ft.Row([remoto, ft.OutlinedButton("Buscar en mi red", on_click=buscar_red)], wrap=True), modelo_r,
        ft.Row([ft.ElevatedButton("Guardar", on_click=guardar_ia), ft.OutlinedButton("Probar", on_click=probar)], wrap=True))

    def cambiar_tema(e):
        modo = next(iter(e.control.selected))
        ai.guardar_config(tema=modo)
        st.page.theme_mode = {"dark": ft.ThemeMode.DARK, "light": ft.ThemeMode.LIGHT, "system": ft.ThemeMode.SYSTEM}[modo]
        st.page.update()

    apariencia = tarjeta(
        "Apariencia",
        ft.SegmentedButton(selected={cfg.get("tema", "dark")}, allow_multiple_selection=False, on_change=cambiar_tema,
                           segments=[ft.Segment(value="dark", label=ft.Text("Oscuro"), icon=ft.Icon(ft.Icons.DARK_MODE)),
                                     ft.Segment(value="light", label=ft.Text("Claro"), icon=ft.Icon(ft.Icons.LIGHT_MODE)),
                                     ft.Segment(value="system", label=ft.Text("Auto"), icon=ft.Icon(ft.Icons.BRIGHTNESS_AUTO))]))

    def abrir(url):
        return lambda _: st.page.launch_url(url)

    acerca = tarjeta(
        f"Acerca de {app_info.NOMBRE} · v{app_info.VERSION}", logo(72),
        ft.Text(f"Creado por {app_info.AUTOR}. Gratis y sin anuncios. Si te sirve, puedes apoyar su desarrollo."),
        ft.Row([ft.ElevatedButton("☕ Donar (PayPal)", icon=ft.Icons.FAVORITE, on_click=abrir(app_info.DONACIONES)),
                ft.OutlinedButton("Sitio web", icon=ft.Icons.PUBLIC, on_click=abrir(app_info.WEB)),
                ft.OutlinedButton(app_info.EMAIL, icon=ft.Icons.MAIL, on_click=abrir("mailto:" + app_info.EMAIL))],
               wrap=True))
    return ft.Column([
        ft.Text("Ajustes", style=ft.TextThemeStyle.HEADLINE_SMALL), aviso, tarj_ia,
        apariencia,
        acerca,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
