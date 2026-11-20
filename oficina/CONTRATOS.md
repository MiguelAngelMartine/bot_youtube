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
- `## Cruce de declaraciones` (si lo hay): ataque → respuesta, con citas literales, quién, cargo, fecha y medio.

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
 "pasos": [{"di": "texto que lee la voz", "ve": {"tipo": "...", "...": "..."}}]}
```

## Fase 4
**`revision/verificacion.md`**, **`revision/neutralidad.md`** y **`revision/cumplimiento.md`**: una sección por bloque con el veredicto `APTO` o `CORREGIR`. Cada problema va con la frase exacta y el cambio propuesto.

## Fase 5
**`episodio.json`** (Editor de cierre): `{fecha, titulo_video, secciones: [sumario, bloques..., breves, (corrección al final, desde el 7-nov-2026)]}`; la despedida, último paso de la última sección.

**Fotos** (Editor gráfico): `imagenes/sN_M.jpg` y `imagenes/retrato_<apellido>.jpg`, `creditos.json` (`{fichero: {titulo, url, autor, licencia, pagina, fuente, persona?}}`; `persona` marca el retrato de esa persona) y el campo `foto` en las escenas de `episodio.json`.

## Fase 6
- **`episodio.mp4`**, **`episodio.srt`**, **`episodio_descripcion.txt`**, **`escenas.json`** (los escribe `largo.py`; `episodio.py`, el estilo anterior, escribe los mismos); log en `render.log`.
- **`calidad/informe.md`** (Control de calidad): `APTO` o `CORREGIR`, con la lista de problemas y el segundo exacto.
- **`miniatura.png`** (Diseñador gráfico): 1280x720, estilo de `canal/miniatura_referencia.png`. Sus fotos (`imagenes/miniatura_<apellido>.jpg`, y `miniatura_fondo.jpg` si hizo falta) quedan con su crédito en `creditos.json`; el recorte se guarda como `<foto>_recorte.png`.

## Fase 7
- **`publicacion.md`** (Editor de plataforma): título, descripción, etiquetas, hashtags, comentario fijado, categoría y lista de comprobación de YouTube Studio.
- **`parte_del_dia.md`** (Jefe de producción): qué entró, qué se cayó y por qué, vueltas de la mesa de control, duración y avisos.

## Archivo (fuera de los días)
- **`archivo/historias.json`**: `[{id, titulo, desde, ultimo_dia, estado: "abierta|cerrada", resumen_ultimo}]`
- **`archivo/personas.json`**: `{"Óscar Puente": {"cargo": "Ministro de Transportes", "partido": "PSOE", "fuente": "...", "fecha": "..."}}`
- **`archivo/correcciones.md`**: el historial de erratas publicadas.

## Anexo: catálogo de escenas del guion (`"ve"` de cada paso)
Formato técnico. Las normas de qué contar y cómo están en `NORMAS.md` (guía única), que manda sobre esto.

Cada escena dura desde el paso donde se pide hasta la siguiente. Los objetos aparecen cuando la voz dice el trozo de `"cuando"`, que debe copiarse **literal** del texto `"di"` (unas 2-4 palabras seguidas).

| tipo | para qué | campos | límites |
|---|---|---|---|
| `sumario` | titulares del día a pantalla completa (solo en el bloque 0) | `items[{texto, cuando, titular, destaca, etiqueta, persona?, foto?}]` | ≤ 4 items; texto ≤ 70 caracteres, titular 2-5 palabras |
| `mapa` | dónde ha pasado | `puntos[{nombre, lon, lat, cuando?, aviso?, pulso?, izq?, abajo?}]`, `ruta?`, `tren?`, `aviso_ruta?`, `titular`, `sub`, `fuente` | ≤ 5 puntos; titular ≤ 40 caracteres |
| `cifra` | el número clave | `numero` (≤ 4 caracteres), `etiqueta`, `sub`, `nota?`, `cuando_nota?`, `fuente` | etiqueta ≤ 28 caracteres |
| `claves` | 3-4 ideas en viñetas | `titulo`, `items[{icono, texto, cuando, escena?, persona_vineta?}]`, `fuente` | ≤ 4 items, ≤ 95 caracteres |
| `cronologia` | qué pasó y cuándo | `titulo`, `items[{hora, texto, cuando, escena?, persona_vineta?}]`, `fuente` | ≤ 4 items, ≤ 90 caracteres |
| `persona` | una persona y su cita | `persona{nombre, cargo, partido, cita?, medio?, cita_cuando?}`, `sello?`, `sello_cuando?`, `flujo?{etiqueta, cuando, a{...}, a_cuando}` | cita ≤ 70 caracteres; sello ≤ 14 caracteres |
| `citas` | 2-3 voces enfrentadas | `titulo`, `items[{nombre, cargo, partido, cita, medio, cuando}]` | ≤ 3 citas, ≤ 110 caracteres |
| `posturas` | quién presiona a quién | `titulo`, `centro{nombre, cargo, partido}`, `presionan[{nombre, partido, cuando}]`, `etiqueta`, `etiqueta_cuando`, `aparte{nombre, partido, texto, cuando}`, `fuente` | ≤ 4 presionan |
| `calendario` | fechas que vienen | `dia`, `mes`, `pie`, `items[{hora, texto, cuando}]`, `fuente` | ≤ 3 items |
| `breve` | noticia corta | `lugar`, `icono`, `titular`, `sub`, `fuente`, `escena?`, `persona_vineta?` | titular ≤ 80 caracteres |
| `despedida` | cierre del vídeo | — | solo en el último paso |

- **Foto de la escena:** las escenas `persona`, `citas`, `claves`, `cronologia`, `cifra` y `breve` admiten `"foto": "sN_M.jpg"`. La elige el editor gráfico; el redactor no la pone. En el tablero sale impresa y pegada, con «Foto de archivo» y el crédito (en `citas` y en `persona` con `flujo` no hay sitio y no sale).
- **Retratos:** las personas de `persona`, `citas` y `posturas` salen en polaroid con el retrato que el editor gráfico marca con `--persona`; si no hay, con sus iniciales.
- **Viñetas** (decisión del usuario del 1-nov-2026, estilo de `canal/estilo_vineta.jpg`): cada item de `claves` y `cronologia`, y el titular de cada `breve`, sale como una viñeta de novela gráfica ilustrada por IA, con el texto arriba en una franja del tono de la viñeta (sin bocadillos). Para pedirla:
  - `"escena"`: en inglés, lo que se ve, concreto y sin texto, en 1 frase (por ejemplo, `"a judge's wooden gavel on a courtroom bench, scales of justice behind"`). Fiel al dato: nada que no haya pasado. No nombres lo que no quieres que salga (si escribes «sin banderas», el modelo las dibuja).
  - `"persona_vineta"` (opcional): el nombre exacto de una persona con nombre propio **solo si la nota cuenta algo que dijo o hizo ella misma** (no lo de su ministerio o su partido). Sale ella dibujada a partir de su foto real.
  - Nunca víctimas, heridos, violencia explícita ni niños identificables. En los bloques sobrios, escenas tranquilas (lugar, objeto, velas).
  - Sin `escena`, la nota sale como antes.
- **Iconos:** vela, persona, documento, reloj, escudo, tren, mazo, altavoz, tienda, grafico, urna, alerta.
- **Partidos y colores definidos:**
  - PSOE, PSC, PP, Vox, Sumar, Frente Amplio, Podemos, PNV, BNG, Junts, ERC, EH Bildu, CC, UPN, SALF, Compromís;
  - UGT, CCOO, Gobierno, Institución, Encuesta.
- **Tono por escenas:** no repetir el mismo tipo de escena dos veces seguidas, y que cada bloque principal use al menos 3 tipos distintos.

### Coordenadas de referencia (lon, lat)
| Ciudad | lon, lat | Ciudad | lon, lat | Ciudad | lon, lat |
|---|---|---|---|---|---|
| Madrid | -3.70, 40.42 | Barcelona | 2.17, 41.39 | Valencia | -0.38, 39.47 |
| Sevilla | -5.98, 37.39 | Bilbao | -2.93, 43.26 | Zaragoza | -0.88, 41.65 |
| Málaga | -4.42, 36.72 | Murcia | -1.13, 37.98 | Valladolid | -4.72, 41.65 |
| A Coruña | -8.41, 43.36 | Santiago | -8.54, 42.88 | Oviedo | -5.85, 43.36 |
| Santander | -3.80, 43.46 | Pamplona | -1.64, 42.81 | Vitoria | -2.67, 42.85 |
| San Sebastián | -1.98, 43.32 | Toledo | -4.02, 39.86 | Córdoba | -4.78, 37.89 |
| Granada | -3.60, 37.18 | Alicante | -0.48, 38.35 | Palma | 2.65, 39.57 |
| Badajoz | -6.97, 38.88 | Salamanca | -5.66, 40.96 | Logroño | -2.45, 42.47 |

Canarias, Ceuta y Melilla quedan fuera del mapa dibujado: en esos casos se usa `claves` o `breve`.

## Anexo: `encargo.json` del director (opcional, `dia/<fecha>/encargo.json`)
- Frase pedida (7-nov-2026): `persona`, `frase`, `tema`, `canal`, `cuenta`, `enlace`, `para` → la comprueba `encargo.py`.
- Shorts: `num_shorts`; `shorts_personas`: `[{"persona", "tema", "mejores_frases": true}]` (con `mejores_frases`, un Short
  por persona con 2-3 frases suyas literales: `shorts_guion.mejores_frases`, campo `frases` en `short_N.json`).
- Día monográfico (20-nov-2026): `"monografico": {"tema", "claves": [...], "instrucciones"}` → `jornada.py` investiga solo
  los temas que casan con `claves` y el jefe de edición hace todos los bloques de ese tema (NORMAS.md §5).
