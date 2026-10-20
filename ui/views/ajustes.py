import threading
from datetime import date

import flet as ft

import app_info
import i18n
from database.db import DB_PATH
from engine import ai, ia_auto, ia_local, recursos
from engine import respaldo as respaldo_motor
from i18n import cobertura, fuentes, t
from ui.components import guardar
from ui.components.logo import logo
from ui.components.widgets import confirmar, tarjeta


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

    # ---------- activar con un botón: usa lo que ya hay y solo descarga si hace falta ----------
    texto_auto = ft.Text("", size=13)
    barra_auto = ft.ProgressBar(value=0, visible=False)
    detalle_auto = ft.Text("", size=12)
    btn_auto = ft.ElevatedButton(t("✨ Activar IA"), icon=ft.Icons.AUTO_AWESOME)

    def refrescar_auto():
        if ai.ia_disponible():
            texto_auto.value = t("✅ Tu IA está lista.")
            btn_auto.visible = False
        else:
            d = ia_auto.diagnostico(pct.value)
            texto_auto.value = ia_auto.describir(d)
            btn_auto.visible = d["accion"] != "ninguna"

    def activar_auto(_):
        btn_auto.disabled = True
        barra_auto.visible, barra_auto.value = True, None
        st.page.update()

        def prog(f, texto):
            barra_auto.value, detalle_auto.value = f or None, f"{texto}  ({f:.0%})" if f else texto
            st.page.update()

        def hacer():
            try:
                msg(ia_auto.activar(prog, pct.value))
            except Exception as ex:
                msg(t("No se pudo activar: {ex}", ex=ex), True)
            barra_auto.visible = False
            btn_auto.disabled = False
            refrescar_int()
            refrescar_auto()
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    btn_auto.on_click = activar_auto
    refrescar_auto()

    avanzadas = ft.ExpansionTile(title=ft.Text(t("Opciones avanzadas (Ollama / IA de otro equipo)")), controls=[
        ft.Column([
            estado_int, plan_int, pct, ft.Row([btn_instalar, btn_quitar], wrap=True), barra_int, texto_int,
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
        texto_auto, btn_auto, barra_auto, detalle_auto,
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

    falta = fuentes.comando_para_instalar(i18n.idioma())   # chino/japonés en un Linux sin fuente CJK
    aviso_fuente = ft.Text(t("Tu sistema no tiene una fuente para este idioma y verás cuadros vacíos. Instálala con: {comando}",
                             comando=falta), color=ft.Colors.AMBER_400, selectable=True, visible=bool(falta))

    idioma = ft.Dropdown(label=t("Idioma de la interfaz"), width=260, value=i18n.idioma(), on_change=cambiar_idioma,
                         options=[ft.dropdown.Option(c, i18n.NOMBRES[c]) for c in i18n.disponibles()])

    def cambiar_escritura(e):
        i18n.fijar_escritura_owee(e.control.value)
        ai.guardar_config(owee_escritura=bool(e.control.value))
        reconstruir()

    owee_ajustes = []
    if i18n.idioma() == "qow":
        owee_ajustes = [ft.Switch(label=t("Mostrar en escritura Owee (glifos)"), value=i18n.escritura_owee(),
                                  on_change=cambiar_escritura)]
        inf = cobertura.informe("qow")

        def copiar_lista(_):
            st.page.set_clipboard(cobertura.como_tsv(inf["faltan"]))
            msg(t("Lista copiada: llévala al glosario de Owee (inglés · español)."))

        owee_ajustes_card = tarjeta(
            t("Cobertura de Owee"),
            ft.ProgressBar(value=inf["traducidos"] / inf["total"]),
            ft.Text(t("{a} de {b} textos de la interfaz ya están en Owee. Lo que falta se ve en inglés (nunca se inventan palabras Owee).",
                      a=inf["traducidos"], b=inf["total"]), size=13),
            ft.OutlinedButton(t("Copiar lista de textos por traducir"), icon=ft.Icons.COPY, on_click=copiar_lista),
            ft.ExpansionTile(title=ft.Text(t("Textos que faltan (los más cortos primero)")),
                             controls=[ft.Text(f"{en}", size=12, selectable=True) for _, en in inf["faltan"][:60]]))
    else:
        owee_ajustes_card = None

    apariencia = tarjeta(
        t("Apariencia"),
        ft.SegmentedButton(selected={cfg.get("tema", "dark")}, allow_multiple_selection=False, on_change=cambiar_tema,
                           segments=[ft.Segment(value="dark", label=ft.Text(t("Oscuro")), icon=ft.Icon(ft.Icons.DARK_MODE)),
                                     ft.Segment(value="light", label=ft.Text(t("Claro")), icon=ft.Icon(ft.Icons.LIGHT_MODE)),
                                     ft.Segment(value="system", label=ft.Text(t("Auto")), icon=ft.Icon(ft.Icons.BRIGHTNESS_AUTO))]),
        idioma, aviso_fuente, *owee_ajustes)

    # ---------- copia de seguridad ----------
    def escribir_copia(destino):
        r = respaldo_motor.crear_copia(st.conn, destino, con_archivos=con_archivos.value)
        copia_info.value = t("Archivos de material incluidos: {n}", n=r["archivos"])

    def copia_lista(destino, error):
        msg(t("No se pudo guardar la copia: {ex}", ex=error) if error else t("✅ Copia guardada en: {ruta}", ruta=str(destino)), bool(error))

    picker_copia = guardar.preparar(st.page, lambda ruta: guardar.escribir_elegido(ruta, "zip", escribir_copia, copia_lista))
    con_archivos = ft.Switch(label=t("Incluir los archivos de material (PDF, Word…)"), value=True)
    copia_info = ft.Text("", size=12)
    ruta_copia = ft.TextField(label=t("Ruta de la copia (.zip) a restaurar"), width=320)

    def restaurar(ruta):
        ruta = (ruta or "").strip().strip("'\"")
        try:
            info = respaldo_motor.inspeccionar(ruta)
        except ValueError as ex:
            return msg(str(ex), True)

        def hacer():
            try:
                respaldo_motor.restaurar(st.conn, DB_PATH, ruta)
            except Exception as ex:
                return msg(t("No se pudo restaurar: {ex}", ex=ex), True)
            st.elegir_perfil(repo_perfil_inicial())
            st.toast(t("✅ Copia restaurada. Tus datos anteriores quedaron en la carpeta «respaldos»."))
            reconstruir()
        confirmar(st.page, t("Restaurar reemplaza tus datos actuales por los de la copia ({planes} asignaturas, {tarjetas} tarjetas, guardada {fecha}). Antes se guarda una copia automática de lo que tienes. ¿Continuar?",
                             planes=info["planes"], tarjetas=info["tarjetas"], fecha=info["fecha"][:10] or "?"), hacer)

    def repo_perfil_inicial():
        from database import repo
        return repo.perfiles(st.conn)[0]["id"]

    picker_restaurar = ft.FilePicker(on_result=lambda e: restaurar(e.files[0].path) if e.files and e.files[0].path else None)
    st.page.overlay.append(picker_restaurar)
    copia = tarjeta(
        t("Copia de seguridad"),
        ft.Text(t("Guarda todo tu estudio en un archivo (perfiles, asignaturas, tarjetas, lecturas, escritos…) para llevarlo a otro equipo o por si algo falla."), size=13),
        con_archivos,
        ft.Row([ft.ElevatedButton(t("Guardar copia de seguridad"), icon=ft.Icons.BACKUP,
                                  on_click=lambda _: guardar.guardar(st.page, picker_copia, f"OweeStudent-copia-{date.today():%Y%m%d}", "zip", escribir_copia, copia_lista))],
               wrap=True), copia_info,
        ft.Row([ruta_copia, ft.OutlinedButton(t("Restaurar"), icon=ft.Icons.RESTORE, on_click=lambda _: restaurar(ruta_copia.value)),
                *([ft.OutlinedButton(t("Elegir archivo…"), icon=ft.Icons.FOLDER_OPEN,
                                     on_click=lambda _: picker_restaurar.pick_files(allowed_extensions=["zip"]))] if guardar.hay_dialogo(st.page) else [])], wrap=True))

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
        ft.Text(t("Ajustes"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), aviso, tarj_ia,
        apariencia,
        *([owee_ajustes_card] if owee_ajustes_card else []),
        copia,
        acerca,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
