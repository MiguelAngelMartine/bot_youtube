# Instrucciones para Claude en bot_youtube (*El Hoyformativo*)

## Guía única (19-nov-2026, decisión del usuario: «solo tiene que haber una guía para todo, unificada y siempre actualizada»)
- **Todas las normas del canal están en [`NORMAS.md`](NORMAS.md)**: veracidad, neutralidad, guion y voz, formatos, imagen,
  monetización, derechos y proceso. Léela antes de trabajar en guiones, imágenes o vídeos. La siguen igual Claude, los agentes
  de `.claude/agents/` (cada uno lo dice en su cabecera), Gemini/freellmpool (`agente_gemini.COMUNES`, `jornada.comunes`) y
  los scripts. Si algo la contradice, manda `NORMAS.md`.
- **Cada decisión nueva del usuario se escribe en `NORMAS.md` en el mismo cambio** (y su fecha de «Última actualización»),
  sustituyendo lo que quede viejo, y se revisa que ningún agente ni prompt diga lo contrario. Si conviene dejar constancia del
  porqué, una línea con la fecha en `oficina/HISTORIAL_DECISIONES.md` (historia, no normas). Nunca se vuelven a crear guías
  paralelas (`LIBRO_DE_ESTILO.md` y `GUION_ESTILO.md` se fundieron en `NORMAS.md`).
- Anexos técnicos: `oficina/CONTRATOS.md` (ficheros entre fases y catálogo de escenas), `oficina/EJEMPLOS_GANCHOS.md`,
  `archivo/palabras_vetadas.json`, `archivo/coletillas_evitar.txt`.

## Cómo trabajar con el usuario
- **Responder siempre en español.**
- **Sincronizar git siempre:** tras cualquier cambio de código o de la guía, commit + push a `origin/main`
  (github.com/MiguelAngelMartine/bot_youtube). Esta copia de trabajo ES el servidor (hostname `server`), así que no hace falta
  `git pull` aparte. Los commits terminan con `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- **Nunca mostrar secretos:** ni leer `.env`, `client_secret.json` ni `token_youtube.json`. Las claves de Telegram están en el
  `.env` de `../kraken-futures-bot`; solo `notifica.py` las lee.
- **Informar sin que pregunte:** en las tareas largas (renders, jornadas), avisar al terminar, también si falla. Por Telegram
  (`notifica.py`), en lenguaje llano.
- **Revisar antes de entregar:** mirar los fotogramas de cada escena antes de mandar un vídeo; no darlo por bueno sin verlo.
- **Publicación automática** (27-nov-2026, sustituye al OK previo del 21-nov): la jornada sube sola el largo y los
  Shorts, privados y programados en sus franjas (NORMAS.md), y avisa por Telegram; el usuario puede pedir que se pare
  antes de la hora. Antes de rehacer algo, comprobar en YouTube si ya está
  publicado: lo publicado no se toca.
- Las búsquedas web sencillas se pueden delegar en un ayudante barato; el diseño, el análisis y los cambios de código, nunca.
- No proponer de nuevo lo que el usuario ya descartó (está en `oficina/HISTORIAL_DECISIONES.md`): ritmo «TikTok» de cortes
  en los Shorts, LTX, caricaturas IA, voces de OpenAI/ElevenLabs, voz propia o clonada, estilo tablero, fondos borrosos.

## Mapa técnico (dónde está cada cosa)
- **Jornada:** cron del servidor → `jornada.sh lanza --si-hora 10` (10:30 Madrid) → `jornada.py` (fases con programas y
  Gemini en cada puesto; Opus para escaleta, guiones y Shorts; Claude de respaldo). Si no termina, `claude -p
  "/edicion-diaria"` retoma (`.claude/skills/edicion-diaria/`). `jornada.sh vigila --si-hora 14` avisa si no hay vídeo.
  Consumo en `archivo/consumo.tsv`; objetivo ≤ 8 % semanal del plan de Claude.
- **Recogida:** `recopila.py`, `temas.py`/`temas_gemini.py`, `investiga.py` (dossieres con Gemini), `redes.py`,
  `x_oficiales.py` (lista cerrada de cuentas comprobadas, cookies en `.env`), `ganchos.py`.
- **Guion:** agentes de `.claude/agents/`, `prechequeo.py`, `coletillas.py`, `shorts_guion.py` (`repeticiones`),
  `prevuelo_voz.py` + `voz_calidad.py` (control de calidad de voz y guion, local y gratis). LLM: `gem.py` (Gemini, dos claves) → freellmpool (`~/.local/bin/freellmpool`) → Claude.
- **Voz:** `voz.py` (Azure Tristán HD, caché en `cache/voz`, Whisper para tiempos). Clave con `clave_azure.py`.
- **Montaje (formato «presentador», SIEMPRE desde el 20-nov-2026):** `presentador.py <fecha> largo|N` con SOLO las imágenes
  de `Imagenes/` (`Fondos`, `Presentador`, `Políticos`; las amplía el usuario; `presentador.py catalogo` las lista) y
  `musica.py`. Descartado hasta nueva orden: `render_ambiente.py`, `ia_vinetas.py`, `motion_comic.py`,
  `biblioteca_ambiente.py`, `fotos.py`, `biblioteca_fotos.py` (siguen en el repo, sin usarse). Miniatura: `miniatura_auto.py`, `imagen_fondo.py`, `miniatura.py`, `director_arte.py`.
- **Publicación:** `subir.py <fecha> [shorts]` (privado; `autorizar` si caduca el token), `descripcion.py`,
  `plataforma.py`, `apto_anuncios.py`, `comenta.py` (cron horario), `notifica.py`, `analitica.py`, `informe_semanal.py`.
- **Pendientes conocidos:** consulta con un abogado de propiedad intelectual antes de monetizar; avatar y banner EH a mano;
  «Vídeo relacionado» de los Shorts y fijar comentarios, sin API (no se pueden automatizar); TikTok aparcado (solo API oficial, en borrador).
