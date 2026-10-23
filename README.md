# 🎓 OweeStudent

Plan de estudios + repaso espaciado (**FSRS**) + IA **local opcional**, para estudiantes y autodidactas.

- **Carpetas y asignaturas**: «Máster» → Management, Idiomas…; «3º de secundaria» → Matemática, Ciencias, Historia.
- Importa planes en **MD, TXT, PDF, DOCX, XLSX** (o pega texto): detecta módulos, temas, libros, enlaces, entregables e idiomas.
- **Material de estudio**: adjunta PDF/Word/Excel/CSV sin duplicar (por huella), léelo dentro de la app, guarda conclusiones, crea tarjetas de cada página e importa vocabulario desde Excel (ideal para alemán/chino).
- Modo **claro / oscuro / automático**.
- **Idiomas de la interfaz**: español, inglés, alemán, ruso, chino y japonés (Ajustes → «Idioma de la interfaz»; la primera vez usa el del sistema). **Owee** ([idioma construido](https://oweeme.github.io/owee/)) también está: con romanización o con su escritura propia (interruptor en Ajustes). Solo traduce lo que ya está en el glosario del idioma; el resto se ve en inglés y Ajustes muestra la cobertura y la lista de lo que falta. Las traducciones al alemán, ruso, chino y japonés están hechas con IA y **sin revisar por hablantes nativos**: si ves un error, avisa (ver «Traducir la app»). En Linux, chino y japonés necesitan una fuente (`sudo apt install fonts-noto-cjk`); la app avisa si falta.
- **Tarjetas de repaso** hechas de *tus* apuntes (con o sin IA) y repaso con FSRS.
- Pomodoro, metas semanales, racha, retención y proyección de fin.
- **Perfiles con clave** opcional (varios usuarios: tú, un familiar…).
- **Sincroniza entre equipos** (Wi-Fi local): el otro equipo aparece por su nombre, confirmas con un PIN de 6 dígitos (sin IP ni escaneo; también hay QR e IP manual). Mezcla los cambios de ambos y transfiere tus archivos de material. Puedes compartir **solo una carpeta**.
- **IA local** (Ollama, LM Studio…) elegida según tu RAM; si tu equipo no puede, usa la IA de otro equipo de tu red. Sin APIs ni suscripciones.

**Autor:** Hector Martinez · [www.oweeme.com](https://www.oweeme.com) · hector@oweeme.com

## ☕ Apoya el proyecto
OweeStudent es gratis. Si te ayuda a estudiar, puedes colaborar con una donación: **[paypal.me/oweeandme](https://www.paypal.com/paypalme/oweeandme)**. ¡Gracias!

## Instalar (sin permisos de administrador)

| Sistema | Archivo de [Releases](../../releases) | Cómo |
|---|---|---|
| **Linux** | `OweeStudent-X-linux-x86_64.tar.gz` | Descomprime y ejecuta `./install.sh` (instala en `~/.local`) |
| **Debian/Ubuntu** | `oweestudent_X_amd64.deb` | `sudo apt install ./oweestudent_X_amd64.deb` (este sí requiere root) |
| **Linux (un archivo)** | `OweeStudent-X-x86_64.AppImage` | `chmod +x` y doble clic; no instala nada. Necesita `libmpv2` del sistema |
| **Windows** | `OweeStudent-X-windows-setup.exe` | Doble clic (instala por usuario). Si SmartScreen avisa: «Más información → Ejecutar de todas formas» (el instalador no está firmado) |
| **macOS** | `OweeStudent-X-macos-arm64.zip` (Apple Silicon) o `-x86_64.zip` (Intel) | Descomprime y arrastra la app a Aplicaciones. Sin firmar: la primera vez, clic derecho → Abrir |
| **Android** | `OweeStudent-X-android.apk` | Ábrelo y permite «instalar apps desconocidas». *Experimental* (ver abajo) |

iOS no se publica (requiere cuenta de Apple Developer). Flathub: hay un borrador en `packaging/flatpak/` (aún sin probar; necesita un módulo `mpv`).

## IA ligera con un botón (opcional)
**Ajustes → «✨ Activar IA»**: la app mira qué hay en tu equipo y hace lo más corto, sin terminal:
1. Si ya hay un servidor de IA funcionando (Ollama, LM Studio, llama.cpp, Jan), lo usa tal cual y elige el modelo más ligero: no descarga nada.
2. Si tienes Ollama instalado pero apagado, lo enciende y, si no tiene modelos, baja uno ligero según tu RAM.
3. Si no hay nada, instala la IA integrada: un motor de ~20 MB (`llama.cpp`) y un modelo pequeño, elegido según tu RAM
(usa hasta el 10 %, ajustable): 4 GB → Qwen 0,5B (~0,5 GB), 16 GB → 1,5B (~1,1 GB), 32 GB → 3B (~2,1 GB).
Se descarga una sola vez (se reanuda si se corta), se enciende sola al usarla y se apaga a los 2 minutos para liberar RAM.
No existe en Android/iOS (no permiten ejecutar programas descargados): allí se usa la IA de tu PC (*Opciones avanzadas → Buscar en mi red*, requiere Ollama en el PC con `OLLAMA_HOST=0.0.0.0`).
En Linux necesita `libgomp1` y `libssl3` (casi siempre ya instaladas; si faltan, la app te dice el comando exacto).
Sin IA también puedes usar «Copiar prompt» con tu chat favorito (Claude, ChatGPT…) y pegar la respuesta al importar.

## Mis estudios (carpetas → estudio → todo lo suyo)
La barra principal es **Hoy · Estudios · Repaso · Más**. **Estudios** muestra tus carpetas (Máster, Idiomas, Programación…) con sus estudios, el avance de cada uno y el siguiente tema.
Al entrar en un estudio, todo queda dentro de él, con pestañas: **Temario · Material · Estudiar · Repaso**. El Material (PDF, Word, Excel, imágenes, enlaces), el Pomodoro, tus apuntes y las tarjetas son de ESE estudio.
**Aprende Owee → pestaña «Escritura»**: escribe en Owee Script sin instalar nada. Un teclado de las 56 sílabas, vocales y números dibuja tu texto en glifos (o escribe en romano y se convierte), y puedes copiar el resultado. El modo **Artículo** te deja escribir un texto largo en Owee, por secciones (introducción, argumentos, conclusión), con vista en escritura Owee, y **valorarlo**: palabras que no se pueden escribir en Owee, palabras fuera del léxico, variedad y hasta qué nivel del curso llega tu vocabulario. La *Práctica* te da rondas de 5 palabras del curso (escribir el significado, copiar un glifo, leer un glifo); lo que falles vuelve en «Repaso».
La flecha ← de la cabecera vuelve a «Estudios» para elegir otro. **Aprende Owee** es un estudio más (con su pestaña extra «Curso») y siempre queda al final. «Repaso» de la barra reúne las tarjetas de todos tus estudios.
Si adjuntas en *Material* un archivo con módulos y temas (md, txt, pdf, docx), la app ofrece **Crear el plan**.

## Estudiar sin perder el hilo
- **Hoy → «Tu sesión de hoy»**: qué hacer ahora, en orden (repasos, siguiente tema, seguir leyendo) y un botón **▶ Empezar ahora** que arranca el Pomodoro.
- **Pomodoro que no se detiene**: sigue corriendo al cambiar de pantalla y se ve en una franja arriba (cuenta atrás, línea de avance, pausa y stop).
- **Material** (pestaña de cada estudio): además de archivos (PDF, Word, Excel, CSV, texto, **imágenes**), puedes añadir **enlaces**; al tocarlos se abren en tu navegador. Los documentos y las imágenes se leen dentro de la app.
- **Flecha ← Atrás** arriba en todas las pantallas; las pestañas principales (Hoy, Estudios, Repaso, Más) empiezan de nuevo.
- El curso y el glosario de Owee se regeneran desde el repositorio del idioma con `tools/owee_curso.py` y `tools/owee_sincronizar.py`.

## Créditos
La lengua Owee (glosario y léxico) es de Hector Martinez, CC BY-SA 4.0; la fuente Owee Sans (`assets/fonts`) es SIL OFL 1.1 (texto junto a ella); el conversor romano ↔ escritura se adapta de su código MIT.

## Datos y privacidad
- Antes de actualizar la base de una versión anterior y antes de cada sincronización, la app guarda una copia en `~/.oweestudent/respaldos/` (las últimas 5 de cada tipo).
- La búsqueda de «Preguntar» guarda un índice de tus archivos en `~/.oweestudent/indice.db` (puedes borrarlo: se rehace solo).
- Tus datos viven en `~/.oweestudent/estudios.db` (Windows: `%USERPROFILE%\.oweestudent`). No sale nada de tu equipo.
- La clave de perfil protege la app, **no cifra el archivo**: para eso cifra el disco del sistema.
- La sincronización usa HTTP en tu red local con un PIN de un solo uso (5 min, se cierra tras 5 intentos fallidos). Úsala en tu red de casa, no en Wi-Fi público. Al compartir una carpeta no viajan tus claves ni el resto de tu estudio.

## Limitaciones conocidas
- **Móvil y tablet:** la interfaz se adapta (barra inferior bajo 700 px de ancho, lateral en pantallas grandes; diálogos y campos caben en 375 px), pero lo verifiqué emulando el tamaño del móvil en el navegador, no en dispositivos reales. No hay **notificaciones push**: Flet 0.28 no las ofrece; usa el archivo `.ics` de «Entregas y exámenes» con el calendario del teléfono. En Android, las exportaciones (Anki, escritos, copias) se guardan en la carpeta privada de la app: para sacarlas, usa el modo web desde el PC (`--web`) o sincroniza con el ordenador.
- **Android es experimental:** la sincronización y la IA por red usan sockets de Python y deberían funcionar, pero falta confirmarlo en más dispositivos. Alternativa: en el PC, Sincronizar → «Usar en el móvil sin instalar nada» y abre la app en el navegador del móvil.
- Escanear el QR con la cámara *dentro* de la app no está disponible (Flet 0.28 no incluye lector); se sustituye por buscar equipos por nombre + PIN. El QR lleva un enlace propio (`oweestudent://sync/…`) que, si Android lo abre desde la cámara, conecta solo: **experimental, sin confirmar en dispositivos reales**.
- Si el móvil no encuentra al PC: casi siempre es el **cortafuegos del PC** bloqueando conexiones entrantes (Deepin/ufw: `sudo ufw allow 8765/tcp`). Prueba al revés (permitir en el móvil, buscar desde el PC) o usa «Conectar por IP» → «Probar conexión», que explica el motivo.
- Los archivos de material viajan del equipo que comparte al que recibe; un archivo que solo tiene el equipo que recibe no se envía de vuelta.
- DOCX no está disponible en Android.
- La mezcla usa la hora de cada equipo: si los relojes difieren mucho, «el más reciente» puede fallar.

## Aprender más rápido y aplicar lo aprendido
- **Tarjetas con huecos** (`La {{fotosíntesis}} ocurre en los {{cloroplastos}}`: una tarjeta por hueco, como los «cloze» de Anki) y **huecos automáticos** sobre las palabras clave de tus apuntes.
- **Tarjetas de producción:** en el repaso *escribes* la respuesta (vocabulario, Owee…); la app ignora mayúsculas y tildes, avisa si fue una errata y te sugiere la nota.
- **Puntos débiles** («Más → Práctica activa → Puntos débiles»): los temas y las tarjetas que más fallas, a partir de tus repasos y prácticas, y un **refuerzo** (simulacro solo con lo que fallas).
- **Retos prácticos:** cada tema puede tener un reto de aplicación con criterios que tú compruebas y una evidencia (qué hiciste, qué aprendiste). Plantillas por tipo, o propuesto por la IA con tu material.
- **Sprints de 7 días** sobre un tema: explorar → entender → practicar → fijar → recordar → probarte → corregir. «Hoy» te muestra el paso que toca y cada paso abre la pantalla correspondiente.
- **Resumen para la familia o el docente** («Métricas»): cifras y títulos de la semana, sin el contenido de tus notas; lo copias o lo guardas tú.
- **Copia de seguridad** («Ajustes»): todo tu estudio (y tus archivos de material) en un `.zip`, y restauración con copia automática previa.
- **Avisos en tu calendario** («Entregas y exámenes»): un archivo `.ics` con tus entregas (aviso el día antes y el mismo día) y un repaso diario a la hora que elijas. La app no manda notificaciones por sí sola; tu calendario sí.

## Para el colegio y para escribir
**Estudiantes de colegio:** el nivel del perfil (primaria, secundaria, adolescente, universitario, adulto) ajusta la app: bloques de estudio más cortos (15 min en primaria), simulacros más breves, un Feynman «para alguien de 8 años» y menos horas propuestas por el asistente; la gestión de lecturas de investigación solo aparece desde la universidad. **«Más → Entregas y exámenes»** guarda tareas, exámenes y proyectos con su fecha: lo urgente sale en «Hoy», y el asistente crea el examen con su fecha cuando le das una fecha límite. Se puede compartir una carpeta con un compañero o docente por la sincronización.

**«Más → Escritor (monografías, tesis, libros)»:** armas un escrito por secciones (monografía, ensayo, tesis o libro) con su esqueleto y una guía de qué va en cada parte, meta de palabras por sección y ritmo diario hasta tu fecha límite. Citas con `[@clave]` (o `[@clave, p. 12]`): la app las convierte a autor-año tipo APA o a numéricas y arma la lista de referencias solo con lo que citaste; las citas sin lectura registrada se avisan. «Fuentes para esta sección» busca pasajes en tus archivos, notas y fichas; con IA, «Borrador con IA» redacta un borrador usando solo esas fuentes (y solo cita las que tienes en «Lecturas»); «Revisar redacción» avisa de frases y párrafos muy largos, párrafos sin cita y repeticiones. Exporta a Word, HTML (para imprimir a PDF) o Markdown.

## Práctica activa y exportar a Anki
**«Más → Práctica activa»** (tres formas de estudiar que fijan más que releer):
- **Recuperación libre:** escribes de memoria todo lo que recuerdas de un tema, y la app lo compara con tus tarjetas, una página de tus archivos, la ficha de una lectura o un texto que pegues: muestra qué palabras clave mencionaste y cuáles te faltaron. Con IA además lista lo que falta y lo que contradice la referencia (siempre usando solo ese texto). Te autoevalúas (0–5) y se programa el repaso.
- **Explícalo (Feynman):** explicas el tema «a alguien de 12 años». Sin IA revisa la longitud, las frases muy largas y las palabras técnicas sin explicar; con IA actúa como un niño curioso y te hace preguntas.
- **Simulacro:** un examen cronometrado con tus propias tarjetas (opción múltiple con distractores sacados de tus otras tarjetas, respuesta abierta o mixto). Al terminar ves la nota, los errores con su respuesta correcta, y cada tarjeta fallada vuelve a tu repaso. Queda un historial de tus prácticas.

**«Más → Exportar a Anki»:** exporta todo tu estudio, una asignatura o un tema como paquete **.apkg** (un mazo por asignatura, con tu progreso de repaso si quieres) o como **CSV**. Comprobado con la biblioteca oficial de Anki; las tarjetas de Owee llevan la fuente Owee Sans dentro del paquete. Si exportas de nuevo, Anki actualiza las tarjetas en vez de duplicarlas. Los archivos quedan en `~/.oweestudent/exportaciones/`.

## Lecturas y preguntas a tus documentos (investigación)
**«Más → Lecturas (investigación)»**: tu cola de lectura por asignatura (por leer · leyendo · leída) con una **ficha** por texto (pregunta de investigación, método, hallazgos, limitaciones, cómo te sirve, cita clave), etiquetas, prioridad y un archivo adjunto. **Importa BibTeX** (Zotero, Mendeley, Google Scholar), exporta BibTeX y las fichas en Markdown, y convierte una ficha en tarjetas de repaso. Las lecturas se sincronizan entre tus equipos.

**«Más → Preguntar a mis documentos»**: escribes una pregunta y la app busca en tus archivos (PDF, Word, Excel, texto), tus notas y tus fichas, y te muestra los pasajes más relevantes con su **fuente (documento y página)** y un botón para abrir esa página. Si tienes una IA configurada, además redacta la respuesta **solo con esos pasajes y citándolos** ([1], [2]…); la app descarta las citas que no existen y avisa si la IA no citó nada. La búsqueda es local (BM25, sin enviar nada a internet); el índice se guarda en `indice.db` junto a tu base y no se sincroniza. La primera pregunta prepara el índice de cada archivo (una sola vez). Límites: busca por palabras (usa las del texto) y no lee escaneos sin texto.

## Asistente de objetivo
«Más → Asistente de objetivo»: eliges qué quieres lograr (**asignatura o examen**, **idioma** con niveles MCER, **tecnología** o **maestría/doctorado**), cuentas tu situación y la app arma un plan con fases, fechas repartidas por meses y un cronograma semanal con tus horas reales. Antes de crearlo te dice si el tiempo te alcanza (y cuántas horas por semana o meses harían falta). Las plantillas ponen la **estructura**; no inventan el contenido de la materia (para una asignatura pegas tu temario). Las horas por idioma son orientativas.

## Aprende Owee (curso del idioma)
Es **opcional**: tu estudio propio va siempre primero. Mientras no tengas uno, «Hoy» te guía a crear tu plan con el asistente o importar el que ya tengas, y ofrece el curso como una opción más; cuando ya tienes tu estudio, ese es el que se abre y manda en «Hoy», y el curso queda como un recordatorio discreto al final (si lo añadiste).

«Más → Aprende Owee»: las 35 lecciones de los niveles 0–3 con glifos, romanización, vocabulario por parte, traducción oculta («tapa la traducción e intenta entender») y ejercicios con respuestas. Puedes añadir el curso a tu plan (carpeta «Owee»: un nivel por unidad, una lección por tema) y crear **por lección** tarjetas de glifos (vocales, 56 sílabas, dígitos) y de vocabulario (en los dos sentidos) para repasarlas con el resto. Las tarjetas guardan solo texto latino con una marca; los glifos se dibujan al mostrarlas. Se regenera con `python tools/owee_curso.py /ruta/a/owee`.

## Traducir la app
**Owee:** `python tools/owee_sincronizar.py /ruta/a/owee` regenera `i18n/catalogos/qow.py` desde `08_Integracion/datos/ui_glosario.tsv` del [repositorio de Owee](https://github.com/oweeme/owee). Nunca inventa palabras: añade términos al glosario (flujo PROPUESTA → APROBADA) y vuelve a ejecutarlo; `tests/test_owee.py` comprueba que todo lo que dice la app en Owee es vocabulario aprobado y sílabas V/CV. El texto se guarda siempre en romano; los glifos solo se usan para mostrar.

Los textos están en español dentro del código: `t("Guardar")`, `tn(n, "{n} día", "{n} días")` (plurales) y `marcar("Lunes")` (listas que se traducen después). Cada idioma es un diccionario `{texto en español: traducción}` en `i18n/catalogos/<código>.py` (copia `en.py`). Para ver qué falta:
```bash
.venv/bin/python -m i18n.extraer
```
Las pruebas (`tests/test_i18n.py`) fallan si falta un texto, si una traducción pierde una `{variable}` o si un plural no es una tupla de formas.

## Desarrollo y prueba en local
Antes de publicar nada, prueba la app en tu equipo (no toca tus datos reales si usas una base de prueba).

```bash
# 1) Entorno. Si falla con «ensurepip is not available» (Debian/Ubuntu): borra la carpeta a medias con  rm -rf .venv  y elige UNA:
#    a) con sudo:     sudo apt install python3-venv   y repite el comando de abajo
#    b) sin sudo:     uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt pytest ruff
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest ruff

# 2) Comprobaciones (≈ 40 s). Son las mismas que corre el CI
.venv/bin/ruff check .
.venv/bin/python -m pytest -q

# 3) Ejecutar la app con DATOS DE PRUEBA (tu estudio real queda intacto)
OWEE_DB=/tmp/owee-prueba.db FLET_APP_STORAGE_DATA=/tmp/owee-prueba .venv/bin/python main.py          # ventana de escritorio
OWEE_DB=/tmp/owee-prueba.db FLET_APP_STORAGE_DATA=/tmp/owee-prueba .venv/bin/python main.py --web    # servidor en http://localhost:8550

# 4) Ver cómo queda en el móvil o la tablet: con --web, abre  http://IP-DE-TU-PC:8550  en su navegador (mismo Wi-Fi;
#    si no abre, puerto 8550 en el cortafuegos: sudo ufw allow 8550/tcp). En el navegador del PC, F12 → modo dispositivo.
```
Sin las variables `OWEE_DB`/`FLET_APP_STORAGE_DATA` la app usa tu base real en `~/.oweestudent/`. Las pruebas automáticas nunca la tocan.

**Atajo:** `./run-local.sh` (o `./run-local.sh --web`) hace todo lo del paso 3 y además resuelve el error `libmpv.so.1: cannot open shared object file` del cliente gráfico de Flet en distribuciones nuevas (que traen `libmpv.so.2`): crea un enlace en `~/.local/lib/owee`. Si no tienes libmpv: `sudo apt install libmpv2`.

**Instaladores en tu equipo** (opcional; el CI los crea solos al publicar una versión):
```bash
.venv/bin/pip install pyinstaller
.venv/bin/flet pack main.py --name OweeStudent -D -y -i assets/icon_256.png --add-data "assets:assets"     # Linux (en Windows: "assets;assets" e icon.ico)
./dist/OweeStudent/OweeStudent                                                                            # probar el binario empaquetado
```
Android (`flet build apk`) necesita Flutter y el SDK de Android: es más cómodo dejar que lo haga GitHub Actions.

**Lista antes de subir a GitHub:** ruff y pruebas en verde · abrir la app con datos de prueba y recorrer «Hoy», «Más» y «Ajustes» · en «Ajustes → Idioma» cambiar de idioma · exportar una copia de seguridad y restaurarla · `git status` sin archivos raros (nada de `.db`, `config.json` ni `exportaciones/`; el `.gitignore` ya los excluye).

Linux empaquetado: el lanzador (`packaging/linux/launcher.sh`) enlaza `libmpv.so.2` como `libmpv.so.1` y, si la app no abre, muestra el motivo y lo guarda en `~/.local/share/oweestudent/ultimo-error.log`. En cada compilación se prueba en un Debian 12 limpio (`packaging/linux/smoke.sh`).
El icono se genera con `tools/gorro.py` (logo de Oweeme + gorro).
Publicar: sube la versión en `app_info.py` y haz `git push` a `main` → GitHub Actions compila, crea la etiqueta `vX.Y.Z` y adjunta los instaladores a la Release (si esa versión ya existe, no la repite).


---
Licencia [MIT](LICENSE). © 2026 Hector Martinez — [www.oweeme.com](https://www.oweeme.com)
