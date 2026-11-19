# GUÍA ÚNICA DE *El Hoyformativo* — normas que se cumplen SIEMPRE

**Última actualización: 19-nov-2026.**

Esta es **la única guía del canal**. La siguen todos por igual: Claude (sesiones y agentes de `.claude/agents/`), Gemini y
freellmpool en `jornada.py`/`agente_gemini.py`, y cualquier script que genere guion, imagen o vídeo.
- **Si algo de otro fichero (un agente, un prompt, CLAUDE.md, un comentario de código) contradice esta guía, manda esta guía.**
- **Cada decisión nueva del usuario se escribe AQUÍ en el mismo cambio** (y se actualiza la fecha de arriba), sustituyendo
  lo que quede viejo: nunca se añade una norma nueva dejando la antigua contradictoria. La historia de cada decisión está en
  `oficina/HISTORIAL_DECISIONES.md` (solo consulta, no son normas).
- Anexos técnicos (no son normas, son formatos y datos): `oficina/CONTRATOS.md` (ficheros entre fases y catálogo de
  escenas), `oficina/EJEMPLOS_GANCHOS.md` (ganchos elegidos por el director), `archivo/palabras_vetadas.json` (palabras que
  la voz dice mal) y `archivo/coletillas_evitar.txt` (coletillas usadas estos días).

Objetivo: canal diario de política española **monetizable**, **plural**, con **hechos reales y contrastados**, **sin riesgos
legales** y con **tono desenfadado** que enganche. Esto no es asesoramiento jurídico: antes de monetizar, consulta breve con un
abogado de propiedad intelectual.

---

## 1. Identidad
- Canal ***El Hoyformativo***. Lema: «La actualidad, en un minuto» · «Noticias · Contexto · Opinión».
- Logo **EH**: «EH» blanco en círculo azul noche con aro amarillo (`genera_video2.logo`). Nombre «EL HOY FORMATIVO»
  («FORMATIVO» en amarillo). Urni ya no sale en los vídeos ni se nombra.
- Paleta: azul noche `#101C34` (estructura), blanco (texto), amarillo `#FACC15` (palabras clave), rojo `#E52521` (solo
  alerta y polémica, poco).
- Música propia (`musica.py`). Voz: ver §4.

## 2. Veracidad: todo lo que sale es real y contrastado
- Cada dato viene de **al menos dos medios**, o va **atribuido** al único que lo publica. La atribución a medios va **en
  pantalla** («según X» y el recuadro FUENTES), **nunca en la voz**. La voz sí dice quién afirma algo y si no está confirmado
  («sin confirmación oficial», «está previsto»).
- Cada frase se comprueba contra el **texto completo** de las noticias, no solo contra los titulares. Nada de cifras, fechas,
  lugares ni detalles que no estén en las fuentes («por la mañana» sin fuente, no). Si hay duda, se quita.
- **Citas literales intactas**, entre «», con nombre y cargo de quien las dice. Lo literal es solo lo que el medio pone
  entre comillas, nunca su paráfrasis. Nada de citas parciales del periodista.
- **Si lo han dicho, se cita**, haya pruebas o no: va como afirmación o acusación de alguien con nombre, nunca como un hecho,
  y se busca la respuesta del aludido.
- Una sola encuesta no es una tendencia.
- Las imágenes corresponden a lo narrado. Nunca sale una persona que no aparece en la noticia.
- **La foto de una cita es la de QUIEN LA DICE** (no la del destinatario). Mejor sin foto que con la cara equivocada
  (cuidado con apellidos compartidos: García, Sánchez, Díaz…).
- Nunca imágenes realistas generadas con IA de personas reales ni de hechos que parezcan reales.
- Redes: un mensaje en la cuenta **oficial** de un político es una declaración («<nombre>, en X»). Solo cuentas comprobadas.
  Nunca capturas de X: la cita va en nuestra tarjeta.

## 3. Neutralidad y salseo
- **El salseo es el eje del canal:** cruces de declaraciones, reproches, acusaciones y respuestas, con las frases literales de
  más gancho. Cada ataque con su respuesta si la hay; si no la hay, **solo la cita** (nunca «no ha respondido»).
- **Plural:** fuentes de todo el espectro (El País, elDiario.es, Público, La Vanguardia, RTVE, Europa Press, EFE, 20minutos,
  El Confidencial, El Mundo, ABC, La Razón). Se elige la frase más fuerte de **cada** parte; ni la última palabra ni la frase
  más llamativa pueden ser siempre del mismo lado.
- **Humor sobre todos por igual.** Ironía sobre la situación y el absurdo, nunca tomar partido.
  - Prohibido declarar ganadores: «zasca», «le dio un repaso», «humilla», «destroza», «le pone en su sitio», «se retrata».
    («ZASCA» solo existe como etiqueta de formato de un Short, §5.)
  - Si la guasa cae solo sobre un lado, se **reequilibra** (se añade al otro), **nunca se borra**. La mesa de control vela
    por la pluralidad, **no toca el estilo** (sarcasmo, coletillas, frases hechas).
- Los conectores no añaden lo que la fuente no dice: «por eso», «tras», «sin embargo»… solo si el dossier lo dice.
- **Insultos y tacos:** descalificaciones políticas literales sí (entre «»), en cualquier sitio. Insultos vejatorios, solo
  dentro de la pieza: **nunca en los primeros 30 s, la miniatura ni el título**. Tacos, **nunca** («con un insulto que no
  reproducimos»). Títulos y miniaturas, sin tacos ni insultos personales (`apto_anuncios.py`).
- Isabel Díaz Ayuso tiene mucho gancho: si ha dicho algo relevante, sale, siempre con el mismo trato que los demás.

## 4. Guion y voz
### Quién escribe
- **El guion lo escribe SIEMPRE Claude Opus** (largo y Shorts). Gemini y freellmpool pueden preparar material, pero no el
  texto final. Cada Short usa **solo su propio contexto** (nada de material de otro Short o pieza).

### Tono «Vikingo Blanco / La Pulla»
- Español de España, desenfadado, coloquial, como contándoselo a un amigo en un bar; plural (ver §3). Un guion **plano** de
  lector de titulares es un fallo tan grave como el partidismo.
- Verbos coloquiales («suelta», «va y dice», «le contesta», «se queda tan ancho») en vez de «aseguró», «afirmó», «por su parte».
- Conectores orales («Mira…», «Vale…», «A ver…», «Y claro…», «Pues resulta que…», «Agárrate…»), segunda persona de vez en
  cuando («fíjate», «imagínate»), complicidad con el espectador.
- **1-2 coletillas de la paleta por pieza y por Short** (abajo), adaptadas al contexto, bien colocadas, sin amontonarlas.
  Cada coletilla sale **una sola vez por vídeo** y **no se repite hasta pasados 5 días** (`coletillas.py`).
- La **corrección** (si la hay) va honesta y directa, sin chascarrillos.

### Estructura de cada pieza y de cada Short
- **Gancho primero:** la frase literal de más impacto (3-12 palabras) abre el Short y cada pieza; luego quién la dice, a quién,
  el resto de la cita y el contexto.
- **El gancho, una sola vez:** ni la entrada ni la cita que sigue lo repiten; si la cita empieza por el gancho, después va
  solo el resto. Enlace afirmativo y variado («Y remata:», «Y sigue:», «Y añade:»), nunca «¿Por qué?» ni siempre la misma
  fórmula.
  - Mal: «Estamos como el perro del hortelano». Sánchez se compara con el perro del hortelano. ¿Por qué?: «Estamos como el
    perro del hortelano, el PP y Vox ni regulan ni dejan regular».
  - Bien: «Estamos como el perro del hortelano». Pedro Sánchez tira del refranero, y remata: «el PP y Vox ni regulan ni dejan
    regular».
- **NADA se dice dos veces:** cada dato, cita, idea y muletilla sale una sola vez (en la pieza, en el Short y en el episodio
  entero). Si la entrada ya cuenta quién dice qué, el contexto no lo repite; la réplica ya dicha no se anuncia otra vez; nada
  de «según él» dos veces ni «lo suyo… lo suyo». Lo mide `shorts_guion.repeticiones`; si repite, vuelve a Opus.
- Cierre de los Shorts: pregunta de sí o no **nombrando a quien dijo la frase** («¿Tiene razón Ayuso?»), sin tomar partido,
  y «Te leo en comentarios» + suscríbete.

### La voz: Tristán HD «1,6» enérgica
- **Tristán HD de Azure** (`es-ES-Tristan:DragonHDLatestNeural`), **temperatura 1,6**, velocidad normal, filtro «radio»
  (`voz.py`). Licencia comercial. **Sin voz de reserva en producción:** si Azure falla, se reintenta y, si sigue, no se sube
  nada (edge-tts no tiene licencia comercial; solo pruebas a mano). Ni voz propia ni clonada.
- El guion se escribe **para esa energía**: ritmo, frases algo más cortas y punzantes, arranques rápidos, verbos de acción.
- **Sin preguntas en el cuerpo** (Tristán no las entona): la única pregunta es la final. En el cuerpo, en afirmativo.
- **Sin chascarrillos de UNA palabra** tras una cita («Toma.», «Ahí va.»): coletillas más largas y con gancho.
- **Fluidez:** frases de longitud variada; nunca ráfagas de frases de una palabra («Un voto. Un voto.») ni frases kilométricas
  sin comas. Comas, puntos y puntos suspensivos donde una persona haría pausa. Ideas enlazadas con conectores, sin frases sin
  verbo ni dos puntos encadenados. Nunca se recortan conectores para ganar segundos.
- **Compatibilidad con Tristán:** cifras en **dígitos** («35 a 34», «el 41 por ciento»); nombre completo la primera vez y
  luego el apellido; siglas raras desarrolladas la primera vez (las que lee mal se corrigen solas con `voz.SIGLAS`); una
  exclamación o interrogación por frase; texto plano, sin Markdown, sin paréntesis, barras ni direcciones web; nada de «.:».
- Antes de montar, **prevuelo de la voz** (`prevuelo_voz.py`): si un oído (Gemini/OpenAI y Whisper) marca algo que no suena
  natural, se reescribe con Opus y se repite. Las palabras descartadas van a `archivo/palabras_vetadas.json` y **no se usan**.

### Ejemplo de calibración
Entrada: «Ayuso en redes: "Espero que a partir del 29 de noviembre haya una huelga eterna para el PSOE". Sayas pregunta en la
Diputación Permanente si "la resaca de tanta gamba" impidió a los sindicatos ver la realidad.»
Salida: «Vale, ojo a la frase del día. Isabel Díaz Ayuso, en sus redes, justo después de la huelga del 11: «Espero que a partir
del 29 de noviembre haya una huelga eterna para el PSOE». Una huelga eterna… que ya no es un día ni dos, es para siempre. Y la
cosa acabó en la Diputación Permanente, donde se lió. Sergio Sayas, del PP, preguntó si «la resaca de tanta gamba» no había
dejado a los sindicatos ver la realidad… la resaca de la gamba, en pleno Congreso, con dos tazas.»

### Paleta de coletillas y chascarrillos (lista del usuario; adaptar pronombres al contexto, ritmo normal, sin tacos)
- Esto es un sindiós de proporciones bíblicas.
- Esto es un sindiós.
- Estoy más perdido que un pulpo en un garaje.
- Se me está poniendo cara de boniato.
- Esto tiene una pinta regulera.
- Me hallo en una encrucijada existencial.
- Estoy más tieso que la mojama.
- Qué fantasía más turbia.
- Esto es una bacanal de sinsentidos.
- Se me está poniendo el cuerpo como un botijo.
- ¡Qué escándalo de criatura!
- Estoy más agobiado que un gremlin en una sauna.
- Esto es más raro que un ciervo con flequillo.
- Menudo percal.
- Estoy en un sinvivir de categoría.
- Qué despropósito de dimensiones industriales.
- Se ha liao la mundial en el convento.
- ¡Al turrón!
- ¡Venga, que nos vamos!
- Esto es así y punto pelota.
- ¡Qué movida más gorda!
- ¡Ni tan mal!
- Se nos está yendo de las manos.
- ¡Virgen del camino seco!
- ¡Qué barbaridad!
- ¡Estamos apañados!
- Cada palo que aguante su vela.
- Quien mucho abarca, poco aprieta.
- A perro flaco, todo son pulgas.
- El que se pica, ajos come.
- Se barruntaba el percal.
- No se veía venir el estacazo.
- Estaba el asunto más negro que el sobaco de un grillo.
- Ni el tato daba un duro.
- Se ha quedado la cosa como un solar después de la guerra.
- No había por dónde meterle mano al asunto.
- Se ha descubierto el pastel y encima estaba revenío.

Fuera de la paleta, para siempre: tacos («me cago en la leche», «coño», «del copón», «almorrana»…) y lo que esté en
`archivo/palabras_vetadas.json`.

## 5. Formatos y producción diaria
- **Cada día: 1 vídeo largo + hasta 3 Shorts.** Primero los Shorts, luego el largo. Jornada automática a las **10:30 de
  Madrid** (`jornada.sh` → `jornada.py`; Claude solo entra si fallan Gemini/freellmpool o un control de calidad); a las
  14:30 aviso si el vídeo no está subido.
- **Vídeo largo «todo breves», 2:30-3:00** (410-500 palabras): 5-6 piezas de 20-30 s (55-80 palabras, 2-3 pasos), cada una
  un enfrentamiento que abre con su gancho literal, réplica si la hay, sin antecedentes largos; transiciones de una frase.
  La primera pieza, el cruce más fuerte del día (redes primero). **Sin sumario narrado** (el sumario de `episodio.json` solo
  alimenta miniatura y título), sin sección de breves aparte, nada de noticias generalistas. Corrección (si la hay) al final,
  antes de la despedida: «Si te ha servido, suscríbete y dale a la campanita. Y si no, también, hombre, que no cuesta nada.
  Gracias por vernos. Mañana, más.» Tragedias: tono sobrio, sin ganchos llamativos, música baja.
- **Shorts de 25-40 s** (40-60 s si reúnen varios ganchos con un hilo común, sin numerarlos), uno por frase con más gancho
  (sobre todo de redes), de partidos distintos, cita entera literal de 4+ palabras. Etiqueta de formato arriba a la derecha:
  ÚLTIMA HORA (solo hechos de hoy), POLÉMICA, ZASCA o ANÁLISIS. Cierre de 3-4 s con la pregunta (§4).

## 6. Imagen
- **Escenas de ambiente** de línea clara a **color pleno**, animadas (cámara 2,5D `motion_comic`; **LTX no**, inventa caras),
  a pantalla completa, **sin personas en primer plano** y **siempre de lugares políticos**: Congreso, Senado, Moncloa, sedes,
  parlamentos, ayuntamientos, ministerios, salas de prensa, atriles, urnas o avenidas institucionales sobrias. Nunca playas,
  puertos, terrazas, mercados ni calles turísticas. Primero imagen nueva con FLUX (se guarda en `biblioteca_ambiente`); si
  falla, la biblioteca; OpenAI solo como excepción los días sin cuota.
- **Siempre un personaje en la escena:** el recorte real (sin fondo) de quien dice la cita o, si no hay cita, de la persona de
  la que se habla. Primero los recortes curados del usuario, luego `fotos.mejores` / `biblioteca_fotos`. Largo: una sola
  persona, abajo a la izquierda, con el rótulo de nombre y cargo al lado del hombro (cargo real, nunca notas internas); en un
  relevo sale la anterior y entra la nueva, nunca dos caras fundidas. Shorts: la persona arriba y la cita debajo.
- **Karaoke SIEMPRE** (largo y Shorts), estilo TikTok: Inter Black, blanco con palabras clave (citas, nombres, cifras) en
  amarillo, borde negro grueso, sincronizado con la voz; como mucho 3 líneas y sin tapar la etiqueta ni el rótulo.
- **Variedad:** ninguna foto ni viñeta se repite en 7 días (`variedad.py`); ninguna imagen se repite entre los Shorts del día.
- **Fotos siempre a color**, en alta resolución y con licencia (§8). Sin foto libre de una persona: ilustración de su ámbito,
  sin caras inventadas.
- **Miniatura del largo:** la genera OpenAI con la frase gancho incrustada y un fondo del contexto, sin caras inventadas, más
  el **recorte real de quien dice la frase** a la derecha y una **etiqueta roja** con quién lo dice. Respaldo: titular gigante
  en 3 líneas con brochas (`miniatura_titular`). **Los Shorts no llevan miniatura**: la elige el usuario en Studio.
- Todo lo hecho con IA lleva «Ilustración IA» en pantalla.

## 7. Monetización (todo lo que se sube tiene que serlo)
- **Riesgo n.º 1: «contenido no auténtico».** Guion original cada día con narrativa propia, estructura variable, imágenes que
  no se repiten, metadatos únicos.
- Licencia comercial de todo: voz Azure, música propia, fotos libres (§8), FLUX (Apache 2.0) u OpenAI, tipografías OFL. Si
  falta algo, **no se sube**.
- Anuncios: nada de detalles gráficos de víctimas, cuerpos ni violencia; miniatura y título sin morbo ni gritos.
- Elecciones: nunca dar como cierto algo falso sobre cómo, cuándo o dónde votar.
- IA: la descripción dice que hay voz sintética y ayuda de IA; si una imagen dibuja a una persona real, el vídeo se marca como
  «contenido alterado o sintético» (`subir.py`). Las descripciones dicen que las frases están comprobadas y que el equipo
  editorial revisa antes de publicar (es verdad: publica el usuario).
- Metadatos: vídeo con 35-45 etiquetas y 12-15 hashtags; Shorts con 15-25 etiquetas y 8-12 hashtags; solo de personas y temas
  que salen; títulos con verbos neutros.

## 8. Derechos de autor
- Los hechos se cuentan con **palabras propias**; nunca se lee ni se muestra un artículo, titular o captura de un medio.
- Citas de políticos: cortas, entre «», atribuidas, de declaraciones públicas.
- **Fotos:** solo de licencia libre con crédito en pantalla y en la descripción: CC0, dominio público, CC BY y fuentes oficiales
  que permiten reutilizar citando (Moncloa, Congreso, Senado); CC BY-SA con «foto adaptada» en la descripción. **Nunca** fotos
  de periódicos, agencias (EFE, Europa Press…), Getty ni capturas de televisión, ni con licencia NC o ND. Nunca víctimas ni
  personas ajenas a la noticia.
- Dibujar a una persona con IA solo a partir de fotos CC0, de dominio público o CC BY, y solo por algo que dijo o hizo.
- Música propia: sin reclamaciones de Content ID.

## 9. Proceso y control de calidad
- Mesa de control (verificador, defensor de la neutralidad, asesor de cumplimiento) con APTO/CORREGIR por pieza; prechequeo
  mecánico (citas literales, gancho, tono, coletillas, repeticiones, duración).
- **Antes de entregar cualquier vídeo se miran sus fotogramas.** El control de calidad marca CORREGIR si: el tono es plano;
  falta el karaoke o no es TikTok; una escena sale sin personaje o con la cara equivocada; hay repeticiones; un fondo no es
  político; o se incumple cualquier punto de esta guía.
- **Todo se sube como PRIVADO** (`subir.py`); **publicar es siempre decisión del usuario**. De cada día queda solo la última
  versión (se borra la anterior si sigue privada). **Antes de rehacer algo se comprueba si ya está publicado: lo publicado no
  se toca.**
- Aviso por Telegram al terminar o si algo falla, en lenguaje llano. Nunca se muestran claves ni secretos.
- Cada cambio de código o de esta guía: commit y push a `origin/main` (el servidor es la propia copia de trabajo).

## Fuentes de las normas de YouTube y derechos
- Contenido no auténtico y reutilizado: https://support.google.com/youtube/answer/1311392
- Contenido alterado o sintético: https://support.google.com/youtube/answer/14328491
- Directrices para anunciantes: https://support.google.com/youtube/answer/6162278
- Requisitos del Programa de Socios: https://support.google.com/youtube/answer/72851
- Preguntas frecuentes de Creative Commons: https://creativecommons.org/faq/
- Ley de Propiedad Intelectual (arts. 32 y 33): https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930
