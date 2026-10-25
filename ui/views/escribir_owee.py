import flet as ft

from database import repo
from engine import certificacion_owee as cert
from engine import escritura as escritor
from engine import escritura_owee as motor
from i18n import marcar, owee, t
from owee_curso import curso
from ui.components.owee_texto import glifos
from ui.components.teclado_owee import teclado

OBJETIVOS = {"libre": (marcar("Práctica libre"), 200), "maestro_infantil": (marcar("Certificado de maestro infantil (300 palabras)"), 300),
             "maestro_adultos": (marcar("Certificado de maestro de jóvenes y adultos (600 palabras)"), 600),
             "examinador": (marcar("Certificado de examinador (800 palabras)"), 800)}
MODOS_VISTA = {"taller": marcar("Taller libre"), "practica": marcar("Práctica"), "articulo": marcar("Artículo")}


def build(st, recargar=lambda: None):
    """Escribir en Owee Script dentro de la app: un taller libre (teclado de sílabas) y rondas de práctica con las palabras
    del curso. Las palabras que fallas se añaden a «Repaso»."""
    c = st.conn
    est = {"vista": st.escritura_vista or "taller", "ronda": None, "i": 0, "ok": 0, "respondida": False, "art": None, "sec": None}
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    escrito: list[str] = []                      # lo compuesto con el teclado, en romano

    def romano() -> str:
        return "".join(escrito)

    def selector():
        def cambiar(e):
            est["vista"] = next(iter(e.control.selected))
            mostrar()
        return ft.SegmentedButton(selected={est["vista"]}, on_change=cambiar, allow_multiple_selection=False,
                                  segments=[ft.Segment(value=k, label=ft.Text(t(v))) for k, v in MODOS_VISTA.items()])

    # ---------- piezas comunes: visor + teclas de control ----------
    visor = glifos("", size=44, selectable=True)
    visor_romano = ft.Text("", size=14, color=ft.Colors.OUTLINE)
    campo = ft.TextField(label=t("O escribe en romano"), dense=True, width=300)

    def refrescar():
        visor.value = owee.a_escritura(romano())
        visor_romano.value = romano()
        if campo.value != romano():
            campo.value = romano()
        st.page.update()

    def poner(texto):
        escrito.append(texto)
        refrescar()

    def desde_campo(e):
        escrito[:] = [campo.value or ""]
        visor.value = owee.a_escritura(campo.value or "")
        visor_romano.value = campo.value or ""
        st.page.update()
    campo.on_change = desde_campo

    def borrar(_):
        if escrito:
            texto = romano()[:-1] if len(escrito) == 1 else None
            if texto is not None:
                escrito[:] = [texto] if texto else []
            else:
                escrito.pop()
        refrescar()

    def limpiar(_):
        escrito.clear()
        refrescar()

    controles = ft.Row([ft.OutlinedButton(t("⌫ Borrar"), on_click=borrar), ft.OutlinedButton(t("Espacio"), on_click=lambda _: poner(" ")),
                        ft.OutlinedButton(t("Nexo (-)"), on_click=lambda _: poner("-")), ft.OutlinedButton(t("Limpiar"), on_click=limpiar)], wrap=True)

    def zona_escritura():
        return ft.Container(ft.Column([ft.Row([visor], scroll=ft.ScrollMode.AUTO), visor_romano], spacing=2), padding=12, border_radius=8,
                            border=ft.border.all(1, ft.Colors.OUTLINE), height=110)

    # ---------- taller libre ----------
    def mostrar_taller():
        escrito.clear()
        refrescar_vacio()

        def copiar(_):
            st.page.set_clipboard(visor.value or "")
            st.toast(t("Copiado en escritura Owee"))
        cuerpo.controls = [
            selector(),
            ft.Text(t("Escribe con el teclado de sílabas (o en romano) y mira tu texto en escritura Owee. Una palabra con mayúscula inicial es un nombre propio."), size=13),
            zona_escritura(), campo, controles,
            ft.OutlinedButton(t("Copiar en escritura Owee"), icon=ft.Icons.COPY, on_click=copiar),
            teclado(poner)]
        st.page.update()

    def refrescar_vacio():
        visor.value, visor_romano.value, campo.value = "", "", ""

    # ---------- práctica ----------
    def mostrar_practica():
        plan_id = curso.plan_del_curso(c, st.perfil_id)
        sig = curso.siguiente_leccion(c, plan_id) if plan_id else None      # palabras hasta la lección que te toca
        pool = motor.palabras(sig["id"] if sig else None) or motor.palabras()
        if not pool:
            cuerpo.controls = [selector(), ft.Text(t("Aún no hay palabras: avanza en el curso."))]
            st.page.update()
            return
        if est["ronda"] is None:
            est.update(ronda=motor.ronda(pool, 5), i=0, ok=0, respondida=False)
        pregunta()

    def nueva_ronda(_=None):
        est["ronda"] = None
        mostrar_practica()

    def pregunta():
        r, i = est["ronda"], est["i"]
        if i >= len(r):
            return resultado()
        q = r[i]
        escrito.clear()
        refrescar_vacio()
        est["respondida"] = False
        veredicto = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
        siguiente = ft.ElevatedButton(t("Siguiente"), visible=False)
        comprobar = ft.ElevatedButton(t("Comprobar"), icon=ft.Icons.CHECK)
        if q["modo"] == "es_a_owee":
            enunciado = ft.Text(t("Escribe en Owee: «{sig}»", sig=q["significado"]), size=18, weight=ft.FontWeight.W_500)
        elif q["modo"] == "glifo_a_owee":
            enunciado = ft.Column([ft.Text(t("Copia esta palabra con el teclado"), size=14), glifos(q["palabra"], size=56)], spacing=2)
        else:
            enunciado = ft.Column([ft.Text(t("Lee y escribe en romano"), size=14), glifos(q["palabra"], size=56)], spacing=2)
        solo_romano = q["modo"] == "glifo_a_romano"

        def comprobar_click(_):
            if est["respondida"]:
                return
            est["respondida"] = True
            ok = motor.comprobar(romano() or campo.value or "", q["palabra"])
            if ok:
                est["ok"] += 1
                veredicto.value, veredicto.color = t("✅ Correcto"), ft.Colors.GREEN_400
            else:
                veredicto.value, veredicto.color = t("❌ Era: {palabra}", palabra=q["palabra"]), ft.Colors.RED_300
                plan_id = curso.plan_del_curso(c, st.perfil_id)
                tema = repo.tema_para_tarjetas(c, plan_id) if plan_id else None
                if tema:       # lo que fallas vuelve en «Repaso»
                    repo.crear_tarjetas(c, tema, [(curso.MARCA_OWEE + q["palabra"], q["significado"])], "owee")
                    repo.crear_tarjetas(c, tema, [(q["significado"], curso.MARCA_OWEE + q["palabra"])], "produccion")
                    est["fallos"] = est.get("fallos", 0) + 1
            comprobar.visible, siguiente.visible = False, True
            st.page.update()

        def avanzar(_):
            est["i"] += 1
            pregunta()
        comprobar.on_click, siguiente.on_click = comprobar_click, avanzar
        cuerpo.controls = [selector(), ft.ProgressBar(value=i / len(r)), ft.Text(t("Palabra {i} de {n}", i=i + 1, n=len(r)), size=12, color=ft.Colors.OUTLINE),
                           enunciado, *([] if solo_romano else [zona_escritura()]), campo, *([] if solo_romano else [controles]),
                           ft.Row([comprobar, siguiente]), veredicto, *([] if solo_romano else [teclado(poner, incluir_digitos=False)])]
        st.page.update()

    def resultado():
        r = est["ronda"]
        extra = [ft.Text(t("Los fallos se añadieron a «Repaso» para que vuelvan."), size=13)] if est.get("fallos") else []
        est["fallos"] = 0
        cuerpo.controls = [selector(), ft.Text(t("Resultado: {ok} de {n}", ok=est["ok"], n=len(r)), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                           *extra, ft.ElevatedButton(t("Nueva ronda"), icon=ft.Icons.REFRESH, on_click=nueva_ronda)]
        st.page.update()

    # ---------- artículo: un texto largo en Owee, por secciones, para valorar lo aprendido ----------
    def mostrar_articulos():
        est["art"] = None
        plan_id = curso.plan_del_curso(c, st.perfil_id)
        lista = escritor.escritos(c, plan_id) if plan_id else []
        titulo = ft.TextField(label=t("Título del artículo"), width=320, dense=True)
        objetivo = ft.Dropdown(label=t("Objetivo"), width=360, dense=True, value="libre",
                               options=[ft.dropdown.Option(k, t(v[0])) for k, v in OBJETIVOS.items()])

        def crear(_):
            if plan_id and (titulo.value or "").strip():
                est["art"], est["sec"] = escritor.crear_escrito(c, plan_id, titulo.value, "ensayo", meta_palabras=OBJETIVOS[objetivo.value or "libre"][1]), None
                mostrar_editor()
        filas = [ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.ARTICLE), title=ft.Text(e["titulo"]),
                             subtitle=ft.Text(t("{n} palabras", n=escritor.progreso(c, e["id"])["palabras"]), size=11),
                             on_click=lambda _, i=e["id"]: abrir(i)) for e in lista]
        cuerpo.controls = [selector(),
                           ft.Text(t("Escribe un texto más largo en Owee, por secciones, y valora lo que has aprendido: la app revisa tus palabras y tu vocabulario."), size=13),
                           *(filas or [ft.Text(t("Aún no tienes artículos. Crea el primero."))]),
                           ft.Row([titulo, objetivo, ft.ElevatedButton(t("＋ Nuevo artículo"), icon=ft.Icons.ADD, on_click=crear)], wrap=True)]
        st.page.update()

    def abrir(art_id):
        est["art"], est["sec"] = art_id, None
        mostrar_editor()

    def mostrar_editor():
        art = escritor.escrito(c, est["art"])
        secs = escritor.secciones(c, est["art"])
        if est["sec"] not in [x["id"] for x in secs]:
            est["sec"] = secs[0]["id"]
        sec = escritor.seccion(c, est["sec"])
        total = escritor.progreso(c, est["art"])
        vista_glifos = glifos("", size=28, selectable=True)
        contador = ft.Text("", size=12, color=ft.Colors.OUTLINE)
        valoracion = ft.Column(spacing=4)
        campo_texto = ft.TextField(label=t("Escribe aquí en romano (abajo se dibuja en escritura Owee)"), value=sec["texto"] or "",
                                   multiline=True, min_lines=6, max_lines=16)

        def refrescar_texto():
            vista_glifos.value = owee.a_escritura(campo_texto.value or "")
            contador.value = t("{n} palabras", n=escritor.contar_palabras(campo_texto.value or "")) + " · " + t("Guardado")

        def al_cambiar(_):
            escritor.editar_seccion(c, sec["id"], texto=campo_texto.value or "")
            refrescar_texto()
            st.page.update()
        campo_texto.on_change = al_cambiar

        def insertar(texto):
            campo_texto.value = (campo_texto.value or "") + texto
            al_cambiar(None)

        def valorar(_):
            todo = "\n".join((escritor.seccion(c, x["id"])["texto"] or "") for x in secs)
            v = motor.valorar(todo)
            lineas = []
            if not v["palabras"]:
                lineas.append(ft.Text(t("Escribe algo primero para valorarlo.")))
            else:
                lineas += [ft.Text(t("Tu texto: {n} palabras ({u} distintas) en {o} oraciones.", n=v["palabras"], u=v["distintas"], o=v["oraciones"]), weight=ft.FontWeight.BOLD),
                           ft.Text(t("{p:.0%} de tus palabras están en el léxico de Owee.", p=v["cobertura"])),
                           ft.Text(t("Variedad de palabras: {v:.0%} (cuanto más alta, menos repites).", v=v["variedad"]))]
                if v["nivel"] is not None:
                    lineas.append(ft.Text(t("Usas vocabulario hasta el nivel {n} del curso.", n=v["nivel"])))
                if v["nombres"]:
                    lineas.append(ft.Text(t("Nombres propios: {n}", n=v["nombres"])))
                if v["invalidas"]:
                    lineas.append(ft.Text(t("No se pueden escribir en Owee (revisa las sílabas; no existe la «i»): {lista}", lista=", ".join(v["invalidas"])), color=ft.Colors.RED_300))
                if v["desconocidas"]:
                    lineas.append(ft.Text(t("No están en el léxico (¿errata o palabra nueva?): {lista}", lista=", ".join(v["desconocidas"])), color=ft.Colors.AMBER_400))
                if not v["invalidas"] and not v["desconocidas"]:
                    lineas.append(ft.Text(t("✅ Sin errores de escritura. Prueba oraciones más largas o más variedad de palabras."), color=ft.Colors.GREEN_400))
            if art["meta_palabras"] in (300, 600, 800) and v["palabras"]:          # artículo para el certificado de maestro o examinador
                r = cert.revisar_articulo(todo, art["meta_palabras"])
                marca = lambda ok: "✅" if ok else "⬜"      # noqa: E731
                lineas += [ft.Divider(),
                           ft.Text(t("Revisión para el certificado"), weight=ft.FontWeight.BOLD),
                           ft.Text(f"{marca(r['extension_ok'])} " + t("Extensión: {n} de {m} palabras", n=v["palabras"], m=r["minimo"])),
                           ft.Text(f"{marca(r['sin_errores'])} " + t("Solo palabras válidas en Owee")),
                           ft.Text(f"{marca(len(r['compuestos']) >= 3)} " + t("Compuestos: {n} (usa varios)", n=len(r["compuestos"]))),
                           ft.Text(f"{marca(r['pasado'] and r['futuro'])} " + t("Tiempos: pasado `pe` y futuro `pu`")),
                           ft.Text(f"{marca(len(r['enlaces']) >= 2)} " + t("Palabras de enlace: {lista}", lista=", ".join(r["enlaces"]) or "—")),
                           ft.Text(t("Cuando esté listo, publícalo en tu blog de oweeme.com con tu video de YouTube y pide tu examen. El examinador revisa la corrección, la claridad, la variedad y la reflexión."), size=12, italic=True)]
            valoracion.controls = lineas
            st.page.update()

        def copiar(_):
            todo = "\n\n".join(owee.a_escritura(escritor.seccion(c, x["id"])["texto"] or "") for x in secs)
            st.page.set_clipboard(todo)
            st.toast(t("Copiado en escritura Owee"))

        chips = ft.Row([(ft.FilledButton if x["id"] == est["sec"] else ft.OutlinedButton)(
            f"{x['titulo']} ({escritor.contar_palabras(x['texto'] or '')})", on_click=lambda _, i=x["id"]: (est.update(sec=i), mostrar_editor()))
            for x in secs], wrap=True, spacing=6)
        refrescar_texto()
        cuerpo.controls = [
            selector(),
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Mis artículos"), on_click=lambda _: mostrar_articulos()),
                    ft.Column([ft.Text(art["titulo"], theme_style=ft.TextThemeStyle.TITLE_LARGE),
                               ft.Text(t("{n} de {m} palabras", n=total["palabras"], m=art["meta_palabras"]), size=12, color=ft.Colors.OUTLINE)], spacing=0, expand=True)]),
            chips, ft.Text(sec["notas"] or "", size=12, italic=True), campo_texto, contador,
            ft.Container(ft.Row([vista_glifos], scroll=ft.ScrollMode.AUTO), padding=12, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT)),
            ft.ExpansionTile(title=ft.Text(t("Teclado de sílabas")), controls=[ft.Container(teclado(insertar, incluir_digitos=True), padding=8)]),
            ft.Row([ft.ElevatedButton(t("Valorar mi texto"), icon=ft.Icons.FACT_CHECK, on_click=valorar),
                    ft.OutlinedButton(t("Copiar en escritura Owee"), icon=ft.Icons.COPY, on_click=copiar)], wrap=True),
            valoracion]
        st.page.update()

    def mostrar():
        {"taller": mostrar_taller, "practica": mostrar_practica, "articulo": mostrar_articulos}[est["vista"]]()

    st.escritura_vista = None
    mostrar()
    return cuerpo
