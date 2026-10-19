"""English. Clave = texto en español; valor = traducción (o tupla (singular, plural) para tn())."""
TEXTOS = {
    # --- niveles, días, tipos ---
    "primaria": "primary school", "secundaria": "secondary school", "adolescente": "teenager",
    "universitario": "university", "adulto": "adult",
    "Lunes": "Monday", "Martes": "Tuesday", "Miércoles": "Wednesday", "Jueves": "Thursday",
    "Viernes": "Friday", "Sábado": "Saturday", "Domingo": "Sunday",
    "url": "link", "libro": "book", "herramienta": "tool", "alternativa": "alternative",
    "Conclusión": "Conclusion", "Cita": "Quote", "Duda": "Question", "Idea": "Idea",
    "mínimo (equipos muy justos)": "minimum (very limited computers)", "ligero": "light",
    "equilibrado": "balanced", "completo": "full",

    # --- botones y palabras comunes ---
    "Guardar": "Save", "Cancelar": "Cancel", "Sí, borrar": "Yes, delete", "Crear": "Create",
    "Borrar": "Delete", "Editar": "Edit", "Quitar": "Remove", "Renombrar": "Rename", "Mover": "Move",
    "Entrar": "Sign in", "Importar": "Import", "Adjuntar": "Attach", "Leer": "Read", "Probar": "Test",
    "Detectar": "Detect", "Generar": "Generate", "Sincronizar": "Sync", "Detener": "Stop",
    "Pregunta": "Question", "Respuesta": "Answer", "Tipo": "Type", "Nombre": "Name", "Título": "Title",
    "Tema": "Topic", "Nivel": "Level", "Meses": "Months", "Día": "Day", "Hoja": "Sheet", "Clave": "Password",
    "Usuario": "User", "Actividad": "Activity", "PIN": "PIN", "Bloque": "Block", "Modelo": "Model",
    "Motor de IA": "AI engine", "Listo": "Done", "listo": "done", "Auto": "Auto", "Oscuro": "Dark", "Claro": "Light",
    "Sin datos aún": "No data yet", "Probando…": "Testing…", "Pensando…": "Thinking…",
    "Evaluando…": "Evaluating…", "Sincronizando…": "Syncing…", "Detenido": "Stopped",
    "(Sin carpeta)": "(No folder)", "Sin carpeta": "No folder", "(ninguno)": "(none)",
    "Estudio": "Study", "Descanso": "Break",

    # --- navegación (main) ---
    "Hoy": "Today", "Plan": "Plan", "Material": "Material", "Repaso": "Review", "Más": "More",
    "Estudiar (Pomodoro y tarjetas)": "Study (Pomodoro and flashcards)",
    "Carpetas y asignaturas": "Folders and subjects", "Importar plan": "Import plan", "Métricas": "Stats",
    "Sincronizar con otro equipo": "Sync with another device", "Ajustes, IA y apariencia": "Settings, AI and appearance",
    "Aún no hay asignatura. Ve a «Más → Carpetas y asignaturas» o «Importar plan».":
        "There is no subject yet. Go to “More → Folders and subjects” or “Import plan”.",

    # --- acceso ---
    "Demasiados intentos. Espera {s} s": "Too many attempts. Wait {s} s",
    "Clave incorrecta": "Wrong password", "Inicia sesión para continuar": "Sign in to continue",

    # --- hoy ---
    "Añadir al cronograma": "Add to schedule", "＋ Añadir al cronograma": "＋ Add to schedule",
    "Quitar del cronograma": "Remove from schedule", "Bloque (ej. Bloque 1: IT)": "Block (e.g. Block 1: IT)",
    "{n} temas atrasados reprogramados desde hoy":
        ("{n} overdue topic rescheduled from today", "{n} overdue topics rescheduled from today"),
    "Nada pendiente para hoy 🎉": "Nothing due today 🎉", "Esta semana": "This week",
    "{h:.1f} de {meta:g} h ·": "{h:.1f} of {meta:g} h ·",
    "🔁 {n} repasos pendientes hoy → empezar":
        ("🔁 {n} review due today → start", "🔁 {n} reviews due today → start"),
    "🔁 Repasos al día ✅": "🔁 Reviews up to date ✅", "Cronograma de hoy": "Today's schedule",
    "Sin cronograma importado": "No schedule imported", "Temas programados / atrasados": "Scheduled / overdue topics",
    "Reprogramar atrasados (inteligente)": "Reschedule overdue topics (smart)",

    # --- plan ---
    "Aún no hay plan. Ve a «Planes» para crear uno o a «Importar».": "There is no plan yet. Go to “Plans” to create one or to “Import”.",
    "Progreso general": "Overall progress", "Nuevo tema": "New topic", "Nuevo recurso": "New resource",
    "Fecha programada (AAAA-MM-DD, opcional)": "Scheduled date (YYYY-MM-DD, optional)",
    "Enlace, libro o recurso": "Link, book or resource", "Fecha (AAAA-MM-DD)": "Date (YYYY-MM-DD)",
    "Horas estimadas": "Estimated hours", "Editar tema": "Edit topic", "¿Borrar este tema?": "Delete this topic?",
    "Renombrar unidad": "Rename unit", "¿Borrar la unidad con sus temas y recursos?": "Delete the unit with its topics and resources?",
    "Título (ej. Módulo IT: Redes, o Inglés B2)": "Title (e.g. IT module: Networks, or English B2)",
    "Nueva unidad": "New unit", "＋ Nueva unidad / módulo": "＋ New unit / module",
    "{fecha} · {hechas:.1f}/{est} h": "{fecha} · {hechas:.1f}/{est} h", " (meses {a}-{b})": " (months {a}-{b})",
    "Recursos": "Resources", "＋ Tema": "＋ Topic", "＋ Recurso": "＋ Resource", "Borrar unidad": "Delete unit",
    "Estudiar": "Study",

    # --- importar ---
    "Fecha de inicio (AAAA-MM-DD)": "Start date (YYYY-MM-DD)", "Guardar en la carpeta": "Save in folder",
    "Crear un plan nuevo": "Create a new plan", "Agregar al plan activo": "Add to the active plan",
    "Importado": "Imported", "Error: {ex}": "Error: {ex}", "Error IA: {ex}": "AI error: {ex}",
    "…o pega la ruta del archivo": "…or paste the file path",
    "…o pega aquí el texto (Markdown: temas, tablas de cronograma, etc.)": "…or paste the text here (Markdown: topics, schedule tables, etc.)",
    "Objetivo (ej. Aprobar cálculo I / Aprender redes para IT / Inglés B2)": "Goal (e.g. Pass Calculus I / Learn networking for IT / English B2)",
    "Horas/semana": "Hours/week", "Revisa horas y meses (deben ser números)": "Check hours and months (they must be numbers)",
    "Prompt copiado. Pégalo en tu chat de IA": "Prompt copied. Paste it into your AI chat",
    "Configura la IA en Ajustes (o usa «Copiar prompt» con tu chat)": "Set up the AI in Settings (or use “Copy prompt” with your chat)",
    "Plan generado: revísalo/edítalo abajo y pulsa «Importar texto pegado».": "Plan generated: review/edit it below and press “Import pasted text”.",
    "Importar plan de estudios": "Import study plan", "✨ Generar un plan con IA (opcional)": "✨ Generate a plan with AI (optional)",
    "Copiar prompt para mi chat (Claude, ChatGPT…)": "Copy prompt for my chat (Claude, ChatGPT…)",
    "Con «Copiar prompt»: pégalo en tu chat, copia su respuesta y pégala abajo en «Importar texto pegado». Funciona con tu suscripción normal, sin API.":
        "With “Copy prompt”: paste it into your chat, copy its answer and paste it below in “Import pasted text”. It works with your regular subscription, no API needed.",
    "Acepta {formatos} o texto pegado. Detecta módulos, temas, bibliografía, enlaces, entregables, idiomas y cronograma semanal.":
        "Accepts {formatos} or pasted text. It detects modules, topics, bibliography, links, deliverables, languages and the weekly schedule.",
    "Elegir archivo": "Choose file", "Importar texto pegado": "Import pasted text", "Plan pegado": "Pasted plan",

    # --- estudiar ---
    "Elige un tema desde «Plan» u «Hoy»": "Pick a topic from “Plan” or “Today”",
    "Pomodoro registrado (+25 min)": "Pomodoro logged (+25 min)", "Primero elige un tema": "Pick a topic first",
    "Explícalo con tus palabras (Feynman / Active Recall)": "Explain it in your own words (Feynman / active recall)",
    "Elige un tema y escribe tu resumen": "Pick a topic and write your summary",
    "Repaso programado: {fecha}": "Review scheduled: {fecha}",
    "Tus apuntes o material del tema (pega texto; usa **negritas** para términos clave)": "Your notes or material for the topic (paste text; use **bold** for key terms)",
    "{n} tarjetas creadas (sin IA). Se repasan en «Repaso».":
        ("{n} flashcard created (no AI). It is reviewed in “Review”.", "{n} flashcards created (no AI). They are reviewed in “Review”."),
    "No detecté definiciones. Usa el formato «Término: explicación» o **negritas**.": "I found no definitions. Use the format “Term: explanation” or **bold**.",
    "Configura la IA local en Ajustes.": "Set up the local AI in Settings.", "Pega primero tus apuntes.": "Paste your notes first.",
    "Generando tarjetas…": "Generating flashcards…",
    "{n} tarjetas creadas con IA. Revísalas: un modelo pequeño puede fallar.":
        ("{n} flashcard created with AI. Check it: a small model can be wrong.", "{n} flashcards created with AI. Check them: a small model can be wrong."),
    "Tarjeta añadida": "Flashcard added", "Configura la IA en Ajustes para usar esta función.": "Set up the AI in Settings to use this feature.",
    "Elige primero un tema.": "Pick a topic first.",
    "Preguntas para comprobarte (verifica las respuestas en tu material):": "Questions to test yourself (check the answers against your material):",
    "¿Qué tan bien lo recordaste? (0 nada – 5 perfecto)": "How well did you remember it? (0 nothing – 5 perfect)",
    "Tarjetas de repaso (tú creas las preguntas)": "Review flashcards (you write the questions)",
    "＋ Añadir tarjeta manual": "＋ Add flashcard manually", "Iniciar Pomodoro": "Start Pomodoro",
    "Crear tarjetas de mis apuntes": "Create flashcards from my notes", "✨ Con IA": "✨ With AI",
    "Guardar y programar repaso": "Save and schedule review", "✨ Preguntas de repaso (IA)": "✨ Review questions (AI)",

    # --- repaso ---
    "¿Qué tan bien lo recordaste? 0 = nada · 3 = con esfuerzo · 5 = perfecto": "How well did you remember it? 0 = nothing · 3 = with effort · 5 = perfect",
    "No tienes repasos pendientes hoy 🎉 Crea tarjetas desde tus apuntes en «Estudiar».": "You have no reviews due today 🎉 Create flashcards from your notes in “Study”.",
    "Tarjetas pendientes: {n}": "Flashcards due: {n}", "Resúmenes (Feynman) pendientes: {n}": "Summaries (Feynman) due: {n}",
    "Explica con tus palabras: {tema}": "Explain in your own words: {tema}",
    "Mostrar respuesta (intenta recordar primero)": "Show answer (try to recall it first)",

    # --- métricas ---
    "A tu ritmo real ({h:.1f} h/semana) terminas hacia {fin:%d/%m/%Y}. Faltan {n} temas (~{horas:.0f} h).":
        "At your real pace ({h:.1f} h/week) you will finish around {fin:%d/%m/%Y}. {n} topics left (~{horas:.0f} h).",
    "Faltan {n} temas (~{horas:.0f} h). Registra sesiones con el Pomodoro para calcular tu fecha de fin.":
        "{n} topics left (~{horas:.0f} h). Log sessions with the Pomodoro to estimate your finish date.",
    "🔥 Racha": "🔥 Streak", "{n} días": ("{n} day", "{n} days"), "⏱ Últimos 7 días": "⏱ Last 7 days", "{h:.1f} h": "{h:.1f} h",
    "Retención (últimos 30 días)": "Retention (last 30 days)",
    "{ret:.0%} de recuerdos acertados en {rep} repasos · {tj} tarjetas": "{ret:.0%} recalled correctly in {rep} reviews · {tj} flashcards",
    "Aún sin repasos. Crea tarjetas en «Estudiar» y repásalas cada día.": "No reviews yet. Create flashcards in “Study” and review them every day.",
    "Proyección de fin": "Finish projection", "Avance por unidad": "Progress by unit", "Mayor índice de olvido": "Most forgotten",

    # --- carpetas y perfiles ---
    "Clave de ese usuario": "That user's password", "Cambiar de usuario": "Switch user",
    "Perfil (quién estudia)": "Profile (who is studying)", "Nuevo perfil": "New profile", "Clave (opcional)": "Password (optional)",
    "Clave actual": "Current password", "Clave nueva (vacía = sin clave)": "New password (empty = no password)",
    "La clave actual no coincide": "The current password does not match", "Clave actualizada": "Password updated",
    "Clave eliminada": "Password removed", "Clave de acceso": "Access password", "Clave de este perfil": "This profile's password",
    "Cerrar sesión": "Sign out", "Nueva carpeta": "New folder", "Renombrar carpeta": "Rename folder",
    "Nombre (ej. Máster, 3º de secundaria, Idiomas)": "Name (e.g. Master's, 9th grade, Languages)",
    "Nombre (ej. Matemática, Alemán, Redes)": "Name (e.g. Mathematics, German, Networking)",
    "¿Borrar la carpeta «{nombre}» con todas sus asignaturas y su progreso?": "Delete the folder “{nombre}” with all its subjects and progress?",
    "Nueva asignatura": "New subject", "Mover «{titulo}»": "Move “{titulo}”", "Mover a la carpeta": "Move to folder",
    "¿Borrar esta asignatura y su progreso?": "Delete this subject and its progress?",
    "Progreso {p:.0%}": "Progress {p:.0%}", "  ·  activa": "  ·  active", "Mover a otra carpeta": "Move to another folder",
    "＋ Asignatura": "＋ Subject", "Importar aquí": "Import here", "Borrar carpeta": "Delete folder", "＋ Nueva carpeta": "＋ New folder",
    "Una carpeta agrupa tus asignaturas (ej. «Máster» → Management, Idiomas, IT; o «3º de secundaria» → Matemática, Ciencias, Historia). Toca una asignatura para activarla.":
        "A folder groups your subjects (e.g. “Master's” → Management, Languages, IT; or “9th grade” → Maths, Science, History). Tap a subject to make it active.",

    # --- material ---
    "Primero crea o elige una asignatura en «Planes».": "First create or pick a subject in “Plans”.",
    "Solo enlazar (no copiar el archivo)": "Link only (do not copy the file)",
    "Ese archivo no es el mismo (su contenido es distinto).": "That is not the same file (its content is different).",
    "Archivo vinculado ✅": "File linked ✅",
    "«{titulo}» ya estaba adjuntado en esta asignatura: no se duplicó.": "“{titulo}” was already attached to this subject: it was not duplicated.",
    "Adjuntado ✅": "Attached ✅", " (ya lo tenías en otra asignatura: se reutilizó el mismo archivo)": " (you already had it in another subject: the same file was reused)",
    "No se pudo adjuntar: {ex}": "Could not attach: {ex}",
    "¿Quitar «{titulo}» y sus notas? (el archivo original no se borra)": "Remove “{titulo}” and its notes? (the original file is not deleted)",
    "página {a}/{b}": "page {a}/{b}", "sin empezar": "not started", "{n} notas": ("{n} note", "{n} notes"),
    "  ·  ⚠ el archivo no está en este equipo": "  ·  ⚠ the file is not on this device",
    "Vincular el archivo aquí": "Link the file here", "Material · {plan}": "Material · {plan}",
    "Adjunta tus libros, PDFs, Word, Excel o CSV. Un mismo archivo nunca se duplica, aunque lo adjuntes en varias asignaturas. Lee dentro de la app, guarda conclusiones y crea tarjetas.":
        "Attach your books, PDFs, Word, Excel or CSV files. The same file is never duplicated, even if you attach it to several subjects. Read inside the app, save conclusions and create flashcards.",
    "＋ Adjuntar archivo": "＋ Attach file", "Aún no hay material en esta asignatura.": "There is no material in this subject yet.",
    "No se pudo leer el archivo: {ex}": "Could not read the file: {ex}",
    "Tu conclusión o idea clave (página {n})": "Your conclusion or key idea (page {n})",
    "{n} tarjetas creadas desde esta página.": ("{n} flashcard created from this page.", "{n} flashcards created from this page."),
    "No encontré definiciones («Término: explicación») ni **negritas**. Guarda tus conclusiones y vuelve a probar, o crea tarjetas a mano en «Estudiar».":
        "I found no definitions (“Term: explanation”) or **bold** text. Save your conclusions and try again, or create flashcards by hand in “Study”.",
    "Configura la IA en Ajustes para usar esto.": "Set up the AI in Settings to use this.",
    "(Resumen automático: verifícalo con el texto.)": "(Automatic summary: check it against the text.)",
    "Importar como tarjetas de vocabulario…": "Import as vocabulary flashcards…", "Volver al material": "Back to material",
    "de {total}": "of {total}", "{n} notas en total": ("{n} note in total", "{n} notes in total"),
    "Tus conclusiones de esta página": "Your conclusions for this page", "Crear tarjetas de esta página": "Create flashcards from this page",
    "✨ Resumir": "✨ Summarize", "No se pudo leer la tabla: {ex}": "Could not read the table: {ex}", "columna {n}": "column {n}",
    "Pregunta (ej. palabra en alemán/chino)": "Question (e.g. German/Chinese word)", "Respuesta (ej. significado)": "Answer (e.g. meaning)",
    "Dato extra opcional (ej. pinyin)": "Optional extra (e.g. pinyin)", "La primera fila es cabecera": "The first row is a header",
    "Crear también respuesta → pregunta": "Also create answer → question",
    "{n} tarjetas creadas (las repetidas se omitieron). Repásalas en «Repaso».":
        ("{n} flashcard created (duplicates were skipped). Review it in “Review”.", "{n} flashcards created (duplicates were skipped). Review them in “Review”."),
    "No se pudo importar: {ex}": "Could not import: {ex}", "Importar vocabulario": "Import vocabulary", "Crear tarjetas": "Create flashcards",

    # --- sincronizar ---
    "Nombre de este equipo": "Name of this device", "Nombre guardado": "Name saved", "Todo mi estudio": "All my study data",
    "Solo la carpeta «{nombre}»": "Only the folder “{nombre}”", "Qué compartir": "What to share",
    "Error al mezclar: {ex}": "Error while merging: {ex}", "Se cerró por demasiados PIN incorrectos. Vuelve a empezar.": "Closed after too many wrong PINs. Start again.",
    "✅ Sincronizado: {nuevos} nuevos, {actualizados} actualizados, {borrados} borrados.": "✅ Synced: {nuevos} new, {actualizados} updated, {borrados} deleted.",
    "El tiempo terminó sin sincronizar. Puedes volver a intentarlo.": "Time ran out without syncing. You can try again.",
    "No se pudo abrir la sincronización: {ex}": "Could not open syncing: {ex}",
    "Este equipo aparece como «{nombre}»": "This device appears as “{nombre}”",
    "En el otro equipo: Sincronizar → Buscar equipos → elige este → escribe el PIN.": "On the other device: Sync → Find devices → pick this one → enter the PIN.",
    "Otras formas de conectar (IP / QR)": "Other ways to connect (IP / QR)", "IP de este equipo: {ip}": "This device's IP: {ip}",
    "QR con enlace propio: al escanearlo con la cámara del móvil, Android debería abrir OweeStudent y conectar solo (experimental). Si solo ves texto, cópialo en «Conectar por IP».":
        "QR with its own link: when scanned with the phone camera, Android should open OweeStudent and connect on its own (experimental). If you only see text, copy it into “Connect by IP”.",
    "Válido 5 minutos. Mientras tanto, deja esta pantalla abierta.": "Valid for 5 minutes. Keep this screen open meanwhile.",
    "PIN que muestra el otro equipo": "PIN shown on the other device", "Sincronizando con {equipo}…": "Syncing with {equipo}…",
    "Sincronizar con {equipo}": "Sync with {equipo}", "Buscando equipos en tu Wi-Fi…": "Looking for devices on your Wi-Fi…",
    "Error buscando: {ex}": "Search error: {ex}", "Carpeta: {nombre}": "Folder: {nombre}", "Todo su estudio": "All their study data",
    "No encontré equipos en {red}.x (tu IP: {ip}).": "I found no devices on {red}.x (your IP: {ip}).",
    "1) En el otro equipo abre Sincronizar → «Permitir sincronización».  2) Ambos en el mismo Wi-Fi.  3) Si sigue sin aparecer, su cortafuegos puede estar bloqueando: prueba AL REVÉS (permite aquí y busca desde el otro) o usa «Conectar por IP» → «Probar conexión» para saber el motivo.":
        "1) On the other device open Sync → “Allow syncing”.  2) Both on the same Wi-Fi.  3) If it still does not show up, its firewall may be blocking it: try the OTHER WAY AROUND (allow here and search from the other) or use “Connect by IP” → “Test connection” to find out why.",
    "IP del otro equipo, o el enlace del QR": "IP of the other device, or the QR link", "Escribe primero la IP del otro equipo.": "Enter the other device's IP first.",
    "Escribe la IP": "Enter the IP", "No se pudo sincronizar: {ex}": "Could not sync: {ex}", "Sincronizar": "Sync",
    "Escanea con la cámara del móvil: abre OweeStudent en el navegador, con los datos de este equipo en vivo.":
        "Scan with the phone camera: it opens OweeStudent in the browser, with this device's data live.",
    "Estudia en cualquier equipo y sincroniza: se mezclan los cambios de los dos (gana el más reciente en cada elemento) y ambos quedan iguales. Se guarda un respaldo antes de mezclar.":
        "Study on any device and sync: the changes from both are merged (the most recent wins for each item) and both end up the same. A backup is saved before merging.",
    "1 · Este equipo": "1 · This device", "2 · Dar permiso a otro equipo": "2 · Allow another device", "Permitir sincronización": "Allow syncing",
    "3 · Buscar equipos cercanos": "3 · Find nearby devices", "Buscar equipos": "Find devices", "¿No aparece? Conectar por IP": "Not showing up? Connect by IP",
    "Probar conexión": "Test connection", "Usar en el móvil sin instalar nada": "Use on your phone without installing anything",
    "Mientras este equipo esté encendido, tu móvil o tablet usa la app por Wi-Fi.": "As long as this device is on, your phone or tablet uses the app over Wi-Fi.",
    "Activar / desactivar": "Turn on / off", "Sincronizar": "Sync",

    # --- ajustes ---
    "Ajustes": "Settings", "Idioma de la interfaz": "Interface language", "Apariencia": "Appearance",
    "Servidor local": "Local server", "Modelo local": "Local model", "Modelo del otro equipo": "Model on the other device",
    "IA de otro equipo (opcional, ej. http://192.168.1.50:11434)": "AI on another device (optional, e.g. http://192.168.1.50:11434)",
    "No encontré ningún servidor. ¿Está Ollama/LM Studio abierto?": "I found no server. Is Ollama/LM Studio open?",
    "Encontrados {n} modelos en {url}": "Found {n} models at {url}", "No se pudo conectar: {ex}": "Could not connect: {ex}",
    "Buscando IA en tu red…": "Looking for AI on your network…",
    "No encontré ninguna. En el otro equipo inicia Ollama así: OLLAMA_HOST=0.0.0.0 ollama serve": "I found none. On the other device start Ollama like this: OLLAMA_HOST=0.0.0.0 ollama serve",
    "Encontrada: {url} ({n} modelos). Pulsa Guardar.": "Found: {url} ({n} models). Press Save.",
    "IA configurada (se guarda solo en este equipo, no se sincroniza)": "AI configured (saved only on this device, it is not synced)",
    "Respuesta: {texto}": "Answer: {texto}", "Falló: {ex}": "Failed: {ex}",
    "  ⚠ el presupuesto es menor que el modelo mínimo": "  ⚠ the budget is smaller than the minimum model",
    "RAM: {total:.1f} GB ({libre:.1f} libres). Presupuesto para la IA ({pct:.0f}%): {pres:.1f} GB → modelo recomendado: {m} (~{gb} GB, {desc}).":
        "RAM: {total:.1f} GB ({libre:.1f} free). AI budget ({pct:.0f}%): {pres:.1f} GB → recommended model: {m} (~{gb} GB, {desc}).",
    "Modelo {modelo} instalado y configurado": "Model {modelo} installed and configured",
    "No se pudo descargar. ¿Está Ollama instalado y abierto? (ollama.com/download) Detalle: {ex}": "Could not download. Is Ollama installed and open? (ollama.com/download) Details: {ex}",
    "⬇ Instalar IA (descarga única)": "⬇ Install AI (one-time download)", "Desinstalar": "Uninstall",
    "✅ IA instalada (modelo {modelo}). Se enciende sola al usarla y se apaga después para no gastar RAM.":
        "✅ AI installed (model {modelo}). It starts by itself when used and shuts down afterwards to save RAM.",
    "La IA integrada todavía no está instalada.": "The built-in AI is not installed yet.",
    "Este dispositivo no puede ejecutar la IA por sí solo. Usa la IA de tu PC: abre «Opciones avanzadas» → «Buscar en mi red».":
        "This device cannot run the AI by itself. Use your PC's AI: open “Advanced options” → “Find on my network”.",
    "Se instalará el modelo {modelo} (~{gb:.1f} GB) y un motor de ~20 MB, elegido por tu RAM ({ram:.0f} GB, usando hasta el {pct:.0f}%). Se descarga una sola vez y puede continuar si se corta.":
        "Model {modelo} (~{gb:.1f} GB) and a ~20 MB engine will be installed, chosen for your RAM ({ram:.0f} GB, using up to {pct:.0f}%). It downloads once and resumes if interrupted.",
    "✅ IA instalada. Ya puedes usar «Generar plan con IA» y las tarjetas con IA.": "✅ AI installed. You can now use “Generate plan with AI” and AI flashcards.",
    "No se pudo instalar: {ex}": "Could not install: {ex}", "IA desinstalada": "AI uninstalled",
    "Opciones avanzadas (Ollama / IA de otro equipo)": "Advanced options (Ollama / AI on another device)",
    "⬇ Instalar con Ollama (ya instalado)": "⬇ Install with Ollama (already installed)",
    "Si este equipo no puede con la IA, usa la de otro (tu PC, por Wi-Fi). Si hay varias, la app prueba en orden: integrada → Ollama de este equipo → otro equipo.":
        "If this device cannot handle the AI, use another one (your PC, over Wi-Fi). If there are several, the app tries them in order: built-in → Ollama on this device → another device.",
    "Buscar en mi red": "Find on my network", "Inteligencia artificial (opcional)": "Artificial intelligence (optional)",
    "Sin IA la app ya reprograma atrasados, crea tarjetas de tus apuntes y proyecta tu fin. Con IA añade: generar un plan desde un objetivo y tarjetas/resúmenes del material. Todo ocurre en tu equipo: nada sale de él.":
        "Without AI the app already reschedules overdue topics, builds flashcards from your notes and projects your finish date. With AI it adds: generating a plan from a goal and flashcards/summaries from your material. Everything happens on your device: nothing leaves it.",
    "Probar la IA": "Test the AI", "Acerca de {app} · v{version}": "About {app} · v{version}",
    "Creado por {autor}. Gratis y sin anuncios. Si te sirve, puedes apoyar su desarrollo.": "Created by {autor}. Free and ad-free. If it helps you, you can support its development.",
    "☕ Donar (PayPal)": "☕ Donate (PayPal)", "Sitio web": "Website",

    # --- motor: IA, archivos, sincronización ---
    "Configura una IA en Ajustes (este equipo u otro de tu red)": "Set up an AI in Settings (this device or another on your network)",
    "El modelo no devolvió módulos. Reintenta.": "The model returned no modules. Try again.", "Ninguna IA respondió →": "No AI answered →",
    "El motor de IA se cerró al arrancar (detalles en {ruta})": "The AI engine closed on startup (details in {ruta})",
    "A tu sistema le falta una librería ({lib}). Instálala una vez con: sudo apt install {pkg} (o pide ayuda a quien administre el equipo) y vuelve a intentarlo.":
        "Your system is missing a library ({lib}). Install it once with: sudo apt install {pkg} (or ask whoever manages the computer) and try again.",
    "Este dispositivo no puede ejecutar la IA integrada. Usa la IA de otro equipo.": "This device cannot run the built-in AI. Use the AI of another device.",
    "El paquete del motor de IA no contiene llama-server": "The AI engine package does not contain llama-server",
    "La IA integrada no está instalada (Ajustes → IA)": "The built-in AI is not installed (Settings → AI)",
    "El motor de IA tardó demasiado en arrancar": "The AI engine took too long to start",
    "No se pudo descargar ({ex}). Revisa tu conexión y vuelve a intentarlo: continuará donde se quedó.": "Could not download ({ex}). Check your connection and try again: it will resume where it stopped.",
    "{etiqueta} {hecho:.0f} de {total:.0f} MB": "{etiqueta} {hecho:.0f} of {total:.0f} MB",
    "Este equipo no está conectado a ninguna red Wi-Fi/LAN.": "This device is not connected to any Wi-Fi/LAN network.",
    "Los equipos parecen estar en redes distintas (este: {yo}, el otro: {host}). Conecta ambos al mismo Wi-Fi (ojo con «red de invitados» o datos móviles).":
        "The devices seem to be on different networks (this one: {yo}, the other: {host}). Connect both to the same Wi-Fi (watch out for “guest network” or mobile data).",
    "✅ Conectado con «{nombre}». Falta el PIN.": "✅ Connected to “{nombre}”. The PIN is still needed.",
    "El archivo recibido no es una base de OweeStudent": "The received file is not an OweeStudent database",
    "Falta el PIN del otro equipo": "The other device's PIN is missing",
    "Equipo nuevo: recibiste una copia completa": "New device: you received a full copy",
    "Mezclado: {nuevos} nuevos, {actualizados} actualizados, {borrados} borrados": "Merged: {nuevos} new, {actualizados} updated, {borrados} deleted",
    "{n} archivos de material copiados": "{n} material files copied", ". El otro equipo también quedó actualizado.": ". The other device is up to date too.",
    "El otro equipo no responde (tiempo agotado). Casi siempre es su CORTAFUEGOS bloqueando conexiones entrantes. En Linux: sudo ufw allow {puerto}/tcp  ·  En Deepin: Centro de control → Cortafuegos. O prueba al revés: pulsa «Permitir sincronización» en ESTE equipo y busca desde el otro.":
        "The other device is not answering (timed out). It is almost always its FIREWALL blocking incoming connections. On Linux: sudo ufw allow {puerto}/tcp  ·  On Deepin: Control Center → Firewall. Or try the other way around: press “Allow syncing” on THIS device and search from the other.",
    "El equipo está encendido pero la sincronización no está abierta: pulsa «Permitir sincronización» allí.": "The device is on but syncing is not open: press “Allow syncing” there.",
    "Hay algo en ese puerto, pero no es OweeStudent.": "Something is on that port, but it is not OweeStudent.",
    ". Pero no pude devolverlo al otro equipo ({ex}).": ". But I could not send it back to the other device ({ex}).",
    "No hay ruta hacia ese equipo: revisa que esté encendido y en el mismo Wi-Fi.": "There is no route to that device: check that it is on and on the same Wi-Fi.",
    "Esa carpeta no existe": "That folder does not exist", "PIN incorrecto": "Wrong PIN", "El otro equipo respondió {code}": "The other device answered {code}",
    "Formato no soportado: .{ext}": "Unsupported format: .{ext}",
    "DOCX no está disponible en esta versión. Usa MD, TXT, PDF o XLSX.": "DOCX is not available in this version. Use MD, TXT, PDF or XLSX.",
}
