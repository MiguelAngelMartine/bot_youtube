# Redacción de *Política en Claro*: organigrama y cadena de montaje

La oficina funciona como una redacción de informativos de televisión:
- cada puesto es un **agente** de Claude Code con una sola responsabilidad (definido en `.claude/agents/`);
- el **jefe de producción** coordina la jornada (`.claude/skills/edicion-diaria/`);
- cada fase deja su trabajo en un **fichero** de `dia/AAAA-MM-DD/` que recoge la fase siguiente (contratos en `oficina/CONTRATOS.md`). Nadie trabaja sobre el papel de otro sin pasar por su puesto.

Las tareas mecánicas (descargar RSS, renderizar el vídeo, dibujar la miniatura) las hacen **herramientas** en Python. Los agentes deciden, redactan, comprueban y corrigen.

```
 FASE 0 · ARCHIVO Y ERRATAS
   Fe de erratas ───────────────► correcciones.md    (¿algo de ayer resultó falso o incompleto?)
   Documentalista ──────────────► contexto.md        (historias que siguen, cargos verificados)
 FASE 1 · RECOPILACIÓN
   Recopilador ── recopila.py ──► noticias.json → temas.json   (11 medios, agrupadas por tema)
   Investigadores (1 por tema) ─► dossier/<tema>.md            (hechos, versiones, citas, fuentes)
 FASE 2 · CONSEJO DE REDACCIÓN
   Jefe de edición ─────────────► escaleta.json      (qué entra, en qué orden, tono, enfoque, duración)
 FASE 3 · REDACCIÓN
   Redactores (1 por bloque) ───► bloques/NN.json    (texto con la voz de Urni + escenas)
 FASE 4 · MESA DE CONTROL  (las tres en paralelo; si alguna dice CORREGIR, el bloque vuelve al redactor)
   Verificador ─────────────────► revision/verificacion.md   (cada frase contra el dossier)
   Defensor de la neutralidad ──► revision/neutralidad.md    (equilibrio, tiempos, lenguaje)
   Asesor de cumplimiento ──────► revision/cumplimiento.md   (YouTube, derechos, tono en tragedias)
 FASE 5 · CIERRE
   Editor de cierre ────────────► episodio.json      (sumario + bloques + despedida, duración final)
   Editor gráfico ── fotos.py ──► imagenes/ + creditos.json + campo "foto"  (retratos para las polaroids y foto de cada escena de texto)
 FASE 6 · PRODUCCIÓN
   Montador ── largo.py ────────► episodio.mp4, episodio.srt, escenas.json  (horizontal estilo tablero)
   Control de calidad ── control_calidad.py ─► calidad/informe.md   (fotogramas, sonido, sincronía)
   Diseñador gráfico ── miniatura.py ───────► miniatura.png (+ banner y avatar del canal)
 FASE 7 · PUBLICACIÓN
   Editor de plataforma ────────► publicacion.md     (título, descripción, etiquetas, comentario, lista para YouTube Studio)
   Jefe de producción ──────────► parte_del_dia.md + aviso por Telegram al director (el usuario)
 DIRECTOR (el usuario): ve el vídeo, aprueba y lo sube a YouTube.
 FASE 8 · ARCHIVO (después de publicar)
   Documentalista ──────────────► archivo/historias.json, archivo/personas.json
```

## Horario de la jornada
El vídeo se publica **por la tarde** para que tenga horas de visualizaciones el mismo día:
- **todo el día, cada hora:** el servidor recoge noticias y textos completos (bots del servidor);
- **15:00:** arranca la redacción con lo publicado desde la edición anterior (unas 24 h, hasta las 15:00);
- **~16:30:** vídeo, miniatura y textos listos; aviso por Telegram al director;
- **17:00-18:00:** el director revisa y publica.

Lo que pase después de las 15:00 entra en el episodio del día siguiente, y la fe de erratas recoge cualquier cambio.

## Puestos

| Fase | Puesto | Qué hace | Qué NO hace | Modelo |
|---|---|---|---|---|
| 0 | **Fe de erratas** | Compara lo que dijo el episodio anterior con las noticias nuevas. Si algo resultó falso o una parte lo desmiente, propone una corrección para abrir el episodio. | Opinar o reescribir el episodio viejo | sonnet |
| 0/8 | **Documentalista** | Lleva el archivo: historias en curso (día N de Urda...), cargos y partidos de cada persona, cifras ya dadas. Da contexto a los investigadores y actualiza el archivo tras publicar. | Inventar contexto que no esté en una fuente | sonnet |
| 1 | **Recopilador** | Lanza la recopilación de los 11 medios, limpia duplicados y agrupa las noticias por tema, indicando qué medios cubren cada uno. | Elegir qué es importante | sonnet |
| 1 | **Investigador** (uno por tema) | Lee las noticias completas (al menos dos medios de líneas distintas). Saca hechos, cifras, citas literales y la versión de cada parte, y marca cada hecho como CONTRASTADO (2+ medios) o ATRIBUIDO (1 medio). | Redactar el guion | sonnet |
| 2 | **Jefe de edición** | Consejo de redacción: elige 4-6 temas por relevancia informativa, decide orden, tono (normal/sobrio), enfoque y tiempo de cada bloque, y los breves. | Escribir el texto | opus |
| 3 | **Redactor** (uno por bloque) | Escribe el bloque con la voz de Urni (libro de estilo): gancho, hechos, contexto, «qué pasa ahora». Elige las escenas del catálogo. | Añadir nada que no esté en el dossier | opus |
| 4 | **Verificador** | Comprueba frase a frase contra el dossier y el texto de las noticias: cifras, fechas, cargos, citas literales, atribuciones. | Corregir el estilo | opus |
| 4 | **Defensor de la neutralidad** | Mide el equilibrio: versiones de Gobierno, oposición y socios; tiempo por partido; adjetivos valorativos; encuadres. | Censurar hechos incómodos | sonnet |
| 4 | **Asesor de cumplimiento** | Revisa YouTube (contenido no auténtico, anuncios en tragedias, elecciones) y la ley: citas breves y atribuidas, sin textos copiados, derecho al honor. | Asesoría jurídica formal | sonnet |
| 5 | **Editor de cierre** | Monta el episodio final: sumario, bloques corregidos, despedida y corrección si la hay. Comprueba la duración (6-8 min) y la coherencia. | Meter hechos nuevos | opus |
| 5 | **Editor gráfico** | Elige para cada escena de texto una foto real, de licencia libre, que corresponda a lo que se narra. Mira cada candidata antes de elegirla. | Fotos de víctimas, de medios o agencias, o con personas ajenas a la noticia | sonnet |
| 6 | **Montador** | Renderiza el vídeo. Si una escena falla (trozo no encontrado, texto largo), lo ajusta y repite. | Cambiar el contenido | sonnet |
| 6 | **Control de calidad** | Mira los fotogramas de cada escena (textos cortados, solapes, huecos), el volumen y la sincronía voz-escena. Aprueba o devuelve al montador. | Opinar del contenido | sonnet |
| 6 | **Diseñador gráfico** | Miniatura de cada episodio hecha para su noticia principal: protagonista recortado con gesto acorde, foto del tema y titular de gancho literal (estilo en `canal/miniatura_referencia.png`). Banner y avatar del canal, una sola vez. | Titulares engañosos o con valoraciones; fotos sin licencia libre o de víctimas | sonnet |
| 7 | **Editor de plataforma** | Título (≤ 70 caracteres), descripción con capítulos y fuentes, etiquetas, hashtags, comentario fijado y la lista de comprobación de YouTube Studio. | Títulos de gancho engañoso | sonnet |
| todas | **Jefe de producción** | Coordina la jornada, lanza a cada puesto con su encargo, decide las vueltas atrás, escribe el parte del día y avisa por Telegram. | Saltarse la mesa de control | (sesión principal) |

**Próximamente** (cuando el canal arranque):
- **Editor de formatos cortos:** 1-2 Shorts verticales al día, que ayudan a llegar a los requisitos de YouTube.
- **Analista de audiencia:** qué temas y formatos retienen más, a partir de las estadísticas de YouTube.

## Reglas de la casa
1. **Nada sale al aire sin pasar la mesa de control.** Un bloque con un CORREGIR vuelve al redactor, como mucho 2 vueltas. Si sigue mal, el bloque se cae del episodio.
2. **Cada dato, con su fuente en pantalla.** Si algo solo lo cuenta un medio, se dice «según X».
3. **Los políticos no se dibujan.** Van en tarjeta: iniciales, cargo verificado, color del partido.
4. **Las tragedias, en tono sobrio:** sin Urni, música baja y sin detalles escabrosos.
5. **El director decide.** La oficina deja el vídeo listo para revisar; publicar lo hace el usuario.
