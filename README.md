# 🎓 OweeStudent

Plan de estudios + repaso espaciado (**FSRS**) + IA **local opcional**, para estudiantes y autodidactas.

- Importa planes en **MD, TXT, PDF, DOCX, XLSX** (o pega texto): detecta módulos, temas, libros, enlaces, entregables e idiomas.
- **Tarjetas de repaso** hechas de *tus* apuntes (con o sin IA) y repaso con FSRS.
- Pomodoro, metas semanales, racha, retención y proyección de fin.
- **Perfiles con clave** opcional (varios usuarios: tú, un familiar…).
- **Sincroniza entre equipos por QR** (Wi-Fi local): mezcla los cambios de ambos, gana el más reciente.
- **IA local** (Ollama, LM Studio…) elegida según tu RAM; si tu equipo no puede, usa la IA de otro equipo de tu red. Sin APIs ni suscripciones.

**Autor:** Hector Martinez · [www.oweeme.com](https://www.oweeme.com) · hector@oweeme.com

## ☕ Apoya el proyecto
OweeStudent es gratis. Si te ayuda a estudiar, puedes colaborar con una donación: **[paypal.me/oweeandme](https://www.paypal.com/paypalme/oweeandme)**. ¡Gracias!

## Instalar (sin permisos de administrador)

| Sistema | Archivo de [Releases](../../releases) | Cómo |
|---|---|---|
| **Linux** | `OweeStudent-X-linux-x86_64.tar.gz` | Descomprime y ejecuta `./install.sh` (instala en `~/.local`) |
| **Debian/Ubuntu** | `oweestudent_X_amd64.deb` | `sudo apt install ./oweestudent_X_amd64.deb` (este sí requiere root) |
| **Windows** | `OweeStudent-X-windows-setup.exe` | Doble clic (instala por usuario). Si SmartScreen avisa: «Más información → Ejecutar de todas formas» (el instalador no está firmado) |
| **Android** | `OweeStudent-X-android.apk` | Ábrelo y permite «instalar apps desconocidas». *Experimental* (ver abajo) |

macOS e iOS: aún no se publican (requieren compilar en un Mac y cuenta de Apple Developer).

## IA local (opcional)
Instala [Ollama](https://ollama.com/download), abre la app → **Ajustes → «Instalar IA recomendada para mi RAM»**.
Usa por defecto el 10 % de tu RAM (ajustable): 4 GB → `qwen2.5:0.5b`, 16 GB → `1.5b`, 32 GB → `3b`.

## Datos y privacidad
- Tus datos viven en `~/.oweestudent/estudios.db` (Windows: `%USERPROFILE%\.oweestudent`). No sale nada de tu equipo.
- La clave de perfil protege la app, **no cifra el archivo**: para eso cifra el disco del sistema.
- La sincronización usa HTTP en tu red local con una clave de un solo uso (5 min). Úsala en tu red de casa, no en Wi-Fi público.

## Limitaciones conocidas
- **Android es experimental:** Android bloquea por defecto las conexiones HTTP sin cifrar, así que la sincronización y la IA por red pueden no funcionar en el APK; alternativa: en el PC, Ajustes → «Usar en el móvil» y abre la app en el navegador del móvil.
- DOCX no está disponible en Android.
- La mezcla usa la hora de cada equipo: si los relojes difieren mucho, «el más reciente» puede fallar.

## Desarrollo
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt pytest
.venv/bin/python -m pytest        # pruebas
.venv/bin/python main.py          # ejecutar
.venv/bin/python main.py --web    # servir la app por Wi-Fi
```
Linux: si falta `libmpv.so.1`, `ln -s /usr/lib/x86_64-linux-gnu/libmpv.so.2 ~/.local/lib/libmpv.so.1` y `LD_LIBRARY_PATH=~/.local/lib`.
Publicar: `git tag v0.1.0 && git push --tags` → GitHub Actions compila y adjunta los instaladores a la Release.


---
© 2026 Hector Martinez — [www.oweeme.com](https://www.oweeme.com)
