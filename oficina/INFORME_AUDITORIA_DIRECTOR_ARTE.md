# Auditoría técnica de la redacción y propuesta del Director de Arte — *El Hoyformativo*

**Fecha:** 8-nov-2026  
**Alcance:** solo análisis. No se ha cambiado código, agentes ni contratos.  
**Jornada de referencia:** `dia/2026-11-07/`, completa y publicada.

**Cómo se hizo (versión ligera).** La auditoría se hizo la mañana de una jornada, con el límite de uso compartido. Por eso:
- Se han leído enteros `oficina/CONTRATOS.md`, `largo.py:main` (líneas 610-959), las cabeceras y las funciones de todos los módulos del motor, `director_arte.py` (inicio), los JSON reales y los agentes clave.
- De `largo.py:piezas_h`, `vista_tablero`, `_panel` y `short.py:main` se han leído los fragmentos relevantes, no cada línea.
- Lo que no se ha podido comprobar se marca como **[no verificado]**.

---

## 1. Resumen ejecutivo

**Cómo funciona hoy:**
- **Coordinación por ficheros.** La redacción trabaja con **contratos de ficheros** en `dia/<fecha>/`.
- **El orden visual se decide pronto y de forma dispersa:**
  - el **redactor** elige un **tipo de escena** del catálogo para cada paso (`ve.tipo`);
  - el **editor gráfico** añade fotos y viñetas;
  - el **motor** (`largo.py` / `short.py`) decide el resto, con valores fijos en el código.
- **No hay un plan visual explícito.** La «dirección de arte» actual (`director_arte.py`) solo puntúa **versiones de la miniatura** con Gemini.

**Principales hallazgos:**
1. **Ya existe un plan visual implícito y bien estructurado.** Hay 9 tipos de escena con campos semánticos (`claves`, `citas`, `persona`, `cifra`, `calendario`, `breve`…), sincronización con la voz por palabra (`cuando`) y un `escenas.json` de salida con los tiempos reales. El Director de Arte puede **apoyarse en esto, no sustituirlo**.
2. **El motor no lee ningún parámetro de estilo externo.**
   - Fijos en el código: movimientos de cámara, duraciones de transición, tamaños, zonas, colores y orden de capas.
   - Solo hay unos pocos interruptores: `tono` normal/sobrio, `comic` (lo activan las viñetas) y `categoria` en los Shorts.
3. **La identidad visual está repartida.**
   - Los colores están en `genera_video2.py` y repetidos a mano en `corto.py`, `short.py`, `titulares.py`, `miniatura.py` y `vinetas.py`.
   - Hay 7 tipografías en `fuentes/` y no hay un «manual» en código.
4. **La biblioteca de viñetas está vacía.** `canal/biblioteca_vinetas/` tiene `catalogo.json` con 95 escenarios, pero **0 imágenes**. El cron de las 17:40 UTC que la llenaba **no está en el crontab actual**: el plan B ante la caída de Cloudflare no existe en la práctica.
5. **Cambio mínimo recomendado:**
   - un **fichero de dirección nuevo y opcional**, `direccion_arte.json`, que escribe un programa (Gemini y Python, sin agente de Claude por defecto) entre el cierre y el montaje;
   - que `largo.py` y `short.py` lean **parámetros con valores por defecto iguales a los actuales**.

   Sin el fichero, todo sale exactamente como hoy (compatible hacia atrás y con la recuperación de jornadas).

---

## 2. Arquitectura real actual

### 2.1 Puestos y programas

| Fase | Quién (fichero real) | Lee | Escribe |
|---|---|---|---|
| 0-1 Recogida | `recopila.py` *(el programa se llama así, no «recopilador.py»; el agente sí se llama `recopilador`)* | RSS de 11 medios (`recopila.py:16-23`) | `noticias.json` |
| | `temas_gemini.py` (respaldo: agente `recopilador`) | `noticias.json` | `temas.json` |
| | `articulos.py` | `temas.json` | `articulos/NNN.txt` |
| | `erratas.py` (respaldo: `fe-de-erratas`) | episodio anterior y noticias | `correcciones.md` |
| | `contexto.py` (respaldo: `documentalista`) | `archivo/` | `contexto.md` |
| | `redes.py` (+ `x_oficiales.py`) | fuentes oficiales de partidos | `redes.md`, `redes.json` |
| | `ganchos.py` (8-nov) | `noticias.json`, `ganchos_director.md` | `ganchos.md` y su sección al principio de `redes.md` |
| | `encargo.py` | `encargo.json` | `encargo.json` (`verificada`, `prueba`) |
| | `investiga.py` (respaldo: `investigador`) | artículos y `redes.md` | `dossier/<id>.md` |
| 2 Consejo | agente `jefe-de-edicion` (Opus) | `temas.json`, dossieres, `redes.md` | `escaleta.json` |
| 3 Redacción | agente `redactor` (uno por bloque) | dossier, escaleta, `contexto.md` | `bloques/NN.json` |
| 3b Prechequeo | `prechequeo.py` | `bloques/NN.json` | stdout (OK o problemas) |
| 4 Mesa | `verificador`, `defensor-neutralidad`, `asesor-cumplimiento` | bloques y dossieres | `revision/{verificacion,neutralidad,cumplimiento}.md` |
| 5 Cierre | `editor-de-cierre` (Opus) | escaleta, bloques, revisiones, correcciones | `episodio.json` |
| 5b Gráfica | agente `editor-grafico` + `fotos.py` + `ia_vinetas.py preparar` + `revisa_vinetas.py` | `episodio.json` | `imagenes/`, `creditos.json`, `ve.foto` en `episodio.json`, `vinetas/sS_P_I.jpg`, `vinetas/hoja.png`, `revision/vinetas.md` |
| 6 Montaje | `largo.py` (sin agente) | `episodio.json`, `creditos.json`, `imagenes/`, `vinetas/` | `episodio.mp4`, `episodio.srt`, `escenas.json`, `episodio_descripcion.txt`, `render.log`, `tmp_largo/` |
| 6b Calidad | `control_calidad.py` + agente `control-calidad` | `episodio.mp4`, `escenas.json` | `calidad/escena_NN.png`, `calidad/datos.md`, `calidad/informe.md` |
| 6c Miniatura | agente `disenador-grafico` + `miniatura.py` + `director_arte.py` | episodio e imágenes | `miniatura.png`, `revision/miniatura.md` |
| 7 Publicación | `plataforma.py` (respaldo: `editor-plataforma`), `subir.py`, `notifica.py` | `episodio_descripcion.txt` y otros | `publicacion.md`, `youtube.json` |
| 7b Shorts | `shorts_dia.py` = `shorts_guion.py` + `short.py` | `episodio.json`, `redes.md`, `encargo.json` | `shorts/short_N.json`, `short_N.mp4`, `short_N_portada.png`, `shorts/hoja.png`, `shorts/youtube.json` |
| 8 Archivo | `documentalista` | el día | `archivo/historias.json`, `archivo/personas.json` |

**Coordinación:**
- La lleva la skill `.claude/skills/edicion-diaria/SKILL.md` (Sonnet), lanzada por `jornada.sh` desde cron a las 10:00 y 11:00 UTC con `--si-hora 12`.
- El vigilante de las 16:30 es `jornada.sh vigila`.
- El consumo de cada jornada queda en `archivo/consumo.tsv`.

### 2.2 Diagrama del flujo actual

```
recopila.py ─► noticias.json ─► temas_gemini.py ─► temas.json ─► articulos.py ─► articulos/
                         │                                              │
                         └► ganchos.py ◄── redes.py ◄─ x_oficiales.py   │
                               │            │                           ▼
                               └──► redes.md (ganchos arriba) ──► investiga.py ─► dossier/<id>.md
erratas.py ─► correcciones.md     contexto.py ─► contexto.md     encargo.py ─► encargo.json
                                         │
                                         ▼
                         jefe-de-edicion ─► escaleta.json
                                         ▼
                    redactor ×N ─► bloques/NN.json ─► prechequeo.py
                                         ▼
       verificador ∥ neutralidad ∥ cumplimiento ─► revision/*.md  (≤2 vueltas, vuelta al redactor)
                                         ▼
                         editor-de-cierre ─► episodio.json
                                         ▼
     editor-grafico + fotos.py + ia_vinetas.py + revisa_vinetas.py ─► imagenes/, vinetas/, creditos.json, ve.foto
                                         ▼
       largo.py ─► episodio.mp4, escenas.json, .srt  ─► control_calidad.py ─► calidad/  (≤2 vueltas, montador)
       disenador-grafico + miniatura.py + director_arte.py ─► miniatura.png        (en paralelo al montaje)
                                         ▼
       plataforma.py ─► publicacion.md ─► subir.py ─► youtube.json ─► notifica.py
                                         ▼
       shorts_dia.py (shorts_guion.py + short.py) ─► shorts/ ─► subir.py <fecha> shorts
                                         ▼
                                documentalista ─► archivo/
```

---

## 3. Contratos y flujo de ficheros

### 3.1 Validaciones que existen
- **`prechequeo.py`:** comprueba de forma mecánica cada bloque.
  - En la voz: medios nombrados y cifras en dígitos.
  - Cada `cuando` tiene que estar literal en `di` (líneas 27-39).
- **`investiga.py`:** marca con ⚠️ las citas que no están literales en los artículos.
- **`shorts_guion.py`:**
  - cita entera y literal en el material (`_norm`);
  - sin citas parciales y con 4 palabras o más;
  - réplica solo con una «prueba» literal;
  - segunda pasada de Gemini (`verifica_contexto`) que quita las frases no respaldadas;
  - lista `VALORATIVAS`.
- **`ganchos.py`:** la frase tiene que estar literal en el titular o la entradilla.
- **`encargo.py`:** oEmbed, artículos del día o `comprobada_a_mano`.
- **`largo.py`:**
  - avisa si una `foto` no está en `imagenes/` o no tiene crédito (línea 658) y la escena sale sin foto;
  - lanza `ValueError` si un bloque no tiene escenas (683);
  - registra en `render.log` cuántas palabras tienen tiempo de Whisper.
- **`control_calidad.py`:** un fotograma por escena (según `escenas.json`), LUFS y sincronía.
- **`revisa_vinetas.py`** (Gemini): letras inventadas, símbolos, fidelidad de las personas.
- **`director_arte.py`:** nota mínima de 7 para la miniatura.

### 3.2 Gestión de errores
- Cada programa de Gemini sale con **código 2** si Gemini está saturado; entonces la skill lanza el agente de Claude equivalente.
- `jornada.sh` hace hasta 3 intentos si se agota el límite del plan y nunca empieza uno después de las 21:00.
- Si una pieza falla dos veces, se anota en el parte y se sigue.
- Las fases críticas (recopilación, montaje, voz de Azure) avisan con `notifica.py --error` y no se sube nada.

### 3.3 Recuperación de una jornada
- Regla de la skill: **si el fichero de salida de una fase existe y es válido, la fase se salta**. Lo demuestra `parte_del_dia.md` del 7-nov: «14:32 reanudada (intento 2): episodio.json listo».
- Por eso **todo fichero nuevo tiene que ser idempotente y opcional**: si existe, se reutiliza; si falta, el siguiente paso funciona con los valores por defecto.

### 3.4 Contratos que no deben cambiar
- `episodio.json` (lo leen `largo.py`, `shorts_guion.py`, `short.py`, `titulares.py`, `prechequeo` vía bloques y `plataforma.py` vía la descripción).
- `creditos.json` (de él dependen la monetización y los derechos).
- `escenas.json` (lo usa el control de calidad).
- Los nombres `vinetas/s<sec>_<paso>_<item>.jpg` e `imagenes/retrato_<apellido>[_k].jpg` con `persona`.
- `shorts/short_N.json`.
- El catálogo de `ve.tipo`.

Se pueden **añadir campos opcionales** (el motor ya ignora los que no conoce; p. ej. `ve._vin` se inyecta en tiempo de ejecución), pero **no renombrar ni quitar** ninguno.

---

## 4. Estructura de `episodio.json` (real, 7-nov)

```json
{"fecha": "Sábado, 7 de noviembre de 2026",
 "titulo_video": "«Hay que ser cobarde»: Ayuso, Sánchez, el caso Koldo y Urda",
 "secciones": [ {"titulo": "...", "tono": "normal|sobrio", "fuentes": ["El País", "..."],
                 "pasos": [ {"di": "texto que lee la voz", "ve": { "tipo": "...", ... }} ]} ]}
```
- 8 secciones: sumario, corrección (antes del 8-nov iba la 2.ª; ahora va al final), 5 bloques y breves.
- 35 pasos, **10 sin `ve`**: el paso continúa la escena anterior y su voz cae sobre ella.
- La sección 0 es siempre el sumario.

**Tipos de escena usados el 7-nov** (`ve.tipo`, número de pasos): `sumario` 1, `claves` 6, `persona` 4, `citas` 5, `calendario` 3, `cifra` 2, `breve` 3, `despedida` 1. El motor admite además `mapa`, `posturas` y `cronologia` (`largo.py:piezas_h`).

| `ve.tipo` | Campos reales | Ejemplo real (resumido) |
|---|---|---|
| `sumario` | `items[]`: `texto, cuando, titular, destaca, etiqueta, persona?, seccion` | `{"titular": "«Hay que ser cobarde»", "destaca": "cobarde", "etiqueta": "Ayuso, en X", "persona": "Isabel Díaz Ayuso", "seccion": 5}` |
| `claves` | `titulo, items[]{icono, texto, cuando, escena, persona_vineta?}, fuente, foto?` | `{"icono": "escudo", "texto": "Núcleo Nacional: los detenidos se elevan a 14, según El Mundo", "cuando": "se han elevado a catorce", "escena": "an empty police station corridor..."}` |
| `persona` | `persona{nombre, cargo, partido, cita, medio, cita_cuando}, sello?, sello_cuando?` | `{"persona": {"nombre": "Pedro Sánchez", "cargo": "Presidente del Gobierno", "cita": "«El PP y Vox han criticado primero que no dimitiera»", ...}, "sello": "VALENCIA"}` |
| `citas` | `titulo, items[]{nombre, cargo, partido, cita, medio, cuando}` | dos voces enfrentadas (Sánchez y Ester Muñoz) |
| `cifra` | `numero, etiqueta, sub, nota, cuando_nota, fuente, foto?` | `{"numero": "69", "etiqueta": "fallecidos en Urda", ...}` |
| `calendario` | `dia, mes, pie, items[]{hora, texto, cuando}, fuente` | `{"dia": "12", "mes": "NOV", "pie": "Arranca la campaña oficial"}` |
| `breve` | `lugar, icono, titular, sub, fuente, escena, foto?` | `{"lugar": "Audiencia Nacional", "icono": "mazo", "titular": "Calama rechaza imputar..."}` |
| `despedida` | (ninguno) | `{"tipo": "despedida"}` |

**Qué ya existe para dirigir visualmente:**
- tipo de escena, texto de pantalla, protagonistas (con cargo y partido), citas literales y su medio;
- descripción en inglés de la viñeta (`escena`), foto de la escena (`foto`), tono por sección y fuentes;
- **anclas de tiempo con la voz** (`cuando`, `cita_cuando`, `sello_cuando`, `cuando_nota`, `items[].cuando`), que el motor resuelve con Whisper (`episodio.Tiempos`);
- la duración de cada escena **no** está en el JSON: la decide la voz.

**Qué falta:**
- **Formato editorial** (noticia, polémica, zasca, declaración, investigación, economía, sucesos, explicación). Solo existe `tono` (2 valores) y, en los Shorts, `categoria` (4 valores).
- **Intención de plano:** encuadre, movimiento, ritmo y énfasis.
- **Paleta o tratamiento por bloque.**
- **Transición deseada.**
- **Prioridad de cada imagen.**
- **«Golpe» (efecto de sonido) deseado.**
- **Subtítulos:** las palabras destacadas no se eligen (`C.grupos_palabras(T, set())` recibe un conjunto **vacío** de claves).

---

## 5. Estructura de `bloques/NN.json`

**Situación actual:**
- Es **una sección** con el mismo formato que las de `episodio.json` (`CONTRATOS.md`, fase 3): `{"titulo", "tono", "fuentes", "pasos": [{"di", "ve"}]}`.
- El 7-nov hubo `bloques/01.json` a `06.json` (5 bloques y breves).
- El editor de cierre los copia en `episodio.json` y añade el sumario, la corrección y la despedida.

**Reglas visuales que ya impone el redactor** (`.claude/agents/redactor.md:24-30`):
- al menos 3 tipos de escena distintos por bloque y nunca el mismo dos veces seguidas;
- cada `cuando` literal, de 2 a 4 palabras;
- las `escena` de las viñetas sin objetos que inviten a escribir;
- `persona_vineta` solo si la nota cuenta algo que hizo esa persona.

---

## 6. Capacidades reales de `largo.py` y `short.py`

### 6.1 `largo.py` (16:9, 1920×1080)

**Dependencias:**
- `corto.py`: piezas polaroid, nota, pegatina, sello, mapa, `grupos_palabras`, `capa_cap`, `fotos_personas`.
- `episodio.py`: `Tiempos`, `capa_teaser`, `rebote`, `CON_FOTO`, `escribe_textos`.
- `genera_video2.py`: colores, `fuente`, `pega`, `suave`, `logo`, `capa_cabecera`, `fondo_marca`, `cuadro_intro`, `cuadro_cierre`, `CORTINILLA`.
- `prototipo_animado.py`: `capa_bloque`, mascota.
- `titulares.py`, `marca.py`, `cierre.py`, `vinetas.py`, `ia_vinetas.py`, `musica.py`, `voz.py`.

**Tubería (`main`, líneas 610-949):**
1. Por cada sección:
   - `voz.locuta` genera la voz (Azure Tristán HD) y `E.Tiempos` da el tiempo de cada palabra (Whisper tiny).
   - Cada paso con `ve` se convierte en una **«parte»**: `{t0, t1, tipo, piezas, fondo, fuente, comic?, sobrio}`.
2. `piezas_h(ve, …)` (línea 102) convierte cada tipo de escena en piezas de tablero (`(imagen, x, y, t_aparece)`), sobre un ancho `LW = 1510`. Las coordenadas están **fijas en el código** para cada tipo.
3. `encaja()` (315) centra las piezas, amplía hasta ×1,35 y crea el **fondo vivo** (`fondo_vivo`, 267: foto o viñeta desenfocada y tintada).
4. `paneles_comic()` (469): en `claves` y `cronologia` con viñetas o `persona_vineta`, y en `breve`, la escena pasa a **cómic a pantalla completa** (`vista_comic` 437, `_panel` 370).
5. La sección 0 con `sumario` va a `titulares.prepara/cuadro` (tarjetas a pantalla completa). Después viene el golpe de marca (`marca.Golpe`, 2,6 s).
6. Audio: `musica.mezcla` con efectos `pop` (cada pieza), `whoosh` (cada cambio de escena), `clic` y `campana` (despedida), y la sintonía en el golpe. Música más baja en los bloques sobrios (`calma`).
7. Render: `cuadro(t)` (776) compone cada fotograma. `trabajadores()` reparte los fotogramas en **N procesos con `fork`** (`cv2.setNumThreads(1)` antes del fork) y ffmpeg une los trozos y mezcla el audio (loudnorm −14 LUFS).

**Elementos que sabe dibujar (existentes):**
- Polaroid con retrato y crédito.
- Nota y pegatina.
- Sello.
- Flecha.
- Mapa con puntos.
- Tarjeta de cita.
- Cifra grande.
- Hoja de calendario.
- Fila con icono (`episodio.icono`).
- Panel de cómic:
  - viñeta con zoom lento y recuadro de narración;
  - foto de persona con contorno suave y cita escribiéndose;
  - texto grande sobre trama.
- Cabecera con logo, nombre y fecha.
- Rótulo del bloque (`P.capa_bloque`).
- Píldora «A continuación» (`capa_teaser`).
- Línea de FUENTES.
- Barra de progreso amarilla.
- Subtítulos de 1-2 palabras con clave amarilla.
- Despedida con botón de suscribirse y campana (`cierre.Cierre`).

**Movimientos y animaciones existentes:**
- **Cámara del tablero** (`vista_tablero`, 504):
  - golpe de cámara hacia cada pieza que entra (`z = 1 + 0,12·e^(−t/0,7)`);
  - en las viñetas con `foco`, acercamiento hasta ×2,2 con zoom lento;
  - suavizado exponencial con τ = 0,22 s.
- Rebote al entrar (`E.rebote`).
- Ken Burns del fondo.
- Zoom lento de 2,5 % en las viñetas.

**Transiciones existentes:**
- Cortinilla roja y amarilla entre bloques (`G2.CORTINILLA` = 0,55 s).
- `desliza()` (450): la escena nueva entra desde la derecha y la anterior se desplaza un 30 % y se oscurece; fundido en los bloques sobrios. Duración 0,7 s, solo si alguna de las dos es cómic.
- En el tablero, «sin dos transiciones seguidas» (`sin_entrada` / `sin_salida`).

**Configurable hoy:**
- `tono` (normal o sobrio): sin pop, música baja, fundido en vez de deslizamiento, trama apagada.
- `CON_URNI`.
- `ve.foto` y la presencia de viñetas (activan el cómic).
- CLI: `--fotogramas` (un PNG por escena, sin vídeo), `--hasta` y `--desde` (tramos de prueba).

**Fijo en el código:**
- Escenario `BX, BY, BW, BH = 40, 178, 1840, 762`, `LW = 1510`.
- Duraciones (0,7 s, 0,35 s, 0,55 s) y zoom máximo (×1,35 / ×2,2).
- Tamaños de letra; posición de los subtítulos (y = 985) y del teaser.
- Colores de cada pieza (`AMARILLA`, `CREMA`).
- Orden de capas.
- Qué tipo de escena se convierte en cómic.

**Reutilizable tal cual por un plan visual:** `piezas_h`, `encaja`, `fondo_vivo`, `paneles_comic`/`_panel`/`vista_comic`, `desliza`, `vista_tablero`, `linea_fuente`, `titulares.cuadro`, `marca.Golpe`, `cierre.Cierre` y el reparto en procesos (`trabajadores`, `dibuja_trozo`).

### 6.2 `short.py` (9:16, 1080×1920)

- **Entrada:** `shorts/short_N.json`, que escribe `shorts_guion.py` o, desde el 8-nov, el guion fijo de `encargo.json → short_fijo`. Campos:
  - `categoria, kicker, quien, cargo, partido, entrada, cita, destaca, fuente, enlace`;
  - `contexto, voz, titulo, portada, hashtags, etiquetas, sintetico`;
  - `replica{quien, cita, prueba, entrada?, kicker?}?` y `medio{quien, cita, entrada, kicker}?` (8-nov).
- **Línea de tiempo**, sacada de la voz con `E.Tiempos`:
  1. gancho: persona MUY grande (`_persona`, encuadre YuNet) y cita enorme (`_cita`);
  2. 1b. segunda voz (`medio`);
  3. contexto: paneles con imágenes del tema que se deslizan (`_panel`, `panel_en`, uno cada 4,5 s aprox.) y el texto frase a frase (`_caja`);
  4. réplica;
  5. cierre desde «¿Qué opinas?» con botón de suscribirse y campana.
- **Fondo:** imagen del tema desenfocada en movimiento (`_fondo_tema`, `_mueve`).
- **Cabecera:** `_cabecera` con logo EH, nombre en dos colores, etiqueta de `categoria` y fecha.
- **Portada:** `portada()` sale en los primeros 0,4 s.
- **Imágenes del tema:** las saca de la sección del vídeo largo donde está la cita (`_seccion`, `_imagenes_tema`), con un máximo de 8.
- **Fijo:** `ZONA = (150, 1050)`, `ALTO_CITA = 300`, tamaños, 4,5 s por panel, golpe de cámara (+10 % en 0,35 s).
- **Hasta el 8-nov no tenía render en paralelo** [no verificado en detalle]; tarda unos 3 min por Short.

### 6.3 Qué haría falta para que lean un plan visual externo
- **Un único punto de lectura:** cargar `direccion_arte.json` si existe y fusionarlo con los valores por defecto (un diccionario `ESTILO`).
- **En `largo.py`, sustituir constantes por valores de `ESTILO`/`plan`:**
  - zoom del golpe de cámara y τ;
  - transición entre partes (cortinilla, deslizamiento, fundido, corte);
  - si una escena va en cómic o en tablero (hoy depende de que haya viñetas);
  - elección de `fondo_de`;
  - palabras clave de los subtítulos (pasar un conjunto no vacío a `grupos_palabras`);
  - qué efectos de sonido suenan.
- **En `short.py`:** duración de cada panel, orden y elección de las imágenes (`_imagenes_tema`), plantilla según `categoria` y palabras destacadas.
- **Por desarrollar** (no existe): tratamientos visuales distintos por formato editorial, rótulo inferior («lower third») de identificación del tema, separador común entre noticias, gráficos de datos (barras y comparativas) y capturas de tuits.

---

## 7. Sistema de fotografías y viñetas

### 7.1 `fotos.py`
- **Fuentes:**
  - `commons_categoria` (categorías de Commons y sus subcategorías por año);
  - `moncloa` (Pool Moncloa);
  - `retrato_wikidata` (P18, con comprobación de que el elemento es una persona, P31=Q5, y de que el nombre coincide);
  - `openverse`, `wikimedia` (búsqueda).
- **Licencias:** filtro `_lic_ok` (CC0, dominio público y CC BY; sin NC ni ND).
- **Flujo del editor gráfico:**
  - `buscar` deja candidatas en `fotos_candidatas/<slug>_<k>.jpg` + `.json`;
  - el agente las mira y elige;
  - `elegir` baja la original con `original()` / `baja()` a 3200 px y la apunta en `creditos.json`;
  - `recorta` saca a una persona de una foto de grupo.
- **`mejores` (7-nov):** reúne candidatas, filtra con YuNet (cara con al menos el 14 % de la altura y 70 px), Gemini puntúa por calidad y gesto (`--animo`) y guarda las mejores con `puntos_gemini`.
- **Metadatos en `creditos.json`** (real): `{titulo, url, ancho, alto, autor, licencia, pagina, fuente, persona?}`.
- **Al motor** solo le llegan: el nombre del fichero (`ve.foto` o el retrato por `persona`) y el crédito.
- **Limitaciones:**
  - sin metadatos de **encuadre** (tamaño o posición de la cara, orientación) ni de **gesto**: YuNet se recalcula en cada montaje;
  - no se sabe la fecha ni el acto de cada foto;
  - muchas personas sin foto libre: el 7-nov, Muñoz, Samper y Otero;
  - la búsqueda es por texto y no se puede pedir «perfil mirando a la izquierda».

### 7.2 `ia_vinetas.py`
- **Escenas:** FLUX.1 schnell de Cloudflare con el estilo `ESTILO`. Si se agota la cuota, el fichero `cache/cloudflare_agotado_<fecha>` desvía al Space de FLUX en Hugging Face (`_escena_hf`).
- **Personas:** FLUX.2 klein con su retrato real y `canal/estilo_vineta.jpg` como referencia (`PERSONA`). Solo desde retratos CC0, dominio público o CC BY (`licencia_dibujable`).
- **`preparar`:** recorre las notas con `escena` (`notas_con_vineta`), genera 2 versiones y deja `vinetas/sS_P_I.jpg`, `vinetas/hoja.png` y el origen de cada una (`guarda_origen`; el 7-nov **no** se generó `origen.json`, así que el motor usa el crédito por defecto [no verificado por qué]).
- **Otras funciones:** `rehacer`, `descartar` y `elegir`. `ilustracion_ambito` dibuja el ámbito de una persona sin foto libre. `caricatura` (7-nov) existe pero el usuario la descartó.
- **Caché:** `cache/vinetas/<sha1>.jpg`; una misma escena no gasta cuota dos veces.
- **Biblioteca:**
  - `catalogo.json` tiene **95 escenarios y 0 imágenes**; el cron que la generaba no está en el crontab;
  - **plan B inexistente** ahora mismo.

### 7.3 `rembg` y YuNet
- **rembg:** `miniatura.recorte` con el modelo `u2net_human_seg`, relleno de huecos desde las 4 esquinas y corte de mesas o carteles en la parte baja. Lo guarda en caché en `<foto>_recorte.png`.
- **YuNet:** `miniatura.cara` / `encuadre_cara` / `protagonista`, a través de `G2._cv2`. Lo usan la miniatura, el sumario, los Shorts y `fotos.mejores`.

### 7.4 Cómo recibir instrucciones visuales más precisas
- Ampliar `creditos.json` con un campo opcional `analisis`, calculado una vez y en caché: `{cara_bbox, cara_frac, mira: "izq|der|frente", gesto, puntos_gemini}`.
- Así el Director de Arte puede pedir «persona X mirando a la derecha, gesto serio» y el motor colocarla enfrentada sin recalcular nada.

---

## 8. Miniaturas y dirección de arte actual

| Función | Dónde | Qué hace |
|---|---|---|
| **Selección de fotos** | `fotos.py mejores`, agente `disenador-grafico` | Candidatas, filtro de cara y Gemini |
| **Composición** | `miniatura.py`: `miniatura()` (con `--rival`, `--inserto`, `--insignia`, `--sobrio`, franja de brocha `brocha()` en el cara a cara) y `miniatura_pro()` (plantillas `informativo` / `impacto`) | Fondo, recorte, encuadre por la cara, titular con relieve, etiqueta, logo, grano y marco |
| **Evaluación** | `director_arte.py`: `evalua(fecha, archivos)` y `main` | Gemini puntúa de 0 a 10 cada versión a tamaño completo y a 320 px; copia la mejor si tiene 7 o más; deja `revision/miniatura.md` |
| **Dirección visual del episodio** | **no existe** | — |

**Qué se conserva:** todo lo anterior.
- `director_arte.py` debería **renombrarse en la documentación** como «evaluador de miniaturas», para no confundirlo con el nuevo puesto; el fichero y su uso no cambian.
- El patrón de `evalua` (Gemini con imágenes a dos tamaños y criterios) es **reutilizable** para revisar los fotogramas de `calidad/escena_NN.png`.

---

## 9. Identidad visual actual

| Elemento | Dónde | Centralizado |
|---|---|---|
| Colores de marca `ROJO #E52521`, `AMARILLO #FACC15`, `NOCHE #101C34` (8-nov) | `genera_video2.py:31-32` | Sí, pero **repetidos a mano**: `corto.NAVY (12,20,38)`, `short.NAVY`, `short.CATEGORIAS` con el azul escrito a mano, `vinetas.py` (rojo antiguo `(200,16,46)` en varias líneas), `ia_vinetas.py` (amarillo antiguo en las hojas), `titulares._tinte`, `miniatura.GRAD`, `largo.AMARILLA/CREMA` |
| Logo EH | `genera_video2.logo_partes/logo` | Sí |
| Nombre | `genera_video2.MARCA` | Sí (pero `short._cabecera` lo escribe en dos colores aparte) |
| Lema | `genera_video2.LEMA` («La política española del día, en claro») | **Desactualizado**: el usuario eligió «La actualidad, en un minuto» |
| Tipografías | `fuentes/`: Inter (4 pesos), Anton, Barlow Condensed, Caveat, Comic Neue, Bangers, VT323 (todas OFL) | No: cada módulo elige la suya. **No hay** Archivo ni Montserrat, que propone el manual del usuario |
| Cabecera | `G2.capa_cabecera` (largo) y `short._cabecera` (Shorts) | Dos implementaciones |
| Rótulo de bloque | `prototipo_animado.capa_bloque` | Sí |
| Subtítulos | `corto.capa_cap` + `grupos_palabras` | Sí (las palabras clave nunca se pasan) |
| Golpe de marca | `marca.Golpe` (el comentario aún habla del «cuadrado rojo» y del «sobre»; con el logo EH el sobre va vacío) | Sí |
| Despedida | `cierre.Cierre` (largo); cierre propio en `short.py` | Dos implementaciones |
| Miniatura | `miniatura.py` (+ `canal/miniatura_referencia.png`) | Sí |
| Banner y avatar | `miniatura.py --canal`; `canal/avatar.png` y `banner.png` **todavía con Urni** | — |

---

## 10. Limitaciones detectadas

1. **La biblioteca de viñetas está vacía** y su cron no existe (§7.2). *Cambio mínimo: volver a poner el cron de `ia_vinetas.py biblioteca` y comprobarlo.*
2. **No hay noción de formato editorial** en el episodio: solo `tono`.
3. **Subtítulos sin palabras clave:** `grupos_palabras(T, set())` en `largo.py:704`.
4. **Identidad repetida** en 8 módulos, con restos de la paleta anterior (§9).
5. **El cómic depende de que existan viñetas:** si Cloudflare falla, todo vuelve a tablero sin decisión explícita.
6. **Las imágenes no se analizan** (encuadre, mirada, gesto) de forma reutilizable.
7. **El control de calidad es visual a posteriori** (agente con capturas). No compara contra lo que se quería.
8. **`short.py` y `largo.py` comparten poco código** (cabecera, cierre, panel): cada mejora se hace dos veces.
9. **La calidad depende de dos vueltas de montaje** (el 7-nov: «CORREGIR» dos veces y unos 40 min de renders extra). Un plan visual validado antes del render evitaría parte.

Aparte de lo técnico: en el crontab del servidor hay una contraseña de `sudo` en texto plano (en una tarea de otro proyecto). Conviene quitarla.

---

## 11. Arquitectura recomendada para el nuevo Director de Arte

**Principios:**
- Un **puesto nuevo de la fase 5c**, entre el editor gráfico y el montaje, que **escribe un fichero** y no habla con nadie.
- **Python y Gemini por defecto; agente de Claude solo de respaldo**, como el resto de la oficina.
- **Opcional e idempotente:** si su fichero no está, el motor hace lo de hoy.

```
editor-de-cierre ─► episodio.json
editor-grafico ───► imagenes/, vinetas/, creditos.json
                         ▼
   NUEVO  direccion_arte.py (Gemini + reglas Python; respaldo: agente director-de-arte)
          lee: episodio.json, escaleta.json (enfoque/tono), creditos.json(+analisis), vinetas/, ganchos.md
          escribe: direccion_arte.json  (+ revision/direccion_arte.md: resumen legible)
                         ▼
   largo.py / short.py ─► leen direccion_arte.json si existe (valores por defecto si no)
                         ▼
   control_calidad.py ─► (NUEVO, opcional) revisa_visual con Gemini: compara fotogramas con el plan
```

**Las 8 capacidades pedidas, puestas en su sitio:**
1. **Dirección creativa:** el formato editorial de cada bloque (§12) y el «concepto» del episodio. *Gemini, una llamada.*
2. **Fotografía y recursos:** pedir lo que falta (persona, gesto, mirada) a `fotos.py mejores` / `ia_vinetas.py` **antes** del montaje. *Python + Gemini, reutilizando lo existente.*
3. **Realización y storyboard:** por escena, la vista (tablero, cómic, persona a pantalla completa), la transición y el énfasis. *Reglas Python más una llamada de Gemini por episodio.*
4. **Composición:** parámetros de `ESTILO` por formato. *Python: tabla fija y versionada.*
5. **Ritmo:** máximo de segundos sin cambio de imagen, efectos, palabras clave de los subtítulos. *Python sobre los tiempos de Whisper (ya están).*
6. **Marca:** módulo único de identidad (§13.1). *Python.*
7. **Supervisión del render:** Gemini sobre `calidad/escena_NN.png` frente al plan, con el patrón de `director_arte.evalua`.
8. **Aprendizaje con métricas de YouTube:** **etapa posterior**. Necesita YouTube Analytics (otro permiso OAuth de `subir.py`, que el usuario tendría que autorizar) y guardar en `archivo/metricas.json` qué formato, gancho y miniatura tuvo cada vídeo.

**No es recomendable:** un agente de Claude que redacte el storyboard de cada escena cada día. Multiplicaría el consumo (el 7-nov ya fueron unos 8 USD equivalentes) y el motor no puede ejecutar libertades que no existen en el código.

---

## 12. Nuevos contratos y ficheros propuestos

Evaluación de los cuatro ficheros sugeridos:

| Propuesto | Recomendación |
|---|---|
| `direccion_arte.json` | **Sí, como fichero único** que reúna la dirección creativa y el plan visual. Un solo fichero es más fácil de reutilizar al retomar y de validar |
| `plan_visual.json` | **Dentro de `direccion_arte.json`** (clave `escenas`). Separarlo obliga a coordinar dos ficheros que siempre cambian juntos |
| `recursos_visuales.json` | **No como fichero nuevo**: ampliar `creditos.json` con campos opcionales (`analisis`, `rol`) y poner las necesidades no cubiertas en `direccion_arte.json → faltan`. Evita dos fuentes de verdad sobre derechos |
| `revision_visual.json` | **Sí, pero como `revision/visual.md`** (más un `calidad/visual.json` para la máquina), siguiendo el patrón de `revision/*.md` y `calidad/informe.md` |

**Contrato propuesto** (fase 5c), `dia/<fecha>/direccion_arte.json` (todo opcional para el motor):
```json
{"version": 1,
 "concepto": "1-2 frases: el hilo visual del día",
 "secciones": [
   {"seccion": 2, "formato": "polemica|zasca|declaracion|ultima_hora|investigacion|economia|sucesos|explicacion",
    "tono": "normal|sobrio",
    "acento": "rojo|amarillo|azul",
    "escenas": [
      {"paso": 0, "vista": "tablero|comic|persona_full|cita_full|cifra_full",
       "transicion": "cortinilla|desliza|fundido|corte",
       "foco": "Isabel Díaz Ayuso", "mira": "der",
       "claves_sub": ["cobarde"],
       "efecto": "pop|whoosh|golpe|ninguno"}]}],
 "shorts": {"1": {"plantilla": "zasca", "panel_s": 3.0}},
 "faltan": [{"seccion": 4, "paso": 2, "que": "retrato", "persona": "Ester Muñoz", "estado": "sin foto libre"}],
 "generado": {"por": "direccion_arte.py", "modelo": "gemini", "hash_episodio": "sha1 de episodio.json"}}
```
- **`hash_episodio`:** si `episodio.json` cambia (el montador corrige algo), el plan se regenera; si no, se reutiliza. Así se respeta la recuperación de jornadas.
- **Validación:** `direccion_arte.py --valida` comprueba lo siguiente y avisa si algo no cuadra (el motor usa entonces los valores por defecto para esa escena):
  - índices de sección y paso existentes;
  - valores dentro de los enumerados;
  - que `foco` aparezca en esa escena;
  - que cada `claves_sub` sea una palabra del `di`.

---

## 13. Modificaciones necesarias en el motor Python

### 13.1 Mínimas (etapa 1, sin cambiar nada visible)
1. **`identidad.py`** (nuevo, solo constantes):
   - colores, fuentes por uso (titular, subtítulo, texto), radios, grosores, lema, `CATEGORIAS` y formatos;
   - `genera_video2.py`, `short.py`, `corto.py`, `titulares.py`, `miniatura.py`, `vinetas.py` y `largo.py` importan de ahí;
   - las mismas cifras que hoy, salvo arreglar los restos de la paleta antigua.
2. **`largo.py` / `short.py`:**
   - función `estilo(dia)` que lee `direccion_arte.json` si existe;
   - si no, `{}`: con valores por defecto **idénticos a los actuales**.

### 13.2 Etapa 2 (empieza a cambiar el resultado)
- `largo.py:704`: `C.grupos_palabras(T, claves_de_la_seccion)` con `claves_sub`.
- `largo.py:663-679`: decidir el cómic por `vista` cuando venga en el plan (si no, la regla actual).
- `largo.py:819-825`: la transición según `transicion` (las funciones `desliza` y la cortinilla ya existen; falta «fundido» fuera del modo sobrio y «corte»).
- `largo.py:729-731`: filtrar o añadir efectos según `efecto`.
- `largo.py:fondo_de`: preferir `foco`.
- `short.py`: `panel_s` en lugar de 4,5 s y plantilla según `categoria` o formato.

### 13.3 Etapa 3 (capacidades nuevas)
- Vistas `persona_full` / `cita_full` / `cifra_full`: componer con `titulares.cuadro` y `short._persona` / `_cita`, adaptados a 16:9.
- Rótulo inferior por formato y separador entre noticias (en `cuadro`, junto a la cortinilla).
- Capturas de tuits verificados por oEmbed (texto, autor y fecha) dibujadas por nosotros, nunca una captura de imagen de X.

**Rendimiento:**
- El plan se lee **antes** del `fork` y se consulta como diccionario dentro de `cuadro(t)`, sin entrada/salida por fotograma.
- Los 4 procesos no cambian.
- Nada de llamadas a modelos dentro del render.

---

## 14. Costes y optimización

**Situación actual por jornada:**
- Llamadas a Gemini, gratis (dos claves desde el 7-nov): temas, erratas, contexto, ~7 dossieres, ganchos, revisión de viñetas, director de arte de la miniatura, plataforma y Shorts (2-3).
- Cloudflare: ~20 viñetas al día (gratis, 10.000 neuronas).
- Claude (`archivo/consumo.tsv`): unos 8 USD equivalentes los días completos (6 y 7-nov), sobre todo Sonnet como coordinador y Opus en consejo y cierre.

**Director de Arte propuesto:**
- **1 llamada de Gemini por episodio** (formato y plan, en JSON) más 1 por Short (opcional, puede ir en la misma).
- Supervisión: **1 llamada de Gemini** con la hoja de contacto de `calidad/` (hoja de 4 en 4, ya generada).
- Total: unas 2-4 llamadas gratuitas más y **0 de Claude** salvo que Gemini falle.

| Tarea | Python | Visión artificial | LLM |
|---|---|---|---|
| Ritmo, tiempos, claves de subtítulo (palabras con más «peso»: nombres propios, cifras, la palabra `destaca`) | ✔ | | |
| Validar el plan | ✔ | | |
| Encuadre, mirada y tamaño de la cara | | ✔ (YuNet, en caché en `creditos.json`) | |
| Gesto o calidad de la foto | | | ✔ Gemini (ya en `fotos.mejores`) |
| Formato editorial y concepto | | | ✔ Gemini |
| Supervisión del render | | | ✔ Gemini con imágenes |

**Reutilización:**
- Caché de viñetas (`cache/vinetas`), de recortes (`_recorte.png`) y de voz.
- Análisis de foto guardado una vez por fichero (clave = nombre y tamaño).

---

## 15. Plan de implementación por etapas

| Etapa | Contenido | Riesgo | Cómo se comprueba |
|---|---|---|---|
| **0** (urgente, independiente) | Volver a poner el cron de la biblioteca de viñetas; actualizar `LEMA`; quitar la contraseña del crontab | Bajo | `crontab -l`; ver imágenes en `canal/biblioteca_vinetas/` |
| **1** | `identidad.py` y lector `estilo(dia)` con valores por defecto iguales a los de hoy | Bajo | `largo.py --fotogramas` de un día ya hecho: **idéntico** píxel a píxel (o casi, por la paleta corregida) |
| **2** | `direccion_arte.py` (Gemini y reglas) que escribe `direccion_arte.json` con `formato` y `claves_sub`; motor: subtítulos con claves y transición por escena | Medio | Comparar `--fotogramas` con y sin el fichero; un día de prueba en `dia/AAAA-MM-DD-prueba` |
| **3** | Análisis de fotos en `creditos.json` (mirada y cara), `foco`, plantillas de Short por formato | Medio | Hoja de Shorts, `calidad/` |
| **4** | Supervisión con Gemini contra el plan (`revision/visual.md`); sustituye a parte de la segunda vuelta del montador | Medio | Menos vueltas en `parte_del_dia.md` |
| **5** | Vistas nuevas (`persona_full`, rótulo inferior, separador, tarjeta de tuit) | Alto (código nuevo de dibujo) | Fotogramas y tiempo de render ≤ +10 % |
| **6** | Métricas de YouTube (Analytics) en `archivo/metricas.json` y ajuste de pesos por formato | Requiere autorización OAuth del usuario | Informe semanal |

Integración en la skill: un paso nuevo «5c. Dirección de arte» después del editor gráfico, con la regla de siempre: **si `direccion_arte.json` existe y su `hash_episodio` coincide, se salta**; si el programa sale con 2, se monta sin plan (no se lanza agente salvo que se decida otra cosa).

---

## 16. Riesgos y compatibilidad

- **Que el render se rompa:** cada campo nuevo es opcional y tiene su valor por defecto en el código. Si falla la validación de una escena, se usa la regla actual. Nunca se para el montaje por el plan.
- **Retomar jornadas:** el fichero con `hash_episodio` se reutiliza o se regenera; no rompe el «si existe, se salta».
- **Tiempo de render** (~15 min, 4 procesos): el plan se carga antes del fork y no hay modelos dentro del render. Las vistas nuevas de la etapa 5 son el único riesgo de que tarde más.
- **Veracidad y normas del canal:**
  - el Director de Arte **no puede añadir texto** que no esté en `episodio.json` ni imágenes que no estén en `creditos.json`;
  - sus campos son de forma, no de contenido;
  - las capturas de tuits solo con texto comprobado por oEmbed;
  - nada de imágenes de IA de personas reales salvo las viñetas ya reguladas.
- **Consumo:** al ser Gemini por defecto, el plan de Claude no crece. Si Gemini falla, se monta sin plan en vez de lanzar un agente.
- **Doble mantenimiento largo y Short:** `identidad.py` y funciones compartidas (cabecera, panel, persona) lo reducen poco a poco, sin reescribir.
- **Duplicidades de nombre:** `director_arte.py` (miniaturas) y el nuevo `direccion_arte.py` se parecen. Se puede llamar al nuevo `realizacion.py` si se prefiere evitar confusión.

---

### Ficheros inspeccionados
`oficina/CONTRATOS.md`, `.claude/skills/edicion-diaria/SKILL.md`, `.claude/agents/{redactor,editor-grafico,disenador-grafico,jefe-de-edicion}.md`, `dia/2026-11-07/{episodio.json, escaleta.json, escenas.json, creditos.json, parte_del_dia.md, bloques/, vinetas/, calidad/, shorts/}`, `largo.py`, `short.py`, `shorts_guion.py`, `director_arte.py`, `miniatura.py`, `fotos.py`, `ia_vinetas.py`, `marca.py`, `titulares.py`, `musica.py`, `cierre.py`, `vinetas.py`, `corto.py`, `episodio.py` (funciones), `genera_video2.py`, `control_calidad.py`, `prechequeo.py`, `plataforma.py`, `revisa_vinetas.py`, `recopila.py` (fuentes), `jornada.sh` (reintentos), `canal/biblioteca_vinetas/catalogo.json`, `archivo/consumo.tsv`, crontab del servidor.
