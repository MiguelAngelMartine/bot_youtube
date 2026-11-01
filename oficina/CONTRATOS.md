# Contratos entre fases

Todo vive en `dia/AAAA-MM-DD/`. Cada puesto **solo escribe sus ficheros** y lee los de las fases anteriores.

## Fase 0
**`correcciones.md`** (Fe de erratas). Si no hay nada, una línea: `SIN CORRECCIONES`. Si hay algo:
```
## Corrección 1
Dijimos (episodio AAAA-MM-DD, bloque N): "<frase exacta>"
Ahora sabemos: <hecho nuevo> — Fuente: <medio>, <enlace>
Propuesta de texto para Urni: "<1-2 frases neutrales>"
```

**`contexto.md`** (Documentalista): historias en curso con su estado anterior y personas con su cargo verificado.

## Fase 1
**`noticias.json`** (lo escribe `recopila.py`): `[{medio, titular, resumen, enlace, hora}]`.

**`temas.json`** (Recopilador):
```json
[{"id": "urda", "tema": "Accidente de Urda: investigación", "resumen": "2-3 frases",
  "medios": ["El País", "ABC", "..."], "n_medios": 7,
  "noticias": [{"medio": "El País", "titular": "...", "enlace": "..."}]}]
```
Ordenado de más a menos medios. Solo política española y sus consecuencias (no deportes, sucesos sin dimensión política, horóscopos...).

**`dossier/<id>.md`** (Investigador), con estas secciones:
- `# Tema`
- `## Hechos`: cada uno con `[CONTRASTADO: medio1, medio2]` o `[ATRIBUIDO: medio]` y el enlace.
- `## Versiones`: Gobierno / oposición / socios / otros, con citas literales entre «» y quién las dijo, con su cargo.
- `## Cifras`: número, qué mide y la fuente.
- `## Contexto`: antecedentes, con fuente.
- `## Qué pasa ahora`: próximos pasos con fecha, con fuente.
- `## Dudas y contradicciones`: lo que los medios cuentan distinto.

## Fase 2
**`escaleta.json`** (Jefe de edición):
```json
{"fecha": "Domingo, 1 de noviembre de 2026", "titulo_video": "≤ 70 caracteres",
 "bloques": [{"n": 1, "id": "urda", "titulo": "≤ 45 caracteres", "tono": "normal|sobrio",
              "segundos": 90, "enfoque": "qué contar y por qué", "imprescindible": ["hecho 1", "versión X"]}],
 "breves": [{"id": "...", "titular": "...", "segundos": 15}],
 "correccion": true}
```

## Fase 3
**`bloques/NN.json`** (Redactor, NN = 01, 02...; los breves van juntos en el último). Es una sección con el formato de `episodio.json`:
```json
{"titulo": "...", "tono": "normal", "fuentes": ["..."],
 "pasos": [{"di": "texto que lee Urni", "ve": {"tipo": "...", "...": "..."}}]}
```

## Fase 4
**`revision/verificacion.md`**, **`revision/neutralidad.md`** y **`revision/cumplimiento.md`**: una sección por bloque con el veredicto `APTO` o `CORREGIR`. Cada problema va con la frase exacta y el cambio propuesto.

## Fase 5
**`episodio.json`** (Editor de cierre): `{fecha, titulo_video, secciones: [sumario, (corrección), bloques..., breves con la despedida]}`.

**Fotos** (Editor gráfico): `imagenes/sN_M.jpg`, `creditos.json` (`{fichero: {titulo, url, autor, licencia, pagina, fuente}}`) y el campo `foto` en las escenas de `episodio.json`.

## Fase 6
- **`episodio.mp4`**, **`episodio.srt`**, **`episodio_descripcion.txt`**, **`escenas.json`** (los escribe `episodio.py`); log en `render.log`.
- **`calidad/informe.md`** (Control de calidad): `APTO` o `CORREGIR`, con la lista de problemas y el segundo exacto.
- **`miniatura.png`** (Diseñador gráfico): 1280x720.

## Fase 7
- **`publicacion.md`** (Editor de plataforma): título, descripción, etiquetas, hashtags, comentario fijado, categoría y lista de comprobación de YouTube Studio.
- **`parte_del_dia.md`** (Jefe de producción): qué entró, qué se cayó y por qué, vueltas de la mesa de control, duración y avisos.

## Archivo (fuera de los días)
- **`archivo/historias.json`**: `[{id, titulo, desde, ultimo_dia, estado: "abierta|cerrada", resumen_ultimo}]`
- **`archivo/personas.json`**: `{"Óscar Puente": {"cargo": "Ministro de Transportes", "partido": "PSOE", "fuente": "...", "fecha": "..."}}`
- **`archivo/correcciones.md`**: el historial de erratas publicadas.
