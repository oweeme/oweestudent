import flet as ft

from engine import certificacion_owee as cert
from engine import escritura_owee as motor
from i18n import marcar, t
from owee_curso import curso
from owee_curso.examenes import EXAMENES, ORDEN
from ui.components.owee_texto import glifos
from ui.components.widgets import tarjeta

RUTAS = {"infantil": marcar("Ruta infantil (5 a 12 años)"), "adultos": marcar("Jóvenes y adultos (13 años en adelante)")}


def opciones_puntos(p: float) -> list[float]:
    """Puntuaciones que puedes darte en un ejercicio de `p` puntos: de 0 al máximo, de medio en medio."""
    return sorted({0.0, *(round(p * f * 2) / 2 for f in (0.25, 0.5, 0.75)), float(p)})


def _num(x: float) -> str:
    return f"{x:g}"


def build(st, ir_articulo=lambda: None):
    """Prepárate para la certificación de Owee: ruta de niveles, simulacros por partes y petición del examen oficial.
    El certificado oficial lo da un examinador y solo vale con su código en el registro público del sitio."""
    c = st.conn
    plan_id = curso.plan_del_curso(c, st.perfil_id)
    cuerpo = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
    est = {"examen": None, "parte": 0, "puntos": {}}

    # ---------- inicio: ruta de certificados ----------
    def mostrar_ruta():
        est.update(examen=None, parte=0, puntos={})
        previos = cert.ultimos(c, plan_id) if plan_id else {}
        bloques = []
        for ruta in ("infantil", "adultos"):
            filas = []
            for k in [x for x in ORDEN if EXAMENES[x]["ruta"] == ruta]:
                e = EXAMENES[k]
                prep = cert.preparacion(c, plan_id, k) if plan_id else 0.0
                ult = previos.get(k)
                estado = (t("Último simulacro: {p:.0f} % — {r}", p=ult["pct"], r=t("aprobado ✅") if ult["aprobado"] else t("a repasar")) if ult
                          else t("Aún sin simulacro"))
                filas.append(ft.Container(padding=12, border_radius=10, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), content=ft.Column([
                    ft.Text(e["titulo"], weight=ft.FontWeight.BOLD, size=15),
                    ft.Text(f"{e['edad']} · {t('{m} min', m=e['minutos'])}", size=12, color=ft.Colors.OUTLINE),
                    ft.Text(t("Curso hecho: {p:.0%}", p=prep), size=12), ft.ProgressBar(value=prep), ft.Text(estado, size=12),
                    ft.Row([ft.ElevatedButton(t("Hacer el simulacro"), icon=ft.Icons.FACT_CHECK, on_click=lambda _, k=k: empezar(k)),
                            ft.OutlinedButton(t("Pedir el examen oficial"), icon=ft.Icons.MAIL, on_click=lambda _, k=k: st.page.launch_url(cert.solicitud_mailto(k)))], wrap=True)],
                    spacing=4)))
            bloques += [ft.Text(t(RUTAS[ruta]), theme_style=ft.TextThemeStyle.TITLE_MEDIUM), *filas]
        maestros = tarjeta(t("Maestro y examinador"), ft.Text(t(
            "Para ser maestro necesitas el Nivel 3 (infantil) o el Nivel 4 (adultos), práctica supervisada, un artículo escrito solo en Owee (300, 600 u 800 palabras) "
            "y un video en YouTube. En la pestaña «Escritura» → «Artículo» puedes escribirlo y revisarlo."), size=13),
            ft.Row([ft.ElevatedButton(t("Escribir mi artículo"), icon=ft.Icons.EDIT, on_click=lambda _: ir_articulo()),
                    ft.OutlinedButton(t("Requisitos completos"), on_click=lambda _: st.page.launch_url(cert.ENLACES["certificacion"]))], wrap=True))
        cuerpo.controls = [
            ft.Text(t("Certificación de Owee"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
            ft.Text(t("El certificado es gratuito y lo da un examinador: solo es válido si su código figura en el registro público. "
                      "Aquí practicas con simulacros por partes (se corrige lo que tiene respuesta exacta; en lo demás te puntúas con la clave) y ves si ya estás listo para pedir el examen oficial."), size=13),
            ft.Row([ft.TextButton(t("Registro público"), on_click=lambda _: st.page.launch_url(cert.ENLACES["registro"])),
                    ft.TextButton(t("Exámenes modelo (PDF)"), on_click=lambda _: st.page.launch_url(cert.ENLACES["examenes"]))], wrap=True),
            *bloques, maestros]
        st.page.update()

    # ---------- simulacro ----------
    def empezar(k):
        est.update(examen=k, parte=0, puntos={})
        mostrar_parte()

    def total_parte(pid) -> float:
        return sum(est["puntos"].get(pid, {}).values())

    def tarjeta_item(pid, idx, it):
        estado = ft.Text("", size=14, weight=ft.FontWeight.BOLD)
        clave = ft.Text("", size=13, selectable=True, visible=False)
        analisis = ft.Column(spacing=2)
        fichas = ft.Row(visible=False, wrap=True, spacing=6)
        campo = None if it["voz"] else ft.TextField(label=t("Tu respuesta"), multiline=bool(it["valorar"]), min_lines=6 if it["valorar"] else 1,
                                                    max_lines=14 if it["valorar"] else 3, dense=not it["valorar"])
        puntos = est["puntos"].setdefault(pid, {})

        def puntuar(p):
            puntos[idx] = p
            for b in fichas.controls:
                b.style = ft.ButtonStyle(bgcolor=ft.Colors.PRIMARY_CONTAINER) if float(b.data) == p else None
            st.page.update()
        fichas.controls = [ft.OutlinedButton(_num(p), data=str(p), on_click=lambda _, p=p: puntuar(p)) for p in opciones_puntos(it["puntos"])]

        def comprobar(_):
            if it["auto"]:
                ok = cert.acierta(it, campo.value if campo else "")
                puntos[idx] = float(it["puntos"]) if ok else 0.0
                estado.value, estado.color = (t("✅ Correcto"), ft.Colors.GREEN_400) if ok else (t("❌ La clave: {c}", c=it["clave"]), ft.Colors.RED_300)
            else:
                clave.value = t("Clave: {c}", c=it["clave"]) if it["clave"] else ""
                clave.visible = bool(it["clave"])
                fichas.visible = True
                estado.value = t("¿Cuántos puntos te das? (máximo {p})", p=_num(it["puntos"]))
                if it["valorar"] and campo and (campo.value or "").strip():
                    v = motor.valorar(campo.value)
                    analisis.controls = [ft.Text(t("Tu texto: {n} palabras ({u} distintas) en {o} oraciones.", n=v["palabras"], u=v["distintas"], o=v["oraciones"]), size=12),
                                         ft.Text(t("{p:.0%} de tus palabras están en el léxico de Owee.", p=v["cobertura"]), size=12)]
                    if v["invalidas"]:
                        analisis.controls.append(ft.Text(t("No se pueden escribir en Owee (revisa las sílabas; no existe la «i»): {lista}", lista=", ".join(v["invalidas"])), size=12, color=ft.Colors.RED_300))
                    if v["desconocidas"]:
                        analisis.controls.append(ft.Text(t("No están en el léxico (¿errata o palabra nueva?): {lista}", lista=", ".join(v["desconocidas"])), size=12, color=ft.Colors.AMBER_400))
            st.page.update()

        lineas = []
        for linea in it["owee"]:
            lineas.append(ft.Column([glifos(linea, size=30), ft.Text(linea, size=12, color=ft.Colors.OUTLINE)], spacing=0))
        for linea in it["glifos"]:
            lineas.append(glifos(linea, size=44))
        boton = ft.OutlinedButton(t("Ver la clave") if not it["auto"] else t("Comprobar"), icon=ft.Icons.CHECK, on_click=comprobar)
        return ft.Container(padding=12, border_radius=8, border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT), content=ft.Column([
            ft.Text(f"{it['enunciado']}  ({_num(it['puntos'])})", size=14),
            *([ft.Text(t("Hazlo en voz alta."), size=12, italic=True)] if it["voz"] else []), *lineas,
            *([campo] if campo else []), boton, estado, clave, analisis, fichas], spacing=6))

    def mostrar_parte():
        e = EXAMENES[est["examen"]]
        partes = e["partes"]
        p = partes[est["parte"]]
        ultima = est["parte"] == len(partes) - 1

        def siguiente(_):
            if ultima:
                return resultado()
            est["parte"] += 1
            mostrar_parte()
        nota = [ft.Text(t("En el examen real esta parte la hace en persona el examinador; aquí se adapta."), size=12, italic=True)] if p["examinador"] else []
        cuerpo.controls = [
            ft.Row([ft.IconButton(ft.Icons.ARROW_BACK, tooltip=t("Salir del simulacro"), on_click=lambda _: mostrar_ruta()),
                    ft.Column([ft.Text(e["titulo"], theme_style=ft.TextThemeStyle.TITLE_MEDIUM),
                               ft.Text(t("Parte {id} de {n}: {nombre} ({p} puntos)", id=p["id"], n=len(partes), nombre=t(p["nombre"]), p=_num(p["puntos"])), size=12, color=ft.Colors.OUTLINE)],
                              spacing=0, expand=True)]),
            ft.ProgressBar(value=est["parte"] / len(partes)), *nota,
            *[tarjeta_item(p["id"], i, it) for i, it in enumerate(p["items"])],
            ft.ElevatedButton(t("Terminar el simulacro") if ultima else t("Siguiente parte"), icon=ft.Icons.NAVIGATE_NEXT, on_click=siguiente)]
        st.page.update()

    def resultado():
        k = est["examen"]
        r = cert.evaluar(k, {pid: total_parte(pid) for pid in (x["id"] for x in EXAMENES[k]["partes"])})
        if plan_id:
            cert.guardar(c, plan_id, r)
        filas = [ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.CHECK_CIRCLE if x["logrado"] else ft.Icons.RADIO_BUTTON_UNCHECKED,
                                                         color=ft.Colors.GREEN_400 if x["logrado"] else ft.Colors.AMBER_400),
                             title=ft.Text(f"{x['id']}. {t(x['nombre'])}"), trailing=ft.Text(f"{_num(x['puntos'])} / {_num(x['maximo'])}")) for x in r["partes"]]
        veredicto = (t("🎉 ¡Aprobado en el simulacro! Ya puedes pedir el examen oficial a un examinador.") if r["aprobado"] else
                     t("Aún no llegas. Repasa: {partes}. Puedes repetir el simulacro las veces que quieras.", partes=", ".join(t(x) for x in r["flojas"]) or t("el total")))
        cuerpo.controls = [
            ft.Text(EXAMENES[k]["titulo"], theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
            ft.Text(t("Resultado: {p:.0f} % ({a} de {m} puntos)", p=r["pct"] * 100, a=_num(r["total"]), m=_num(r["maximo"])), size=18, weight=ft.FontWeight.BOLD),
            ft.Text(veredicto, size=14, color=ft.Colors.GREEN_400 if r["aprobado"] else None), *filas,
            ft.Text(t("Para aprobar: 70 % del total y 50 % en cada parte.") if EXAMENES[k]["ruta"] == "adultos"
                    else t("Para lograrlo: el mínimo de puntos de cada parte."), size=12, color=ft.Colors.OUTLINE),
            ft.Row([ft.ElevatedButton(t("Repetir"), icon=ft.Icons.REFRESH, on_click=lambda _: empezar(k)),
                    ft.OutlinedButton(t("Pedir el examen oficial"), icon=ft.Icons.MAIL, on_click=lambda _: st.page.launch_url(cert.solicitud_mailto(k))),
                    ft.TextButton(t("Volver a la ruta"), on_click=lambda _: mostrar_ruta())], wrap=True)]
        st.page.update()

    mostrar_ruta()
    return cuerpo
