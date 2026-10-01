from datetime import date

import flet as ft

import threading

from database import repo
from engine import ai
from parsers.file_parser import EXTENSIONES


def build(st, ir_a_plan):
    inicio = ft.TextField(label="Fecha de inicio (AAAA-MM-DD)", value=date.today().isoformat(), width=250)
    hay_plan = st.plan_id is not None
    carpeta = ft.Dropdown(label="Guardar en la carpeta", width=320,
                          value=str(st.carpeta_destino) if st.carpeta_destino else "ninguna",
                          options=[ft.dropdown.Option("ninguna", "(Sin carpeta)")] + [
                              ft.dropdown.Option(str(k["id"]), k["nombre"]) for k in repo.carpetas(st.conn, st.perfil_id)])
    destino = ft.RadioGroup(value="agregar" if hay_plan else "nuevo", content=ft.Column([
        ft.Radio(value="nuevo", label="Crear un plan nuevo"),
        ft.Radio(value="agregar", label="Agregar al plan activo", disabled=not hay_plan),
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
            estado.value = f"Error: {ex}"
            st.page.update()
            return
        st.toast("Importado")
        ir_a_plan()

    def _carpeta():
        return None if carpeta.value in (None, "", "ninguna") else int(carpeta.value)

    def desde_ruta(path):
        path = path.strip().strip("'\"")
        guardar(lambda f, pid: repo.importar_archivo(st.conn, path, f, st.perfil_id, pid, _carpeta()))

    ruta = ft.TextField(label="…o pega la ruta del archivo", expand=True)
    pegado = ft.TextField(label="…o pega aquí el texto (Markdown: temas, tablas de cronograma, etc.)",
                          multiline=True, min_lines=6, max_lines=12)

    def al_elegir(e: ft.FilePickerResultEvent):
        if e.files:
            desde_ruta(e.files[0].path)

    picker.on_result = al_elegir

    objetivo = ft.TextField(label="Objetivo (ej. Aprobar cálculo I / Aprender redes para IT / Inglés B2)")
    nivel = ft.Dropdown(label="Nivel", value="universitario", width=200, options=[
        ft.dropdown.Option(x) for x in ("primaria", "secundaria", "adolescente", "universitario", "adulto")])
    horas = ft.TextField(label="Horas/semana", value="10", width=130)
    meses = ft.TextField(label="Meses", value="6", width=100)
    espera = ft.ProgressRing(visible=False, width=20, height=20)

    def copiar_prompt(_):
        try:
            txt = ai.prompt_para_chat(objetivo.value or "mi tema", nivel.value, float(horas.value), int(meses.value))
        except ValueError:
            estado.value = "Revisa horas y meses (deben ser números)"
            st.page.update()
            return
        st.page.set_clipboard(txt)
        st.toast("Prompt copiado. Pégalo en tu chat de IA")

    def generar(_):
        if not ai.ia_disponible():
            estado.value = "Configura la IA en Ajustes (o usa «Copiar prompt» con tu chat)"
            st.page.update()
            return
        espera.visible = True
        st.page.update()

        def hacer():
            try:
                md = ai.generar_plan(objetivo.value, nivel.value, float(horas.value), int(meses.value))
                pegado.value = md
                estado.value = "Plan generado: revísalo/edítalo abajo y pulsa «Importar texto pegado»."
                estado.color = ft.Colors.GREEN_300
            except Exception as ex:
                estado.value, estado.color = f"Error IA: {ex}", ft.Colors.RED_300
            espera.visible = False
            st.page.update()
        threading.Thread(target=hacer, daemon=True).start()
    return ft.Column([
        ft.Text("Importar plan de estudios", style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.ExpansionTile(title=ft.Text("✨ Generar un plan con IA (opcional)"), controls=[
            ft.Column([objetivo, ft.Row([nivel, horas, meses], wrap=True),
                       ft.Row([ft.ElevatedButton("Generar", icon=ft.Icons.AUTO_AWESOME, on_click=generar),
                               ft.OutlinedButton("Copiar prompt para mi chat (Claude, ChatGPT…)", icon=ft.Icons.COPY,
                                                 on_click=copiar_prompt), espera]),
                       ft.Text("Con «Copiar prompt»: pégalo en tu chat, copia su respuesta y pégala abajo en "
                               "«Importar texto pegado». Funciona con tu suscripción normal, sin API.", size=12)])]),
        ft.Text("Acepta " + ", ".join(EXTENSIONES).upper() + " o texto pegado. Detecta módulos, temas, "
                "bibliografía, enlaces, entregables, idiomas y cronograma semanal."),
        destino, carpeta, inicio,
        ft.ElevatedButton("Elegir archivo", icon=ft.Icons.UPLOAD_FILE,
                          on_click=lambda _: picker.pick_files(allowed_extensions=EXTENSIONES)),
        ft.Row([ruta, ft.ElevatedButton("Importar", on_click=lambda _: desde_ruta(ruta.value))]),
        pegado,
        ft.ElevatedButton("Importar texto pegado", icon=ft.Icons.CONTENT_PASTE,
                          on_click=lambda _: guardar(lambda f, pid: repo.importar_texto(
                              st.conn, pegado.value, "Plan pegado", f, st.perfil_id, pid, _carpeta()))),
        estado,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
