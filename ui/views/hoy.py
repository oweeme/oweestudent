from datetime import date

import flet as ft

from database import repo
from owee_curso import curso as curso_owee
from engine import ai
from engine import estudios as estudios_motor
from engine import nivel as niveles
from engine import retos as retos_motor
from engine import sprints as sprints_motor
from i18n import marcar, t, tn
from ui.components.widgets import barra_progreso, dialogo, tarjeta

# Se guardan en español en la base (cronograma.dia); solo se traducen al mostrarlos.
DIAS = [marcar("Lunes"), marcar("Martes"), marcar("Miércoles"), marcar("Jueves"), marcar("Viernes"),
        marcar("Sábado"), marcar("Domingo")]


def bienvenida(st, ir_asistente, ir_importar, ir_owee, curso_plan):
    """Pantalla de inicio cuando todavía no hay un estudio propio: primero lo tuyo; Owee es opcional."""
    c = st.conn
    owee = [ft.Text(t("Un idioma construido, con curso por niveles, glifos y tarjetas. Es opcional: tu propio estudio va primero."), size=13)]
    if curso_plan:
        sig = curso_owee.siguiente_leccion(c, curso_plan["id"])
        owee += [ft.ProgressBar(value=repo.progreso(c, curso_plan["id"])),
                 ft.ElevatedButton(t("Continuar: lección {id} — {titulo}", id=sig["id"], titulo=sig["titulo"]) if sig else t("Repasar el curso"),
                                   icon=ft.Icons.TRANSLATE, on_click=lambda _: ir_owee())]
    else:
        owee.append(ft.OutlinedButton(t("Empezar el curso"), icon=ft.Icons.TRANSLATE, on_click=lambda _: ir_owee()))
    return ft.Column([
        ft.Text(f"{t(DIAS[date.today().weekday()])} {date.today().isoformat()}", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
        tarjeta(t("Empieza aquí"),
                ft.Text(t("Aún no tienes tu estudio en la app. Cuéntale a la app qué quieres lograr, o importa un plan que ya tengas."), size=13),
                ft.Row([ft.ElevatedButton(t("Crear mi plan con el asistente"), icon=ft.Icons.FLAG, on_click=lambda _: ir_asistente()),
                        ft.OutlinedButton(t("Importar un plan que ya tengo"), icon=ft.Icons.UPLOAD_FILE, on_click=lambda _: ir_importar())], wrap=True)),
        tarjeta(t("Aprende Owee (opcional)"), *owee)],
        spacing=10, scroll=ft.ScrollMode.AUTO, expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def sesion_de_hoy(st, n_rev, ir_repaso, ir_a_estudio, ir_material, hoy):
    """Lo primero que ves al abrir: qué hacer AHORA, en orden, con un solo botón para empezar."""
    c, pom = st.conn, st.pomodoro
    if pom.activo:
        return tarjeta(t("Sesión en curso"), ft.Text(f"{t(pom.fase)} · {pom.texto()} — {pom.titulo}", size=13),
                       ft.ElevatedButton(t("Volver a estudiar"), icon=ft.Icons.TIMER, on_click=lambda _: ir_a_estudio()))
    tema = estudios_motor.proximo_tema(c, st.plan_id, hoy.isoformat())
    lect = estudios_motor.lectura_pendiente(c, st.plan_id)
    mins = niveles.ajustes(st.nivel())["pomodoro"][0]
    filas = []
    if n_rev:
        filas.append(ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.REPLAY), title=ft.Text(t("Repasa tus tarjetas: {n} pendientes", n=n_rev), size=13),
                                 on_click=lambda _: ir_repaso()))
    if tema:
        filas.append(ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.SCHOOL), title=ft.Text(t("Estudia: {tema}", tema=tema["titulo"]), size=13),
                                 subtitle=ft.Text(tema["unidad"], size=11)))
    if lect:
        def leer(_):
            st.abrir_material = (lect["id"], lect["pagina_actual"] or 1)
            ir_material()
        filas.append(ft.ListTile(dense=True, leading=ft.Icon(ft.Icons.MENU_BOOK), title=ft.Text(t("Sigue leyendo: {titulo}", titulo=lect["titulo"]), size=13),
                                 subtitle=ft.Text(t("página {a}/{b}", a=lect["pagina_actual"] or 1, b=lect["paginas"]) if lect["paginas"] else "", size=11),
                                 on_click=leer))
    if not filas:
        return tarjeta(t("Tu sesión de hoy"), ft.Text(t("Hoy no tienes nada pendiente. Añade temas en «Plan» o crea un reto."), size=13))

    def empezar(_):
        if tema:
            st.iniciar_pomodoro(tema["id"], tema["titulo"])
            ir_a_estudio()
        else:
            ir_repaso()
    return tarjeta(t("Tu sesión de hoy"), *filas,
                   ft.ElevatedButton(t("▶ Empezar ahora ({m} min)", m=mins) if tema else t("▶ Empezar a repasar"), icon=ft.Icons.PLAY_ARROW, on_click=empezar))


def build(st, ir_a_estudio, recargar, ir_repaso=lambda: None, ir_entregas=lambda: None, ir_sprint=lambda: None, ir_retos=lambda: None,
          ir_asistente=lambda: None, ir_importar=lambda: None, ir_owee=lambda: None, ir_material=lambda: None):
    c, hoy = st.conn, date.today()
    todos = repo.planes(c, st.perfil_id)
    curso_plan = next((p for p in todos if p["titulo"] == curso_owee.TITULO_PLAN), None)
    if not st.plan_id or not [p for p in todos if p["titulo"] != curso_owee.TITULO_PLAN]:
        return bienvenida(st, ir_asistente, ir_importar, ir_owee, curso_plan)
    dia = DIAS[hoy.weekday()]
    act = [ft.ListTile(dense=True, title=ft.Text(r["actividad"]), subtitle=ft.Text(r["bloque"]),
                       trailing=ft.IconButton(ft.Icons.CLOSE, icon_size=16, tooltip=t("Quitar del cronograma"),
                                              on_click=lambda _, i=r["id"]: (repo.borrar_cronograma(c, i), recargar())))
           for r in c.execute("SELECT * FROM cronograma WHERE plan_id=? AND dia=?", (st.plan_id, dia))]

    def add_crono(_):
        d = ft.Dropdown(label=t("Día"), value=dia, options=[ft.dropdown.Option(x, t(x)) for x in DIAS])
        b = ft.TextField(label=t("Bloque (ej. Bloque 1: IT)"))
        a = ft.TextField(label=t("Actividad"))
        dialogo(st.page, t("Añadir al cronograma"), [d, b, a], lambda v: (
            v[2].strip() and repo.agregar_cronograma(c, st.plan_id, v[0], v[1].strip() or t("Bloque"), v[2].strip()),
            recargar()))

    def reprogramar(_):
        n = ai.reprogramar_atrasados(c, st.plan_id)
        st.toast(tn(n, "{n} tema atrasado reprogramado desde hoy", "{n} temas atrasados reprogramados desde hoy"))
        recargar()
    temas = c.execute("""SELECT t.*, u.titulo unidad FROM temas t JOIN unidades u ON u.id=t.unidad_id
        WHERE u.plan_id=? AND t.estado!='completado' AND t.fecha_programada<=?
        ORDER BY t.fecha_programada DESC LIMIT 8""", (st.plan_id, (hoy).isoformat())).fetchall()

    def estudiar(tid, ti):
        st.tema_id, st.tema_titulo = tid, ti
        ir_a_estudio()

    tt = [ft.ListTile(dense=True, title=ft.Text(tm["titulo"], size=13),
                      subtitle=ft.Text(f"{tm['unidad']} · {tm['fecha_programada']}", size=11),
                      trailing=ft.IconButton(ft.Icons.PLAY_CIRCLE, on_click=lambda _, i=tm["id"], n=tm["titulo"]: estudiar(i, n)))
          for tm in temas] or [ft.Text(t("Nada pendiente para hoy 🎉"))]
    meta = repo.meta_semanal(c, st.plan_id)
    hs = repo.horas_semana(c, st.perfil_id)
    n_rev = len(repo.tarjetas_pendientes(c, st.perfil_id)) + len(repo.repasos_pendientes(c, st.perfil_id))
    prox = repo.proximas_entregas(c, st.perfil_id, 7)
    from ui.views.entregas import ICONOS, cuando
    tarjeta_entregas = tarjeta(
        t("Entregas y exámenes"),
        *([ft.ListTile(dense=True, leading=ft.Icon(ICONOS[e["tipo"]], size=18, color=ft.Colors.RED_300 if e["dias"] < 0 else ft.Colors.AMBER_400 if e["dias"] <= 1 else None),
                       title=ft.Text(e["titulo"], size=13), subtitle=ft.Text(f"{e['plan']} · {cuando(e['dias'])}", size=11), on_click=lambda _: ir_entregas())
           for e in prox[:5]] or [ft.Text(t("Nada para esta semana 🎉"))]),
        ft.TextButton(t("Ver todas / añadir"), on_click=lambda _: ir_entregas()))
    extras = []
    s = sprints_motor.sprint_activo(c, st.perfil_id)
    if s is not None:
        paso = sprints_motor.tarea_de_hoy(c, s)
        if paso is not None:
            extras.append(tarjeta(t("Tu sprint de 7 días"), ft.Text(s["titulo"], size=12, color=ft.Colors.OUTLINE),
                                  ft.ListTile(dense=True, title=ft.Text(t("Día {n}", n=paso["dia"]) + " · " + paso["titulo"], size=13),
                                              on_click=lambda _: ir_sprint()),
                                  ft.TextButton(t("Abrir el sprint"), on_click=lambda _: ir_sprint())))
    abiertos = [r for r in retos_motor.retos(c, st.perfil_id, estado="pendiente")]
    if abiertos:
        extras.append(tarjeta(t("Retos abiertos"), *[ft.ListTile(dense=True, title=ft.Text(r["titulo"], size=13), subtitle=ft.Text(f"{retos_motor.progreso(r):.0%}", size=11),
                                                                 on_click=lambda _: ir_retos()) for r in abiertos[:3]],
                              ft.TextButton(t("Ver todos los retos"), on_click=lambda _: ir_retos())))
    if curso_plan and curso_plan["id"] != st.plan_id:       # el curso ya está en tu plan: un recordatorio discreto, nunca por encima de lo tuyo
        sig = curso_owee.siguiente_leccion(c, curso_plan["id"])
        if sig:
            from engine import escritura_owee as owee_motor
            dia = owee_motor.palabra_del_dia(hoy, sig["id"])
            extras.append(tarjeta(t("Aprende Owee · opcional"),
                                  ft.ListTile(dense=True, title=ft.Text(t("Lección {id} — {titulo}", id=sig["id"], titulo=sig["titulo"]), size=13),
                                              on_click=lambda _: ir_owee()),
                                  *([ft.Text(f"{t('Palabra del día')}: {dia[0]} · {dia[1]}", size=12, color=ft.Colors.OUTLINE)] if dia else [])))
    return ft.Column([ft.Text(f"{t(dia)} {hoy.isoformat()}", theme_style=ft.TextThemeStyle.HEADLINE_SMALL),
                      sesion_de_hoy(st, n_rev, ir_repaso, ir_a_estudio, ir_material, hoy),
                      tarjeta(t("Esta semana"), barra_progreso(min(1, hs / meta), t("{h:.1f} de {meta:g} h ·", h=hs, meta=meta)),
                              ft.TextButton(tn(n_rev, "🔁 {n} repaso pendiente hoy → empezar", "🔁 {n} repasos pendientes hoy → empezar")
                                            if n_rev else t("🔁 Repasos al día ✅"),
                                            on_click=lambda _: ir_repaso())),
                      tarjeta_entregas, *extras,
                      tarjeta(t("Cronograma de hoy"), *(act or [ft.Text(t("Sin cronograma importado"))]),
                              ft.TextButton(t("＋ Añadir al cronograma"), on_click=add_crono)),
                      tarjeta(t("Temas programados / atrasados"), *tt,
                              ft.OutlinedButton(t("Reprogramar atrasados (inteligente)"), icon=ft.Icons.AUTO_FIX_HIGH,
                                                on_click=reprogramar))],
                     spacing=10, scroll=ft.ScrollMode.AUTO, expand=True,
                     horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
