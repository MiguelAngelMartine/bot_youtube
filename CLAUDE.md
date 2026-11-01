# Instrucciones para Claude en bot_youtube (*Política en Claro*)

## Cómo trabajar con el usuario
- **Responder siempre en español.**
- **Sincronizar git siempre:** tras cualquier cambio de código, commit + push a `origin/main` (github.com/MiguelAngelMartine/bot_youtube). Cuando el proyecto esté en el servidor, también `git pull` allí: local, GitHub y servidor tienen que coincidir. Los commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Nunca mostrar secretos:** las claves de Telegram están en el `.env` de `../kraken-futures-bot`; solo `notifica.py` las lee.
- **Informar sin que pregunte:** en las tareas largas (renders, jornadas), avisar al terminar, también si falla. Por Telegram, en lenguaje llano.
- **Revisar antes de entregar:** mirar los fotogramas de cada escena (control_calidad.py) antes de mandar un vídeo; no darlo por bueno sin verlo.
- Las búsquedas web sencillas se pueden delegar en un ayudante barato; el diseño, el análisis y los cambios de código, nunca.

## Reglas del canal (obligatorias, detalle en NORMAS.md y oficina/)
- **Todo lo que aparece tiene que ser real y contrastado:**
  - cada frase se comprueba contra el texto completo de las noticias, no solo contra los titulares (error real: dar por ausente a una persona que sí aparecía en una entradilla);
  - no inventar detalles («por la mañana» sin fuente);
  - si solo lo cuenta un medio, «según X».
- **Neutralidad:** todas las partes, sin adjetivos propios y con fuentes de todo el espectro. Del vídeo de referencia de TikTok («Te Ahorro el Click») se copia el lenguaje visual, nunca su sesgo.
- **Monetizable:** el riesgo n.º 1 es el «contenido no auténtico» de YouTube, así que hace falta narrativa propia y variedad. Las tragedias van en tono sobrio. Nada de fotos de víctimas ni de medios o agencias.
- **Identidad fija:**
  - canal *Política en Claro*, presentadora **Urni** (la urna);
  - rojo `#C8102E`, amarillo `#F1BF00` y azul noche;
  - logo = silueta de la urna;
  - música propia (musica.py).

## Decisiones ya tomadas por el usuario (no volver a proponer)
- **Voz:** edge-tts es-ES-AlvaroNeural, +14 %, +6 Hz, **sin entonación por contexto** (la probó y la descartó), con pausas naturales de 0,40 s entre frases y 0,24 s en comas largas (`voz.py`, modo «plano»). Prefirió optimizar esta voz antes que una voz propia o clonada.
- **Formatos:**
  - largo horizontal **estilo tablero** (`largo.py`, el mismo lenguaje que el vertical adaptado a 16:9), para YouTube; el estilo anterior con fotos de fondo (`episodio.py`) queda descartado (1-nov-2026);
  - corto vertical estilo tablero (`corto.py`), para Shorts y TikTok.
- **Miniatura** (1-nov-2026): estilo de `canal/miniatura_referencia.png` (`miniatura.py`), hecha para la noticia principal de cada vídeo: foto del tema de fondo, protagonista recortado con filo blanco fino (sin halo) y gesto acorde con la noticia, titular enorme blanco y amarillo-oro con relieve, y etiqueta roja con el hecho. Gancho en la forma, literal en el texto; en tragedias, `--sobrio`. Detalle en `.claude/agents/disenador-grafico.md`.
- **Arranque del vídeo** (1-nov-2026): sin presentación de Urni ni saludo. Empieza directo con el sumario de titulares a pantalla completa (`titulares.py`, mismo lenguaje que la miniatura, con golpe de sonido por titular) y después el golpe de marca (`marca.py`, 2,6 s): barrido, el logo entra y el sobre cae en la urna justo en el golpe de la sintonía, el nombre y la fecha se revelan, y el logo vuela hasta su sitio en la cabecera del primer bloque (sin cortes). El usuario pidió que todo el vídeo tenga acabado profesional y cuidado al detalle.
- **Mascota:** Urni tal como está (diseño A de `prototipo_animado.mascota`); se vieron variantes (plana, profe, chibi, reportera, con compañera) y prefirió la actual.
- **Horario:** se publica por la tarde. La jornada arranca a las 15:00 y el vídeo tiene que estar listo hacia las 16:30.
- **El usuario revisa y publica.** La oficina nunca sube nada a YouTube.

## Estado y pendientes (1-nov-2026)
- Carpeta de trabajo anterior: `../resumen_politico`, se conserva como copia; el proyecto vivo es este.
- **Servidor** (miguel@192.168.1.129, portátil de 2011, Ubuntu + Docker): el 1-nov se pararon todos los contenedores salvo `allweather-market-recorder` para dedicarlo al canal. Plan:
  1. bots de recogida de noticias cada hora;
  2. Claude Code en el servidor lanzando `/edicion-diaria` a las 15:00;
  3. ~~medir si el servidor monta el vídeo a tiempo~~: medido el 1-nov. Al principio tardaba ~31 min por 6 min de vídeo; tras optimizar (4 procesos a la vez, OpenCV, caché de voz y música) tarda **~11 min**.
- **Tipografías:** ahora son las de Windows (Segoe UI, Bahnschrift, Segoe Print), cuya licencia no permite copiarlas al servidor. Hay que pasar a libres (por ejemplo Inter, Barlow Condensed, Caveat) en las dos máquinas.
- **Permisos** de la oficina para trabajar sola (`.claude/settings.json`): pendiente de que el usuario lo cree o lo apruebe.
- **Acabado profesional del vídeo** (pedido el 1-nov): repaso hecho y pendientes ordenados en `oficina/REPASO_ACABADO.md`.
- **Antes de monetizar:** pasar la voz a una opción con licencia comercial (por ejemplo Azure Speech) y una consulta breve con un abogado de propiedad intelectual.
- **Pendiente de mejorar en el corto vertical:** piezas que se solapan en la escena de posturas; biblioteca de escenarios y personajes genéricos dibujados (lo que más engancha en el vídeo de referencia).
