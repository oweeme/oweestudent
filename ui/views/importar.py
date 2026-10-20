from datetime import date

import flet as ft

import threading

from database import repo
from engine import ai
from i18n import t
from parsers.file_parser import EXTENSIONES
from ui.components.widgets import opciones_nivel


def build(st, ir_a_plan):
    inicio = ft.TextField(label=t("Fecha de inicio (AAAA-MM-DD)"), value=date.today().isoformat(), width=250)
    hay_plan = st.plan_id is not None
    carpeta = ft.Dropdown(label=t("Guardar en la carpeta"), width=320,
                          value=str(st.carpeta_destino) if st.carpeta_destino else "ninguna",
                          options=[ft.dropdown.Option("ninguna", t("(Sin carpeta)"))] + [
                              ft.dropdown.Option(str(k["id"]), k["nombre"]) for k in repo.carpetas(st.conn, st.perfil_id)])
    destino = ft.RadioGroup(value="agregar" if hay_plan else "nuevo", content=ft.Column([
        ft.Radio(value="nuevo", label=t("Crear un plan nuevo")),
        ft.Radio(value="agregar", label=t("Agregar al plan activo"), disabled=not hay_plan),
    ]))
    estado = ft.Text("", color=ft.Colors.RED_300)
    picker = ft.FilePicker()
    st.page.overlay.append(picker)

    def guardar(fn):
        try:
            f = date.fromisoformat(inicio.value)
            plan_id = st.plan_id if destino.value == "agregar" else None
            st.plan_id = fn(f, plan_id)
        except Exception as ex:  # formato, fecha o lectura inválidos
            estado.value = t("Error: {ex}", ex=ex)
            st.page.update()
            return
        st.toast(t("Importado"))
        ir_a_plan()

    def _carpeta():
        return None if carpeta.value in (None, "", "ninguna") else int(carpeta.value)

    def desde_ruta(path):
        path = path.strip().strip("'\"")
        guardar(lambda f, pid: repo.importar_archivo(st.conn, path, f, st.perfil_id, pid, _carpeta()))

    ruta = ft.TextField(label=t("…o pega la ruta del archivo"), expand=True)
    pegado = ft.TextField(label=t("…o pega aquí el texto (Markdown: temas, tablas de cronograma, etc.)"),
                          multiline=True, min_lines=6, max_lines=12)

    def al_elegir(e: ft.FilePickerResultEvent):
        if e.files:
            desde_ruta(e.files[0].path)

    picker.on_result = al_elegir

    objetivo = ft.TextField(label=t("Objetivo (ej. Aprobar cálculo I / Aprender redes para IT / Inglés B2)"))
    nivel = ft.Dropdown(label=t("Nivel"), value="universitario", width=200, options=opciones_nivel())
    horas = ft.TextField(label=t("Horas/semana"), value="10", width=130)
    meses = ft.TextField(label=t("Meses"), value="6", width=100)
    espera = ft.ProgressRing(visible=False, width=20, height=20)

    def copiar_prompt(_):
        try:
            txt = ai.prompt_para_chat(objetivo.value or "mi tema", nivel.value, float(horas.value), int(meses.value))
        except ValueError:
            estado.value = t("Revisa horas y meses (deben ser números)")
            st.page.update()
            return
        st.page.set_clipboard(txt)
        st.toast(t("Prompt copiado. Pégalo en tu chat de IA"))

    def generar(_):
        if not ai.ia_disponible():
            estado.value = t("Configura la IA en Ajustes (o usa «Copiar prompt» con tu chat)")
            st.page.update()
            return
        espera.visible = True
        st.page.update()

        def hacer():
            try:
                md = ai.generar_plan(objetivo.value, nivel.value, float(horas.value), int(meses.value))
                pegado.value = md
                estado.value = t("Plan generado: revísalo/edítalo abajo y pulsa «Importar texto pegado».")
                estado.color = ft.Colors.GREEN_300
            except Exception as ex:
                estado.value, estado.color = t("Error IA: {ex}", ex=ex), ft.Colors.RED_300
            espera.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()
    return ft.Column([
        ft.Text(t("Importar plan de estudios"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.ExpansionTile(title=ft.Text(t("✨ Generar un plan con IA (opcional)")), controls=[
            ft.Column([objetivo, ft.Row([nivel, horas, meses], wrap=True),
                       ft.Row([ft.ElevatedButton(t("Generar"), icon=ft.Icons.AUTO_AWESOME, on_click=generar),
                               ft.OutlinedButton(t("Copiar prompt para mi chat (Claude, ChatGPT…)"), icon=ft.Icons.COPY,
                                                 on_click=copiar_prompt), espera]),
                       ft.Text(t("Con «Copiar prompt»: pégalo en tu chat, copia su respuesta y pégala abajo en «Importar texto pegado». Funciona con tu suscripción normal, sin API."), size=12)])]),
        ft.Text(t("Acepta {formatos} o texto pegado. Detecta módulos, temas, bibliografía, enlaces, entregables, idiomas y cronograma semanal.",
                  formatos=", ".join(EXTENSIONES).upper())),
        destino, carpeta, inicio,
        ft.ElevatedButton(t("Elegir archivo"), icon=ft.Icons.UPLOAD_FILE,
                          on_click=lambda _: picker.pick_files(allowed_extensions=EXTENSIONES)),
        ft.Row([ruta, ft.ElevatedButton(t("Importar"), on_click=lambda _: desde_ruta(ruta.value))]),
        pegado,
        ft.ElevatedButton(t("Importar texto pegado"), icon=ft.Icons.CONTENT_PASTE,
                          on_click=lambda _: guardar(lambda f, pid: repo.importar_texto(
                              st.conn, pegado.value, t("Plan pegado"), f, st.perfil_id, pid, _carpeta()))),
        estado,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
