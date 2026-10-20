import threading
from pathlib import Path

import flet as ft

from database import repo
from database.db import DB_PATH
from engine import ai
from engine import busqueda as bq
from i18n import t

ICONOS = {"material": ft.Icons.MENU_BOOK, "nota": ft.Icons.EDIT_NOTE, "lectura": ft.Icons.ARTICLE}


def ruta_indice() -> Path:
    base = Path(DB_PATH).parent if DB_PATH != ":memory:" else Path.cwd()
    return base / "indice.db"


def build(st, ir_a_material, ir_a_lecturas, indice=None):
    c = st.conn
    idx = indice or bq.Indice(ruta_indice())
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    zona = ft.Column(spacing=10)
    estado = ft.Text("", size=12)
    barra = ft.ProgressBar(visible=False)
    ocupado = {"on": False}

    pregunta = ft.TextField(label=t("Tu pregunta sobre tus documentos"), multiline=True, min_lines=2, max_lines=4, autofocus=True)
    alcance = ft.Dropdown(label=t("Buscar en"), value="esta", width=280, options=[
        ft.dropdown.Option("esta", t("Esta asignatura")), ft.dropdown.Option("todas", t("Todas mis asignaturas"))])
    hay_ia = ai.ia_disponible()
    usar_ia = ft.Switch(label=t("Redactar una respuesta con la IA"), value=hay_ia, disabled=not hay_ia)

    def planes():
        if alcance.value == "todas":
            return [p["id"] for p in repo.planes(c, st.perfil_id)]
        return [st.plan_id] if st.plan_id else []

    def abrir(fuente):
        st.plan_id = fuente.plan_id or st.plan_id
        if fuente.origen == "lectura":
            st.abrir_lectura = fuente.ref_id
            ir_a_lecturas()
        else:
            st.abrir_material = (fuente.ref_id, fuente.pagina or 1)
            ir_a_material()

    def tarjeta_fuente(i, f, texto):
        return ft.Container(ft.Row([
            ft.Text(f"[{i}]", weight=ft.FontWeight.BOLD, size=14),
            ft.Column([ft.Row([ft.Icon(ICONOS[f.origen], size=16), ft.Text(f.etiqueta(), size=13, weight=ft.FontWeight.W_500, expand=True)]),
                       ft.Text(bq.recorte(f.texto, texto), size=12, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True),
                       ft.TextButton(t("Abrir donde aparece"), icon=ft.Icons.OPEN_IN_NEW, on_click=lambda _, f=f: abrir(f))],
                      spacing=2, expand=True)], vertical_alignment=ft.CrossAxisAlignment.START),
            padding=10, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT))

    def mostrar(texto, fuentes, resp, error_ia):
        bloques = []
        if resp is not None:
            if resp["encontrada"]:
                bloques.append(ft.Container(ft.Column([
                    ft.Text(t("Respuesta"), weight=ft.FontWeight.BOLD), ft.Text(resp["texto"], size=15, selectable=True),
                    *([ft.Text(t("⚠ La IA no citó ninguna fuente: no te fíes sin comprobarlo en los pasajes de abajo."),
                               color=ft.Colors.AMBER_400, size=12)] if resp["sin_citas"] else []),
                    ft.Text(t("Una IA pequeña puede equivocarse: comprueba cada cita en su fuente."), size=11, color=ft.Colors.OUTLINE),
                    ft.OutlinedButton(t("Copiar respuesta con citas"), icon=ft.Icons.COPY,
                                      on_click=lambda _: (st.page.set_clipboard(bq.con_citas(resp, fuentes)), st.toast(t("Copiado"))))],
                    spacing=6), padding=12, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST))
            else:
                bloques.append(ft.Text(t("La IA no encontró la respuesta en estos pasajes."), color=ft.Colors.AMBER_400))
        if error_ia:
            bloques.append(ft.Text(t("No se pudo redactar la respuesta: {ex}", ex=error_ia), color=ft.Colors.RED_300, size=12))
        bloques.append(ft.Text(t("Fuentes"), weight=ft.FontWeight.BOLD))
        bloques += [tarjeta_fuente(i, f, texto) for i, f in enumerate(fuentes, start=1)]
        zona.controls = bloques

    def preguntar(_=None):
        if ocupado["on"]:
            return
        texto = (pregunta.value or "").strip()
        if not texto:
            return
        ps = planes()
        if not ps:
            zona.controls = [ft.Text(t("Primero crea o elige una asignatura en «Planes»."))]
            st.page.update()
            return
        ocupado["on"] = True
        zona.controls = []
        st.page.update()

        def hacer():
            try:
                pendientes = bq.materiales_pendientes(c, idx, ps)
                fallidos = []
                for k, m in enumerate(pendientes, start=1):
                    estado.value = t("Preparando «{titulo}» ({i}/{n})… solo se hace una vez.", titulo=m["titulo"], i=k, n=len(pendientes))
                    barra.visible, barra.value = True, 0
                    st.page.update()
                    try:
                        idx.indexar_material(m["hash"], m["ruta"], lambda f: (setattr(barra, "value", f), st.page.update()))
                    except Exception:
                        fallidos.append(m["titulo"])
                barra.visible = False
                estado.value = ""
                fuentes = bq.buscar(c, idx, ps, texto)
                if not fuentes:
                    zona.controls = [ft.Text(t("No encontré nada parecido en tus documentos. Prueba con otras palabras (las mismas que "
                                               "usa el texto) o añade más material."), color=ft.Colors.AMBER_400)]
                else:
                    resp, error = None, None
                    if usar_ia.value and ai.ia_disponible():
                        estado.value = t("La IA está redactando la respuesta…")
                        st.page.update()
                        try:
                            resp = bq.responder(texto, fuentes)
                        except Exception as ex:
                            error = str(ex)
                        estado.value = ""
                    mostrar(texto, fuentes, resp, error)
                if fallidos:
                    zona.controls.append(ft.Text(t("No pude leer: {lista}", lista=", ".join(fallidos)), color=ft.Colors.RED_300, size=12))
            except Exception as ex:
                zona.controls = [ft.Text(t("Error: {ex}", ex=ex), color=ft.Colors.RED_300)]
            finally:
                ocupado["on"] = False
                barra.visible = False
                st.page.update()
        threading.Thread(target=hacer, daemon=True).start()

    pregunta.on_submit = preguntar
    cuerpo.controls = [
        ft.Text(t("Preguntar a mis documentos"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Busca la respuesta en tus archivos, tus notas y tus fichas de lectura, y te dice de dónde sale (documento y página). "
                  "Todo ocurre en tu equipo. Con una IA configurada además redacta la respuesta citando las fuentes."), size=13),
        ft.Row([alcance, usar_ia], wrap=True),
        *([] if hay_ia else [ft.Text(t("Sin IA: te muestro los pasajes más relevantes (Ajustes → Inteligencia artificial)."), size=12)]),
        pregunta, ft.ElevatedButton(t("Preguntar"), icon=ft.Icons.SEARCH, on_click=preguntar), estado, barra, zona]
    return cuerpo
