from datetime import date

import flet as ft

from database import repo
from engine import nivel as niveles
from engine import plantillas as pl
from i18n import marcar, t
from ui.components.widgets import ancho_dialogo, tarjeta

ETIQUETA_OBJETIVO = {
    "asignatura": marcar("¿Qué asignatura o examen preparas?"), "idioma": marcar("¿Qué idioma quieres aprender?"),
    "tecnologia": marcar("¿Qué quieres dominar? (ej. Python, redes, diseño)"),
    "posgrado": marcar("¿Cuál es tu tema o pregunta de investigación?")}
ETAPAS = {"inicio": marcar("Estoy empezando"), "revision": marcar("Ya tengo la pregunta y leo la literatura"),
          "escritura": marcar("Ya tengo datos y estoy escribiendo")}
NIVELES_TEC = {"principiante": marcar("principiante"), "intermedio": marcar("intermedio"), "avanzado": marcar("avanzado")}


def _numero(texto, por_defecto, entero=False):
    try:
        v = float(str(texto).replace(",", "."))
    except ValueError:
        return por_defecto
    return int(v) if entero else v


def build(st, ir_a_plan, ir_a_owee=lambda: None):
    c = st.conn
    est = {"tipo": None}
    aviso = ft.Text("", color=ft.Colors.RED_300)
    zona_campos = ft.Column(spacing=10)
    zona_previa = ft.Column(spacing=10)

    objetivo = ft.TextField(label=t("Objetivo"))
    horas = ft.TextField(label=t("Horas/semana"), value=str(niveles.ajustes(st.nivel())["horas_semana"]), width=130)
    meses = ft.TextField(label=t("Meses"), value="6", width=100)
    limite = ft.TextField(label=t("Fecha límite (AAAA-MM-DD, opcional)"), width=260)
    inicio = ft.TextField(label=t("Fecha de inicio (AAAA-MM-DD)"), value=date.today().isoformat(), width=250)
    carpeta = ft.Dropdown(label=t("Guardar en la carpeta"), width=320, value="ninguna",
                          options=[ft.dropdown.Option("ninguna", t("(Sin carpeta)"))] + [
                              ft.dropdown.Option(str(k["id"]), k["nombre"]) for k in repo.carpetas(c, st.perfil_id)])
    temario = ft.TextField(label=t("Temario (un tema por línea; pega el índice de tu programa)"), multiline=True,
                           min_lines=6, max_lines=14)
    nivel_actual = ft.Dropdown(label=t("Tu nivel actual"), width=200, value="A0",
                               options=[ft.dropdown.Option(n, t("A0 (desde cero)") if n == "A0" else n) for n in pl.NIVELES_MCER[:-1]])
    nivel_meta = ft.Dropdown(label=t("Nivel que quieres alcanzar"), width=240, value="B1",
                             options=[ft.dropdown.Option(n) for n in pl.NIVELES_MCER[1:]])
    nota_idioma = ft.Column(visible=False)
    nivel_tec = ft.Dropdown(label=t("Tu nivel actual"), width=200, value="principiante",
                            options=[ft.dropdown.Option(k, t(v)) for k, v in NIVELES_TEC.items()])
    proyecto = ft.TextField(label=t("¿Qué quieres construir con ello? (tu proyecto)"))
    etapa = ft.Dropdown(label=t("¿En qué etapa estás?"), width=320, value="inicio",
                        options=[ft.dropdown.Option(k, t(v)) for k, v in ETAPAS.items()])
    lecturas = ft.TextField(label=t("Lecturas por semana"), value="3", width=160)

    def es_owee(_=None):
        if est["tipo"] == "idioma":
            owee = objetivo.value.strip().lower() == "owee"
            nota_idioma.visible = owee
            st.page.update()

    objetivo.on_change = es_owee
    nota_idioma.controls = [ft.Text(t("¡Owee tiene su propio curso dentro de la app, con lecciones, glifos y tarjetas!"), size=13),
                            ft.OutlinedButton(t("Ir a Aprende Owee"), icon=ft.Icons.TRANSLATE, on_click=lambda _: ir_a_owee())]

    def elegir_tipo(e):
        est["tipo"] = e.control.value
        zona_previa.controls = []
        aviso.value = ""
        objetivo.label = t(ETIQUETA_OBJETIVO[est["tipo"]])
        extra = {"asignatura": [temario], "idioma": [ft.Row([nivel_actual, nivel_meta], wrap=True), nota_idioma],
                 "tecnologia": [nivel_tec, proyecto], "posgrado": [etapa, lecturas]}[est["tipo"]]
        zona_campos.controls = [
            objetivo, *extra, ft.Row([horas, meses, limite], wrap=True), ft.Row([inicio, carpeta], wrap=True),
            ft.ElevatedButton(t("Ver vista previa"), icon=ft.Icons.VISIBILITY, on_click=previsualizar)]
        es_owee()
        st.page.update()

    def datos():
        h = _numero(horas.value, 0.0)
        m = _numero(meses.value, 0, entero=True)
        if limite.value.strip():
            try:
                dias = (date.fromisoformat(limite.value.strip()) - date.fromisoformat(inicio.value.strip())).days
                m = max(1, -(-dias // 30))
                meses.value = str(m)
            except ValueError:
                raise ValueError(t("La fecha límite o la de inicio no tiene el formato AAAA-MM-DD."))
        fecha_limite = date.fromisoformat(limite.value.strip()) if limite.value.strip() else None
        return pl.Datos(
            fecha_limite=fecha_limite, tipo=est["tipo"], objetivo=objetivo.value, horas_semana=h, meses=m,
            nivel_actual={"idioma": nivel_actual.value, "tecnologia": nivel_tec.value}.get(est["tipo"], ""),
            nivel_meta=nivel_meta.value if est["tipo"] == "idioma" else "",
            temario=temario.value.splitlines() if est["tipo"] == "asignatura" else [],
            proyecto=proyecto.value if est["tipo"] == "tecnologia" else "",
            lecturas_semana=_numero(lecturas.value, 3, entero=True), etapa=etapa.value)

    def previsualizar(_):
        zona_previa.controls = []
        try:
            d = datos()
            errores = pl.validar(d)
            if errores:
                raise ValueError(" ".join(errores))
            md = pl.generar_markdown(d)
        except ValueError as ex:
            aviso.value = str(ex)
            st.page.update()
            return
        aviso.value = ""
        r = pl.resumen(md)
        v = pl.viabilidad(d)
        filas = [ft.ListTile(dense=True, title=ft.Text(titulo, size=14),
                             subtitle=ft.Text(t("{n} temas · meses {a}-{b}", n=n, a=a, b=b), size=12),
                             leading=ft.Icon(ft.Icons.FOLDER_OPEN, size=20)) for titulo, n, a, b in r["unidades"]]
        zona_previa.controls = [
            tarjeta(t("Vista previa: {titulo}", titulo=pl.titulo_plan(d)),
                    ft.Text(pl.mensaje_viabilidad(d), color=ft.Colors.GREEN_400 if v["ok"] else ft.Colors.AMBER_400),
                    *filas,
                    ft.Text(t("Cada semana: {n} sesiones de 1 h en tu cronograma.", n=max(1, min(14, round(d.horas_semana)))), size=12),
                    ft.Row([ft.ElevatedButton(t("Crear plan"), icon=ft.Icons.CHECK, on_click=lambda _: crear(d)),
                            ft.OutlinedButton(t("Ver el plan en texto"), icon=ft.Icons.NOTES,
                                              on_click=lambda _: mostrar_texto(md))], wrap=True))]
        st.page.update()

    def mostrar_texto(md):
        dlg = ft.AlertDialog(title=ft.Text(t("Plan en texto")), content=ft.Column([ft.Text(md, selectable=True, size=12)],
                                                                                 scroll=ft.ScrollMode.AUTO, width=ancho_dialogo(st.page, 520), height=420),
                             actions=[ft.TextButton(t("Cerrar"), on_click=lambda _: st.page.close(dlg))])
        st.page.open(dlg)

    def crear(d):
        try:
            f = date.fromisoformat(inicio.value.strip())
            cid = None if carpeta.value in (None, "", "ninguna") else int(carpeta.value)
            st.plan_id = pl.crear_plan(c, d, st.perfil_id, f, cid)
        except Exception as ex:
            aviso.value = t("Error: {ex}", ex=ex)
            st.page.update()
            return
        st.toast(t("Plan creado"))
        ir_a_plan()

    tipos = ft.RadioGroup(on_change=elegir_tipo, content=ft.Column(
        [ft.Radio(value=k, label=t(pl.NOMBRES_TIPO[k])) for k in pl.TIPOS]))
    return ft.Column([
        ft.Text(t("Asistente de objetivo"), theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        ft.Text(t("Cuéntame qué quieres lograr y armo un plan con fases, fechas y un cronograma semanal realista. "
                  "Pone la estructura; el contenido de la materia lo pones tú."), size=13),
        ft.Text(t("¿Qué quieres lograr?"), weight=ft.FontWeight.BOLD), tipos, zona_campos, aviso, zona_previa,
    ], spacing=12, scroll=ft.ScrollMode.AUTO, expand=True)
