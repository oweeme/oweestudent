import threading
import flet as ft

from database import repo
from database.db import DB_PATH
from engine import ai
from engine import busqueda as bq
from engine import escritura as es
from i18n import t, tn
from ui.components import guardar
from ui.components.widgets import ancho_dialogo, confirmar, dialogo
from ui.views.preguntar import ruta_indice

FORMATOS = (("md", "Markdown (.md)"), ("html", "HTML (.html)"), ("docx", "Word (.docx)"))


def _entero(texto, defecto):
    try:
        return max(0, int(str(texto).strip()))
    except ValueError:
        return defecto


def _nombre_archivo(texto: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in texto).strip("-")[:50] or "escrito"


def build(st, ir_a_lecturas=lambda: None, indice=None):
    c = st.conn
    if not st.plan_id:
        return ft.Text(t("Primero crea o elige una asignatura en «Planes»."))
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    aviso = ft.Text("", selectable=True)
    est = {"escrito": None, "formato": "md", "doc": None}
    idx = indice or (bq.Indice(ruta_indice()) if DB_PATH != ":memory:" else None)

    def msg(texto, error=False):
        aviso.value, aviso.color = texto, ft.Colors.RED_300 if error else ft.Colors.GREEN_300
        st.page.update()

    # ---------- exportar ----------
    def escribir(destino):
        doc = es.compilar(c, est["escrito"])
        if est["formato"] == "docx":
            es.a_docx(doc, destino)
        else:
            destino.write_text(es.a_markdown(doc) if est["formato"] == "md" else es.a_html(doc), encoding="utf-8")

    def terminado(destino, error):
        msg(t("No se pudo exportar: {ex}", ex=error) if error else t("✅ Exportado en: {ruta}", ruta=str(destino)), bool(error))

    picker = guardar.preparar(st.page, lambda ruta: guardar.escribir_elegido(ruta, est["formato"], escribir, terminado))

    def exportar(formato):
        if formato == "docx" and not es.docx_disponible():
            return msg(t("Word no está disponible en este dispositivo. Usa Markdown o HTML."), True)
        est["formato"] = formato
        e = es.escrito(c, est["escrito"])
        guardar.guardar(st.page, picker, _nombre_archivo(e["titulo"]), formato, escribir, terminado)

    # ---------- lista de escritos ----------
    def nuevo(_):
        titulo = ft.TextField(label=t("Título"), autofocus=True)
        meta = ft.TextField(label=t("Meta de palabras"), value=str(es.METAS_POR_TIPO["monografia"]), width=170)
        tipo = ft.Dropdown(label=t("Tipo de escrito"), value="monografia", width=240,
                           options=[ft.dropdown.Option(k, t(v)) for k, v in es.NOMBRES_TIPO.items()],
                           on_change=lambda e: (setattr(meta, "value", str(es.METAS_POR_TIPO[e.control.value])), st.page.update()))
        capitulos = ft.TextField(label=t("Capítulos (para libros)"), value="8", width=170)
        limite = ft.TextField(label=t("Fecha límite (AAAA-MM-DD, opcional)"), width=260)
        autor = ft.TextField(label=t("Autor"), value=next((p["nombre"] for p in repo.perfiles(c) if p["id"] == st.perfil_id), ""))
        estilo = ft.Dropdown(label=t("Estilo de citas"), value="apa", options=[ft.dropdown.Option(k, t(v)) for k, v in es.NOMBRES_ESTILO.items()])

        def ok(v):
            if not v[0].strip():
                return
            try:
                eid = es.crear_escrito(c, st.plan_id, v[0], v[1], _entero(v[2], None) or None, v[4].strip() or None, v[5], v[6],
                                       max(1, _entero(v[3], 8)))
            except ValueError:
                return msg(t("La fecha límite debe tener el formato AAAA-MM-DD."), True)
            mostrar_escrito(eid)
        dialogo(st.page, t("Nuevo escrito"), [titulo, tipo, meta, capitulos, limite, autor, estilo], ok, t("Crear"))

    def mostrar_lista():
        est["escrito"] = None
        filas = []
        for e in es.escritos(c, st.plan_id):
            p = es.progreso(c, e["id"])
            filas.append(ft.ListTile(
                leading=ft.Icon(ft.Icons.EDIT_DOCUMENT), title=ft.Text(e["titulo"], weight=ft.FontWeight.W_500),
                subtitle=ft.Column([ft.Text(f"{t(es.NOMBRES_TIPO[e['tipo']])} · " + t("{a} de {b} palabras", a=p["palabras"], b=p["meta"]), size=12),
                                    ft.ProgressBar(value=p["porcentaje"] / 100)], spacing=4),
                on_click=lambda _, i=e["id"]: mostrar_escrito(i)))
        cuerpo.controls = [
            ft.Text(t("Escritor"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL), aviso,
            ft.Text(t("Arma una monografía, un ensayo, una tesis o un libro por secciones, con meta de palabras, citas de tus lecturas "
                      "y lista de referencias automática. Se exporta a Word, HTML o Markdown."), size=13),
            ft.Row([ft.ElevatedButton(t("＋ Nuevo escrito"), on_click=nuevo)]),
            *(filas or [ft.Text(t("Aún no has empezado ningún escrito."))])]
        st.page.update()

    # ---------- un escrito ----------
    def cambiar_estilo(e):
        es.editar_escrito(c, est["escrito"], estilo=e.control.value)
        mostrar_escrito(est["escrito"])

    def editar_datos(_):
        e = es.escrito(c, est["escrito"])
        titulo = ft.TextField(label=t("Título"), value=e["titulo"])
        autor = ft.TextField(label=t("Autor"), value=e["autor"] or "")
        meta = ft.TextField(label=t("Meta de palabras"), value=str(e["meta_palabras"] or 0))
        limite = ft.TextField(label=t("Fecha límite (AAAA-MM-DD, opcional)"), value=e["fecha_limite"] or "")

        def ok(v):
            try:
                es.editar_escrito(c, e["id"], titulo=v[0].strip() or e["titulo"], autor=v[1].strip(), meta_palabras=_entero(v[2], e["meta_palabras"]),
                                  fecha_limite=v[3].strip() or None)
            except ValueError:
                return msg(t("La fecha límite debe tener el formato AAAA-MM-DD."), True)
            mostrar_escrito(e["id"])
        dialogo(st.page, t("Datos del escrito"), [titulo, autor, meta, limite], ok)

    def vista_previa(_):
        doc = es.compilar(c, est["escrito"])
        dlg = ft.AlertDialog(title=ft.Text(t("Vista previa")), content=ft.Column(
            [ft.Markdown(es.a_markdown(doc), selectable=True, extension_set=ft.MarkdownExtensionSet.GITHUB_WEB)], scroll=ft.ScrollMode.AUTO,
            width=ancho_dialogo(st.page, 560), height=460), actions=[ft.TextButton(t("Cerrar"), on_click=lambda _: st.page.close(dlg))])
        st.page.open(dlg)

    def copiar(_):
        st.page.set_clipboard(es.a_markdown(es.compilar(c, est["escrito"])))
        msg(t("Texto copiado (Markdown)."))

    def borrar_este(_):
        e = es.escrito(c, est["escrito"])
        confirmar(st.page, t("¿Borrar «{titulo}» con todas sus secciones?", titulo=e["titulo"]), lambda: (es.borrar_escrito(c, e["id"]), mostrar_lista()))

    def nueva_seccion(_):
        campo = ft.TextField(label=t("Título de la sección"), autofocus=True)
        dialogo(st.page, t("Nueva sección"), [campo], lambda v: v[0].strip() and (mostrar_seccion(es.agregar_seccion(c, est["escrito"], v[0])), None), t("Crear"))

    def mostrar_escrito(eid):
        est["escrito"] = eid
        e = es.escrito(c, eid)
        p = es.progreso(c, eid)
        doc = es.compilar(c, eid)
        ritmo = []
        if p["dias"] is not None:
            ritmo.append(t("{n} días para la fecha límite", n=p["dias"]) if p["dias"] >= 0 else t("La fecha límite ya pasó."))
            if p["palabras_por_dia"]:
                ritmo.append(t("≈ {n:.0f} palabras por día", n=p["palabras_por_dia"]))
        filas = [ft.ListTile(
            dense=True, title=ft.Text(s["titulo"], size=14),
            subtitle=ft.Column([ft.Text(t("{a} de {b} palabras", a=s["palabras"], b=s["meta"]) if s["meta"] else tn(s["palabras"], "{n} palabra", "{n} palabras"), size=11),
                                ft.ProgressBar(value=min(1, s["palabras"] / s["meta"]) if s["meta"] else 0)], spacing=2),
            on_click=lambda _, i=s["id"]: mostrar_seccion(i)) for s in p["secciones"]]
        formato = ft.Dropdown(label=t("Exportar como"), width=200, value="md", options=[ft.dropdown.Option(k, n) for k, n in FORMATOS
                                                                                       if k != "docx" or es.docx_disponible()])
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Volver a mis escritos"), on_click=lambda _: mostrar_lista()),
                    ft.Text(e["titulo"], theme_style=ft.TextThemeStyle.TITLE_LARGE, expand=True),
                    ft.IconButton(ft.Icons.EDIT, tooltip=t("Datos del escrito"), on_click=editar_datos)]), aviso,
            ft.Text(f"{t(es.NOMBRES_TIPO[e['tipo']])} · " + t("{a} de {b} palabras ({p}%)", a=p["palabras"], b=p["meta"], p=p["porcentaje"]), weight=ft.FontWeight.BOLD),
            ft.ProgressBar(value=p["porcentaje"] / 100), *([ft.Text(" · ".join(ritmo), size=12)] if ritmo else []),
            *([ft.Text(t("Citas sin lectura registrada: {lista}. Añádelas en «Lecturas» o corrige la clave.", lista=", ".join(doc["sin_fuente"])),
                       color=ft.Colors.AMBER_400, size=12)] if doc["sin_fuente"] else []),
            ft.Row([ft.Dropdown(label=t("Estilo de citas"), width=240, value=e["estilo"], on_change=cambiar_estilo,
                                options=[ft.dropdown.Option(k, t(v)) for k, v in es.NOMBRES_ESTILO.items()]),
                    ft.OutlinedButton(t("Vista previa"), icon=ft.Icons.VISIBILITY, on_click=vista_previa),
                    ft.OutlinedButton(t("Copiar texto"), icon=ft.Icons.COPY, on_click=copiar)], wrap=True),
            ft.Row([formato, ft.ElevatedButton(t("Exportar"), icon=ft.Icons.DOWNLOAD, on_click=lambda _: exportar(formato.value))], wrap=True),
            ft.Text(t("Secciones"), weight=ft.FontWeight.BOLD), *filas,
            ft.Row([ft.TextButton(t("＋ Nueva sección"), on_click=nueva_seccion),
                    ft.TextButton(t("Borrar escrito"), icon=ft.Icons.DELETE_OUTLINE, on_click=borrar_este)], wrap=True)]
        st.page.update()

    # ---------- una sección ----------
    def mostrar_seccion(sid):
        s = es.seccion(c, sid)
        e = es.escrito(c, s["escrito_id"])
        claves = es.claves_del_plan(c, st.plan_id)
        titulo = ft.TextField(label=t("Título de la sección"), value=s["titulo"])
        meta = ft.TextField(label=t("Meta de palabras"), value=str(s["meta_palabras"] or 0), width=170)
        contador = ft.Text("", size=12)
        texto = ft.TextField(label=t("Escribe aquí. Para citar una lectura usa [@clave]."), value=s["texto"] or "", multiline=True,
                             min_lines=14, max_lines=40)
        salida = ft.Column(spacing=6)

        def contar(_=None):
            n, m = es.contar_palabras(texto.value), _entero(meta.value, 0)
            contador.value = t("{a} de {b} palabras", a=n, b=m) if m else tn(n, "{n} palabra", "{n} palabras")
            st.page.update()

        def guardar_todo(_=None, volver=False):
            es.editar_seccion(c, sid, titulo=titulo.value.strip() or s["titulo"], texto=texto.value, meta_palabras=_entero(meta.value, 0))
            if volver:
                mostrar_escrito(e["id"])
            else:
                msg(t("Sección guardada"))

        texto.on_change = contar
        meta.on_change = contar
        texto.on_blur = lambda _: es.editar_seccion(c, sid, texto=texto.value)       # no se pierde lo escrito al cambiar de campo

        # citar
        opciones = [ft.dropdown.Option(k, f"{es.cita_corta(r)} — {r['titulo'][:40]}") for k, r in claves.items()]
        elegida = ft.Dropdown(label=t("Lectura a citar"), width=320, options=opciones, value=opciones[0].key if opciones else None)
        pagina = ft.TextField(label=t("Página"), width=100)

        def insertar_cita(_):
            if not elegida.value:
                return msg(t("Aún no hay lecturas que citar: añádelas en «Lecturas»."), True)
            marca = f"[@{elegida.value}" + (f", p. {pagina.value.strip()}" if pagina.value.strip() else "") + "]"
            texto.value = (texto.value.rstrip() + " " + marca).strip()
            contar()

        def con_clave(clave):
            def poner(_):
                texto.value = (texto.value.rstrip() + f" [@{clave}]").strip()
                contar()
            return poner

        def fuentes(_):
            if idx is None:
                return
            salida.controls = [ft.Text(t("Buscando en tus documentos…"), size=12)]
            st.page.update()

            def hacer():
                try:
                    for m in bq.materiales_pendientes(c, idx, [st.plan_id]):
                        try:
                            idx.indexar_material(m["hash"], m["ruta"])
                        except Exception:
                            pass
                    r = es.fuentes_para(c, idx, st.plan_id, f"{e['titulo']} {titulo.value} {texto.value[-300:]}")     # el tema del escrito + la sección + lo último que escribiste
                    if not r:
                        salida.controls = [ft.Text(t("No encontré pasajes relacionados en tus documentos."), size=12)]
                    else:
                        salida.controls = [ft.Text(t("Fuentes relacionadas"), weight=ft.FontWeight.BOLD, size=13)] + [ft.Container(ft.Column([
                            ft.Text(x["fuente"].etiqueta(), size=12, weight=ft.FontWeight.W_500),
                            ft.Text(bq.recorte(x["fuente"].texto, titulo.value), size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.TextButton(t("Citar"), icon=ft.Icons.FORMAT_QUOTE, on_click=con_clave(x["clave"])) if x["clave"] else
                            ft.Text(t("Para citarla, regístrala en «Lecturas» (con su autor y año)."), size=11, color=ft.Colors.AMBER_400)], spacing=2),
                            padding=8, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)) for x in r]
                except Exception as ex:
                    salida.controls = [ft.Text(t("Error: {ex}", ex=ex), color=ft.Colors.RED_300)]
                st.page.update()
            threading.Thread(target=hacer, daemon=True).start()

        def borrador(_):
            if idx is None or not ai.ia_disponible():
                return msg(t("Configura la IA en Ajustes para usar esta función."), True)
            puntos = ft.TextField(label=t("¿Qué ideas quieres desarrollar? (opcional)"), multiline=True, min_lines=2, max_lines=5)

            def generar(v):
                salida.controls = [ft.Text(t("La IA está redactando un borrador con tus fuentes…"), size=12)]
                st.page.update()

                def hacer():
                    try:
                        for m in bq.materiales_pendientes(c, idx, [st.plan_id]):
                            try:
                                idx.indexar_material(m["hash"], m["ruta"])
                            except Exception:
                                pass
                        r = es.borrador_ia(c, idx, st.plan_id, f"{e['titulo']} · {titulo.value}", v[0])
                    except Exception as ex:
                        salida.controls = [ft.Text(t("Error IA: {ex}", ex=ex), color=ft.Colors.RED_300)]
                        return st.page.update()
                    if r["sin_fuentes"] or r["no_alcanza"]:
                        salida.controls = [ft.Text(t("No hay fuentes suficientes para redactar esto. Añade material o lecturas con ficha."), color=ft.Colors.AMBER_400)]
                    else:
                        def insertar(_):
                            texto.value = (texto.value.rstrip() + "\n\n" + r["texto"]).strip()
                            salida.controls = []
                            contar()
                        salida.controls = [ft.Container(ft.Column([
                            ft.Text(t("BORRADOR de la IA: revísalo y reescríbelo con tus palabras."), weight=ft.FontWeight.BOLD, size=12, color=ft.Colors.AMBER_400),
                            ft.Text(r["texto"], selectable=True, size=13),
                            *([ft.Text(t("No se citaron estas fuentes porque no están en «Lecturas»: {lista}", lista=", ".join(r["sin_registrar"])), size=11)] if r["sin_registrar"] else []),
                            ft.Row([ft.ElevatedButton(t("Insertar al final"), icon=ft.Icons.ADD, on_click=insertar),
                                    ft.TextButton(t("Descartar"), on_click=lambda _: (setattr(salida, "controls", []), st.page.update()))])], spacing=6),
                            padding=10, border_radius=8, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST)]
                    st.page.update()
                threading.Thread(target=hacer, daemon=True).start()
            dialogo(st.page, t("Borrador con IA"), [puntos], generar, t("Redactar"))

        def revisar(_):
            avisos = es.revisar_seccion(texto.value, _entero(meta.value, 0), set(claves))
            salida.controls = [ft.Text(t("Revisión de la redacción"), weight=ft.FontWeight.BOLD, size=13), *[ft.Text("• " + a, size=13) for a in avisos]]
            st.page.update()

        def mover(delta):
            guardar_todo()
            es.mover_seccion(c, sid, delta)
            mostrar_escrito(e["id"])

        def borrar(_):
            confirmar(st.page, t("¿Borrar la sección «{titulo}»?", titulo=s["titulo"]), lambda: (es.borrar_seccion(c, sid), mostrar_escrito(e["id"])))

        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Volver al escrito"), on_click=lambda _: guardar_todo(volver=True)),
                    ft.Text(e["titulo"], theme_style=ft.TextThemeStyle.TITLE_MEDIUM, expand=True)]), aviso,
            ft.Row([titulo, meta], wrap=True), contador,
            *([ft.ExpansionTile(title=ft.Text(t("Guía de esta sección")), controls=[
                ft.Container(ft.Text(s["notas"], size=13), padding=ft.padding.only(left=16, right=16, bottom=12))])] if s["notas"] else []),
            texto,
            ft.Row([elegida, pagina, ft.OutlinedButton(t("Insertar cita"), icon=ft.Icons.FORMAT_QUOTE, on_click=insertar_cita)], wrap=True),
            ft.Row([ft.ElevatedButton(t("Guardar"), icon=ft.Icons.SAVE, on_click=guardar_todo),
                    ft.OutlinedButton(t("Fuentes para esta sección"), icon=ft.Icons.TRAVEL_EXPLORE, on_click=fuentes),
                    ft.OutlinedButton(t("✨ Borrador con IA"), on_click=borrador),
                    ft.OutlinedButton(t("Revisar redacción"), icon=ft.Icons.FACT_CHECK, on_click=revisar)], wrap=True),
            salida,
            ft.Row([ft.TextButton(t("Subir"), icon=ft.Icons.ARROW_UPWARD, on_click=lambda _: mover(-1)),
                    ft.TextButton(t("Bajar"), icon=ft.Icons.ARROW_DOWNWARD, on_click=lambda _: mover(1)),
                    ft.TextButton(t("Borrar sección"), icon=ft.Icons.DELETE_OUTLINE, on_click=borrar)], wrap=True)]
        contar()

    mostrar_lista()
    return cuerpo

