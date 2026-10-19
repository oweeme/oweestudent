import threading

import flet as ft

import app_info
import i18n
from engine import ai, ia_local, recursos
from i18n import t
from ui.components.logo import logo
from ui.components.widgets import tarjeta


def build(st, recargar, reconstruir=lambda: None):
    aviso = ft.Text("")

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- IA ----------
    cfg = ai.cargar_config()
    url = ft.TextField(label=t("Servidor local"), value=cfg.get("local_url", "http://localhost:11434"), width=280)
    modelo_l = ft.Dropdown(label=t("Modelo local"), width=320, value=cfg.get("local_modelo"),
                           options=[ft.dropdown.Option(cfg["local_modelo"])] if cfg.get("local_modelo") else [])
    remoto = ft.TextField(label=t("IA de otro equipo (opcional, ej. http://192.168.1.50:11434)"),
                          value=cfg.get("remoto_url", ""), width=280)
    modelo_r = ft.Dropdown(label=t("Modelo del otro equipo"), width=320, value=cfg.get("remoto_modelo"),
                           options=[ft.dropdown.Option(cfg["remoto_modelo"])] if cfg.get("remoto_modelo") else [])
    def detectar(_):
        try:
            hallado = ai.detectar_local() if not url.value.strip() else (url.value.strip(), ai.modelos_locales(url.value.strip()))
            if hallado is None:
                raise RuntimeError(t("No encontré ningún servidor. ¿Está Ollama/LM Studio abierto?"))
            url.value, ms = hallado
            modelo_l.options = [ft.dropdown.Option(m) for m in ms]
            modelo_l.value = modelo_l.value if modelo_l.value in ms else ms[0]
            msg(t("Encontrados {n} modelos en {url}", n=len(ms), url=url.value))
        except Exception as ex:
            msg(t("No se pudo conectar: {ex}", ex=ex), True)

    def autodetectar(_):
        url.value = ""
        detectar(_)

    def buscar_red(_):
        msg(t("Buscando IA en tu red…"))

        def hacer():
            try:
                hallados = ai.buscar_en_red()
                if not hallados:
                    msg(t("No encontré ninguna. En el otro equipo inicia Ollama así: OLLAMA_HOST=0.0.0.0 ollama serve"), True)
                    return
                remoto.value, ms = hallados[0]
                modelo_r.options = [ft.dropdown.Option(m) for m in ms]
                modelo_r.value = ms[0]
                msg(t("Encontrada: {url} ({n} modelos). Pulsa Guardar.", url=remoto.value, n=len(ms)))
            except Exception as ex:
                msg(t("Error buscando: {ex}", ex=ex), True)
        threading.Thread(target=hacer, daemon=True).start()

    def guardar_ia(_):
        ai.guardar_config(remoto_url=remoto.value.strip(), remoto_modelo=modelo_r.value or "",
                          local_url=url.value.strip(), local_modelo=modelo_l.value or "")
        msg(t("IA configurada (se guarda solo en este equipo, no se sincroniza)"))

    def probar(_):
        def hacer():
            try:
                msg(t("Probando…"))
                msg(t("Respuesta: {texto}", texto=ai._llm("Responde solo: listo", "Eres un asistente.", 20).strip()[:120]))
            except Exception as ex:
                msg(t("Falló: {ex}", ex=ex), True)
        threading.Thread(target=hacer, daemon=True).start()

    total, libre = recursos.ram_gb()
    pct = ft.Slider(min=5, max=30, divisions=25, value=cfg.get("ram_pct", 10), label="{value}%")
    info_ram = ft.Text("")
    barra = ft.ProgressBar(value=0, visible=False)
    estado_pull = ft.Text("", size=12)

    def actualizar_reco(_=None):
        m, gb, desc, pres = recursos.recomendar(total, pct.value)
        aviso_min = "" if gb <= pres else t("  ⚠ el presupuesto es menor que el modelo mínimo")
        info_ram.value = t("RAM: {total:.1f} GB ({libre:.1f} libres). Presupuesto para la IA ({pct:.0f}%): {pres:.1f} GB → modelo recomendado: {m} (~{gb} GB, {desc}).",
                           total=total, libre=libre, pct=pct.value, pres=pres, m=m, gb=gb, desc=t(desc)) + aviso_min
        info_ram.data = m
        st.page.update()

    pct.on_change = actualizar_reco
    m0, gb0, d0, pres0 = recursos.recomendar(total, pct.value)
    info_ram.value = t("RAM: {total:.1f} GB ({libre:.1f} libres). Presupuesto para la IA ({pct:.0f}%): {pres:.1f} GB → modelo recomendado: {m} (~{gb} GB, {desc}).",
                       total=total, libre=libre, pct=pct.value, pres=pres0, m=m0, gb=gb0, desc=t(d0))
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
                msg(t("Modelo {modelo} instalado y configurado", modelo=modelo))
            except Exception as ex:
                msg(t("No se pudo descargar. ¿Está Ollama instalado y abierto? (ollama.com/download) Detalle: {ex}", ex=ex), True)
            barra.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    # ---------- IA integrada (la opción simple) ----------
    plataforma_ok = ia_local.disponible_en_plataforma()
    estado_int = ft.Text("", size=14)
    plan_int = ft.Text("", size=13)
    barra_int = ft.ProgressBar(value=0, visible=False)
    texto_int = ft.Text("", size=12)
    btn_instalar = ft.ElevatedButton(t("⬇ Instalar IA (descarga única)"), icon=ft.Icons.AUTO_AWESOME)
    btn_quitar = ft.OutlinedButton(t("Desinstalar"), icon=ft.Icons.DELETE_OUTLINE)

    def refrescar_int():
        e = ia_local.estado()
        clave = e["modelo"] or ia_local.clave_modelo_para(total, pct.value)
        mb = ia_local.MODELOS[clave][2]
        if e["instalado"]:
            estado_int.value = t("✅ IA instalada (modelo {modelo}). Se enciende sola al usarla y se apaga después para no gastar RAM.", modelo=clave.upper())
        elif plataforma_ok:
            estado_int.value = t("La IA integrada todavía no está instalada.")
        else:
            estado_int.value = t("Este dispositivo no puede ejecutar la IA por sí solo. Usa la IA de tu PC: abre «Opciones avanzadas» → «Buscar en mi red».")
        plan_int.value = t("Se instalará el modelo {modelo} (~{gb:.1f} GB) y un motor de ~20 MB, elegido por tu RAM ({ram:.0f} GB, usando hasta el {pct:.0f}%). Se descarga una sola vez y puede continuar si se corta.",
                           modelo=clave.upper(), gb=mb / 1024, ram=total, pct=pct.value) if plataforma_ok and not e["instalado"] else ""
        btn_instalar.visible = plataforma_ok and not e["instalado"]
        btn_quitar.visible = e["instalado"]

    def instalar_int(_):
        clave = ia_local.clave_modelo_para(total, pct.value)
        btn_instalar.disabled = True
        barra_int.visible, barra_int.value = True, 0
        st.page.update()

        def prog(f, texto):
            barra_int.value, texto_int.value = f, f"{texto}  ({f:.0%})"
            st.page.update()

        def hacer():
            try:
                ia_local.instalar(clave, prog)
                ai.guardar_config(ram_pct=pct.value)
                msg(t("✅ IA instalada. Ya puedes usar «Generar plan con IA» y las tarjetas con IA."))
            except Exception as ex:
                msg(t("No se pudo instalar: {ex}", ex=ex), True)
            barra_int.visible = False
            btn_instalar.disabled = False
            refrescar_int()
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    def quitar_int(_):
        ia_local.desinstalar()
        msg(t("IA desinstalada"))
        refrescar_int()
        st.page.update()

    btn_instalar.on_click = instalar_int
    btn_quitar.on_click = quitar_int
    refrescar_int()
    pct.on_change = lambda e: (actualizar_reco(), refrescar_int(), st.page.update())

    avanzadas = ft.ExpansionTile(title=ft.Text(t("Opciones avanzadas (Ollama / IA de otro equipo)")), controls=[
        ft.Column([
            info_ram,
            ft.ElevatedButton(t("⬇ Instalar con Ollama (ya instalado)"), icon=ft.Icons.MEMORY, on_click=instalar_ia),
            barra, estado_pull,
            ft.Row([url, ft.OutlinedButton(t("Detectar"), on_click=autodetectar)], wrap=True), modelo_l,
            ft.Text(t("Si este equipo no puede con la IA, usa la de otro (tu PC, por Wi-Fi). Si hay varias, la app prueba en orden: integrada → Ollama de este equipo → otro equipo."), size=12),
            ft.Row([remoto, ft.OutlinedButton(t("Buscar en mi red"), on_click=buscar_red)], wrap=True), modelo_r,
            ft.Row([ft.ElevatedButton(t("Guardar"), on_click=guardar_ia), ft.OutlinedButton(t("Probar"), on_click=probar)],
                   wrap=True)], spacing=10)])

    tarj_ia = tarjeta(
        t("Inteligencia artificial (opcional)"),
        ft.Text(t("Sin IA la app ya reprograma atrasados, crea tarjetas de tus apuntes y proyecta tu fin. Con IA añade: generar un plan desde un objetivo y tarjetas/resúmenes del material. Todo ocurre en tu equipo: nada sale de él."), size=13),
        estado_int, plan_int, pct,
        ft.Row([btn_instalar, btn_quitar], wrap=True), barra_int, texto_int,
        ft.OutlinedButton(t("Probar la IA"), icon=ft.Icons.PLAY_ARROW, on_click=probar), avanzadas)

    def cambiar_tema(e):
        modo = next(iter(e.control.selected))
        ai.guardar_config(tema=modo)
        st.page.theme_mode = {"dark": ft.ThemeMode.DARK, "light": ft.ThemeMode.LIGHT, "system": ft.ThemeMode.SYSTEM}[modo]
        st.page.update()

    def cambiar_idioma(e):
        codigo = i18n.fijar_idioma(e.control.value)
        ai.guardar_config(idioma=codigo)
        reconstruir()

    idioma = ft.Dropdown(label=t("Idioma de la interfaz"), width=260, value=i18n.idioma(), on_change=cambiar_idioma,
                         options=[ft.dropdown.Option(c, i18n.NOMBRES[c]) for c in i18n.disponibles()])

    apariencia = tarjeta(
        t("Apariencia"),
        ft.SegmentedButton(selected={cfg.get("tema", "dark")}, allow_multiple_selection=False, on_change=cambiar_tema,
                           segments=[ft.Segment(value="dark", label=ft.Text(t("Oscuro")), icon=ft.Icon(ft.Icons.DARK_MODE)),
                                     ft.Segment(value="light", label=ft.Text(t("Claro")), icon=ft.Icon(ft.Icons.LIGHT_MODE)),
                                     ft.Segment(value="system", label=ft.Text(t("Auto")), icon=ft.Icon(ft.Icons.BRIGHTNESS_AUTO))]),
        idioma)

    def abrir(url):
        return lambda _: st.page.launch_url(url)

    acerca = tarjeta(
        t("Acerca de {app} · v{version}", app=app_info.NOMBRE, version=app_info.VERSION), logo(72),
        ft.Text(t("Creado por {autor}. Gratis y sin anuncios. Si te sirve, puedes apoyar su desarrollo.", autor=app_info.AUTOR)),
        ft.Row([ft.ElevatedButton(t("☕ Donar (PayPal)"), icon=ft.Icons.FAVORITE, on_click=abrir(app_info.DONACIONES)),
                ft.OutlinedButton(t("Sitio web"), icon=ft.Icons.PUBLIC, on_click=abrir(app_info.WEB)),
                ft.OutlinedButton(app_info.EMAIL, icon=ft.Icons.MAIL, on_click=abrir("mailto:" + app_info.EMAIL))],
               wrap=True))
    return ft.Column([
        ft.Text(t("Ajustes"), style=ft.TextThemeStyle.HEADLINE_SMALL), aviso, tarj_ia,
        apariencia,
        acerca,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
