# bot_youtube · *Política en Claro*

Canal diario de política española en YouTube (y Shorts/TikTok), presentado por **Urni**, la urna del canal. Lo produce una **redacción de agentes de Claude Code** y lo revisa y publica una persona (el director).

- **Promesa:** todo lo que aparece es real y está contrastado con medios fiables de líneas distintas; enfoque neutral; cada dato lleva su fuente en pantalla.
- **Formatos:**
  - vídeo largo horizontal de 6-8 min cada tarde (`episodio.py`);
  - 2-3 cortos verticales de 60-90 s en estilo tablero (`corto.py`).
- **Todo es propio o de licencia libre:** animaciones, música, logo y presentadora los genera el programa. Las fotos son de archivo, libres y con crédito.

## Cómo funciona
La redacción está descrita en [`oficina/ORGANIGRAMA.md`](oficina/ORGANIGRAMA.md):
- 15 puestos en `.claude/agents/`, del recopilador al editor de plataforma;
- el jefe de producción, en `.claude/skills/edicion-diaria/`, lanzado con `/edicion-diaria [AAAA-MM-DD]`.

Cada fase deja sus ficheros en `dia/AAAA-MM-DD/`, según [`oficina/CONTRATOS.md`](oficina/CONTRATOS.md). La voz, el estilo y el catálogo de escenas están en [`oficina/LIBRO_DE_ESTILO.md`](oficina/LIBRO_DE_ESTILO.md); las normas de YouTube y de derechos, en [`NORMAS.md`](NORMAS.md).

| Herramienta | Qué hace |
|---|---|
| `recopila.py` | Noticias de las últimas 24 h de 11 medios |
| `voz.py`, `pausas.py` | Locución de Urni (edge-tts) con pausas naturales y tiempo por palabra |
| `musica.py` | Sintonía, fondo y efectos compuestos por el programa |
| `episodio.py` | Vídeo largo horizontal con escenas animadas y fondos de foto |
| `corto.py` | Corto vertical estilo tablero |
| `fotos.py` | Búsqueda de fotos libres (Openverse, Wikimedia) con su crédito |
| `miniatura.py` | Miniatura del episodio; banner y avatar del canal (`--canal`) |
| `control_calidad.py` | Fotogramas, volumen y sincronía para revisar; copia ligera |
| `notifica.py` | Aviso por Telegram al director |
| `edicion.ps1` | Lanza la jornada completa sin abrir VS Code |

## Puesta en marcha
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python episodio.py 2026-10-31        # episodio de ejemplo
.venv\Scripts\python corto.py 2026-10-31 2         # corto vertical del bloque 2
```
Los vídeos, audios e imágenes de `dia/` se regeneran y no se suben al repositorio.
