# GUÍA ÚNICA DE *El Hoyformativo* — normas que se cumplen SIEMPRE

**Última actualización: 21-nov-2026 (formato «presentador» SIEMPRE con personajes estáticos; «¡Virgen del camino seco!» vetada; catálogo de políticos con subcarpetas y nombres «NombreApellido»; 21-nov: control de calidad de voz y guion local; la voz no cambia de ritmo en coletillas; voz «A3 + B3»: temperatura 1,2 y diccionario SAPI; «mitin/mitines» fuera de la lista negra al ir en el diccionario; cierre de los Shorts como antes; nunca estirar la voz grabada; «enterarais» escrita con tilde para la voz; pausa al cerrar y abrir las citas de la narración; voz en LECTURA ENTERA como estándar: el guion gestiona las pausas; globos de cita solo con su personaje y nunca superpuestos; nada se sube a YouTube sin el OK del usuario por Telegram; Short de cruce de declaraciones por encargo; 22-nov: voz +8 % de velocidad salvo el cierre; «mitin» fuera del diccionario; el Short de cruce modelo como norma; nada se solapa nunca: relevo limpio en cada cambio de escena).**

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
  - **La palabra «zasca» NO se usa NUNCA** (19-nov-2026, el usuario), en ninguna forma («menudo zasca», «zasca en toda
    regla»…): ni en el guion, ni en pantalla, ni en títulos o etiquetas (la etiqueta de los Shorts es RÉPLICA, §5). Lo
    comprueban `prechequeo.py` y `shorts_guion.vetadas`.
  - Prohibido también declarar ganadores: «le dio un repaso», «humilla», «destroza», «le pone en su sitio», «se retrata».
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

### Escribir para el presentador (formato de §6, desde el 20-nov-2026)
- El narrador es el **presentador**: cuenta, presenta y da paso. Cada **cita literal** (4+ palabras) va **sola, como su propia
  frase**, y **justo antes** se dice quién la dice y a quién («Y Feijóo le suelta a Sánchez:», «Sánchez le contesta:»), nunca
  después («…», dijo Feijóo), porque en pantalla el personaje entra al empezar su cita. Única excepción: el **gancho que
  abre** la pieza o el Short va primero y quién lo dice, en la frase **inmediatamente siguiente** («…». Sánchez ataca a
  Feijóo). En la frase que introduce una cita, que no haya otro posible hablante como sujeto: si el montaje no sabe con
  seguridad de quién es la cita, no saca a nadie.
- **Cruce:** ataque literal → puente muy corto (≤ 12 palabras: «Y Sánchez le devuelve:») → réplica literal → el presentador
  vuelve con el chascarrillo o sigue. Nada de narración larga entre el ataque y la réplica (si no, se rompe el cruce).
- Tras cada cita o cruce, **una frase del presentador** (chascarrillo de la paleta o seguir el hilo) antes de la siguiente
  cita: así el vídeo alterna presentador y personajes con ritmo. **Las pausas las pone el guion** con su puntuación (punto,
  coma, dos puntos, puntos suspensivos): la voz lee de corrido lo que está escrito (ver «Lectura entera»).
- Una cita = una persona: no mezclar dos voces dentro de las mismas comillas.

### El Short de cruce modelo (22-nov-2026, el usuario: «ha salido perfecto, guarda las directrices como norma para todos»)
Referencia: `dia/2026-11-22/shorts/short_1.json` (Morant y las «cuatro bofetadas»). Todo Short o pieza con cruce sigue esto:
- **Abre con la frase literal que lo desata**, entera, de la fuente más fiel (transcripción del vídeo o de la noticia, nunca
  la paráfrasis de un rival); quién la dice, en la frase siguiente y muy breve («Lo dijo Morant en un mitin.»).
- **Dos cruces como mucho, de dos personajes cada uno**: el que lanza la frase a la IZQUIERDA y el que replica a la DERECHA,
  con un puente de ≤ 12 palabras que nombra al que replica justo antes de su cita («Ester Muñoz, del PP:», «Y Morant le
  contesta por escrito:»). Entre un cruce y el siguiente, el **presentador** da el contexto (quién es, dónde y cuándo lo dijo,
  si rectifica o no) con una coletilla. El segundo cruce puede ser la réplica de un tercero y la **contrarréplica** del
  primero, que así tiene su voz (equilibrio).
- **Solo personajes con imagen** en `Imagenes/Políticos`; de los demás no se elige cita (no se mete un cruce sin cara).
- **Remate neutral** del presentador sin declarar ganador («Y aquí cada uno entiende la metáfora a su manera.») y **pregunta
  corta con el nombre** de quien dijo la frase («¿Se pasó Morant?»): tiene que caber en una línea del cierre.
- **≤ 60 s** (con la voz a +8 %, unas 145 palabras con el cierre); si pasa, se quita narración, nunca citas.
- **En pantalla**: los dos globos del cruce, uno arriba (izquierda) y otro debajo (derecha), sin pisarse entre ellos ni
  tapar a los personajes ni al subtítulo; cada globo con el cargo limpio y **su fuente** («según The Objective», «según X
  (@cuenta)»: `fuentes_citas`). Se revisan los fotogramas de cada cruce antes de mandarlo.

### La voz: Tristán HD «1,2», LECTURA ENTERA (estándar del usuario desde el 21-nov-2026) + diccionario de pronunciación
- **Tristán HD de Azure** (`es-ES-Tristan:DragonHDLatestNeural`), **temperatura 1,2**, **velocidad +8 %** (22-nov-2026, el usuario: «un punto más de
  velocidad»; `voz.AZURE_VEL`, la misma para toda la pieza), filtro «radio» en
  todo el vídeo, coletillas incluidas (`voz.py`).
- **Lectura entera** (decisión del usuario del 21-nov-2026, estándar para todos los vídeos): la voz lee el guion **de
  corrido, de una vez por pieza** (un Short entero; en el largo, cada sección) y **el guion gestiona las pausas** con su
  puntuación. Nada de partir la voz por frases, por exclamaciones ni por citas, ni de corregirle la velocidad, ni de
  estirar o encoger el audio, ni de meter `<prosody>`: todo eso se probó ese día y sonaba con distintos ritmos o con eco.
  El montaje saca de los tiempos de cada palabra cuándo entra y sale cada personaje (`voz.LECTURA_ENTERA`,
  `presentador._locuta_entero`). Si algo suena acelerado o arrastrado, se arregla **en el guion** (una coma, un punto, un
  punto y seguido, partir la frase), nunca en el audio.
- **Pausa en las comillas:** medio segundo al cerrar una cita y 0,3 s antes de abrirla tras «:» (`voz.pausas_citas`,
  `<break>` de la propia voz). Sin ella, la frase siguiente (una coletilla, por ejemplo) sonaba pegada a la cita.
- **Cierre de los Shorts como siempre:** la pregunta final y «Te leo en comentarios. Y dale a suscribirte, que he visto
  que aún no lo has hecho» van aparte, con su estilo de siempre (temperatura 1,6 y velocidad normal, sin el +8 %; `voz.CIERRE`,
  `voz.AZURE_TEMP_CIERRE`).
- **Diccionario de pronunciación** (`voz.PRONUNCIA`): las palabras que Tristán acentúa o dice mal se le dictan con el
  alfabeto fonético **SAPI** de Azure (la tónica con «1» tras la vocal; p. ej., «mitines» = `m i t i 1 n e s`; en el diccionario: mitines; «mitin» salió el 22-nov-2026 porque con SAPI sonaba «mitón» y sin entrada la dice bien). Si con SAPI no sale, se le **escribe** la palabra de otra forma solo para la voz (`voz.ESCRIBE`, p. ej. «enterarais» → «enterárais», aprobado por el usuario el 21-nov-2026); el texto en pantalla no cambia. Cada
  palabra que el usuario oiga mal se añade ahí y se le manda la prueba por Telegram.
  **Solo puntual** (decisión del usuario, 21-nov-2026): nunca para todas las palabras; dictar todo quita naturalidad.
  Las tomas aprobadas se conservan: añadir una palabra al diccionario solo vuelve a grabar los trozos que la llevan. Licencia comercial. **Sin voz de reserva en producción:** si Azure falla, se reintenta y, si sigue, no se sube
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
- **Control de calidad de VOZ Y GUION** (21-nov-2026, el usuario: «que la voz suene lo más humana posible»; es control del
  guion porque la voz lee lo que el guion escribe). En los Shorts y en el largo, antes de montar, `prevuelo_voz.py` genera la
  locución tal como sale en el vídeo (por tramos, con sus pausas) y la escucha `voz_calidad.py`, **100 % local y gratis**:
  - **Pronunciación:** fonemas oídos (wav2vec2) frente a los esperados (espeak-ng); y Whisper «small» sin el guion delante
    (si entiende otra palabra, p. ej. «ladrillazo» → «trilazova», o la oye con poca seguridad).
  - **Ritmo y entonación:** tramo de más de ~5 s y 15 palabras sin respirar (la voz se «come» un punto o una coma), tramo
    con la entonación plana, frase atropellada (más de ~8 sílabas por segundo) o arrastrada, y silencios raros a mitad de
    frase. Para cada uno propone **dónde poner la pausa**.
  - Lo que se puede reescribir vuelve a **Opus**: otra palabra, una pausa (coma, dos puntos, punto y seguido) o partir la
    frase; las citas «» no se tocan (si Opus cambia una, vuelve el texto anterior). Se escucha otra vez y lo que quede, al
    parte. Lo que está dentro de una cita o es un nombre propio no se reescribe: se avisa en el parte.
  - Gemini, si tiene cuota, es un oído más; OpenAI (de pago) ya no se usa.
  - **Mismo ritmo en todo** (21-nov-2026, el usuario: «no quiero que la voz cambie de ritmo con las frases hechas ni
    coletillas»): el control marca como «cambio de ritmo» cualquier tramo que vaya un 18 % más rápido o más lento que el
    resto, y se arregla **en el guion** (puntuación, partir la frase), porque la voz lee de corrido (lectura entera).
  - **El oído del usuario manda:** el 21-nov suspendió las cinco pruebas que el control daba por buenas o malas («mitines»
    mal acentuado; «¡Venga, que nos vamos!» más rápido que el resto). Las pruebas de sonido se le mandan por Telegram
    (`notifica.py FECHA --audio ruta.mp3 "texto"`) antes de dar por bueno un cambio de voz.
  - El control no lo caza todo (el acento o un tono raro de una palabra bien dicha, como «mitines»), así que lo que el
    usuario oiga mal se arregla primero con el **diccionario de pronunciación** (`voz.PRONUNCIA`, prueba por Telegram); si
    no tiene arreglo (una expresión entera que suena forzada), va a `archivo/palabras_vetadas.json` y **no se usa**
    (tampoco se eligen citas que la lleven). «Mitin/mitines» salió de la lista negra el 21-nov-2026 al entrar en el diccionario.

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

Fuera de la paleta, para siempre: «zasca» en cualquier forma, «ladrillazo va, ladrillazo viene» (la voz no la lee bien, 20-nov-2026), «¡Virgen del camino seco!» (queda forzada, 20-nov-2026), tacos («me cago en la leche», «coño», «del copón», «almorrana»…) y lo que esté en
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
- **Día monográfico por encargo del director** (20-nov-2026, el usuario): si `encargo.json` trae `monografico`, el largo y
  los Shorts de ese día tratan SOLO ese tema (mismo formato «todo breves» de 2:30-3:00, sus bloques = sus cruces), con
  equilibrio estricto de frases y tiempo entre las partes. Los Shorts pueden ser de **«mejores frases»** de una persona
  (`shorts_personas` → `mejores_frases`): 2-3 frases suyas literales del tema, cada una con su contexto breve, sin declarar
  ganador; si se hace de una, se hace igual de la otra parte. Todas las demás normas no cambian.
- **Short de cruce de declaraciones por encargo del director** (21-nov-2026, el usuario): si `encargo.json` trae `cruce`
  (tuits o frases con su enlace), cada frase se comprueba por separado (`encargo.py`: autor y texto literal por oEmbed) y
  solo se usan las comprobadas; con `busca_x` la recogida de ese día trae además los tuits recientes de esas cuentas y la
  búsqueda en X (solo de cuentas oficiales, nunca anónimas) y el tema entra en los dossieres (`claves`). El primer Short es
  ese cruce: quien lanza la frase, a la izquierda con su cita; quien replica, a la derecha con la suya; el presentador da el
  contexto entre medias, con la contrarréplica si la hay y sin declarar ganador. Su noticia entra también en el largo. Si
  varias fuentes citan la frase con palabras distintas, se usa la literal (vídeo o noticia) y nunca una paráfrasis.
  Si el director pide el Short antes de la jornada, se monta a mano y se apunta en `shorts_hechos`: la jornada lo
  conserva tal cual y hace los demás Shorts de otros temas. En el globo, la fuente de cada cita (`fuentes_citas`: X,
  medio) y el cargo limpio, sin notas internas.
- **Shorts de 25-40 s** (40-60 s si reúnen varios ganchos con un hilo común, sin numerarlos), uno por frase con más gancho
  (sobre todo de redes), de partidos distintos, cita entera literal de 4+ palabras, en el formato presentador (§6). Etiqueta de formato arriba a la derecha:
  ÚLTIMA HORA (solo hechos de hoy), POLÉMICA, RÉPLICA o ANÁLISIS. Cierre de 3-4 s con la pregunta (§4).

## 6. Imagen: formato «presentador» (SIEMPRE, desde el 20-nov-2026, decisión del usuario)
Motor: `presentador.py` (`largo` horizontal 1920×1080 y Shorts verticales 1080×1920). Lo de antes (escenas de ambiente con
FLUX, `biblioteca_ambiente`, fotos de `fotos.mejores`/`biblioteca_fotos`, Polaroids, `render_ambiente.py`) **queda descartado
y no se usa hasta nueva orden del usuario.**
- **Imágenes: SOLO las de `Imagenes/`**, que amplía el usuario:
  - `Imagenes/Fondos`: se usa **el fondo que mejor corresponde a cada noticia** (Moncloa, Congreso, hemiciclo, Parlamento
    Europeo, podio de prensa…); en el largo, uno por pieza, sin repetir en piezas seguidas; cambia con un fundido.
  - `Imagenes/Presentador`: el **presentador** (personaje ficticio). Con varias poses (también láminas de varias poses), va
    cambiando de pose cada vez que vuelve.
  - `Imagenes/Políticos` (y sus subcarpetas, p. ej. `Nuevas/`): cada político **sin fondo** (PNG transparente), nombrado
    por la persona: `Apellido_….png`, `NombreApellido.png` o `Nombre Apellido.png` (la clave es el apellido, la última
    palabra; si el archivo trae nombre de pila y la cita también, tienen que coincidir, para no confundir apellidos comunes;
    con apellidos que llevan varios políticos —Montero, Muñoz, García…, `presentador.APELLIDOS_AMBIGUOS`— la cita tiene que
    traer el nombre de pila o no sale imagen).
    Si hay varias imágenes de la misma persona, se alternan. Las imágenes con fondo (p. ej., grupos) no se usan; si el
    fondo transparente viene «dibujado» (cuadros grises o blanco), se recorta con rembg (`isnet-general-use`), se revisa
    sobre fondo de color y el original se guarda en `Imagenes/_originales/`.
- **El presentador está a la IZQUIERDA mientras el narrador lee el guion** (es quien narra), con el subtítulo karaoke de lo
  que dice.
- **Cita literal de un personaje:** el presentador **sale de forma elegante** (fundido + desliz, nunca brusco) y **entra el
  personaje** (QUIETO en pantalla: sin balanceo ni «respiración»; solo se mueve al entrar y salir) con su frase literal en un bocadillo (karaoke: la palabra que suena en amarillo) y su rótulo rojo con nombre,
  cargo real y «según [medio]». Citas de menos de 4 palabras se quedan en la narración.
- **Cruce de declaraciones:** el que ataca **se queda a la izquierda** y **el que replica entra por la DERECHA** con su
  réplica. Los dos bocadillos se ajustan al hueco entre ellos sin taparse ni tapar a nadie (en el largo, el del ataque arriba
  y la réplica abajo; en los Shorts, los dos encima de los personajes). Al acabar sus citas **salen y vuelve el presentador**
  con su chascarrillo o siguiendo el guion. Nunca dos figuras fundidas en el mismo sitio: primero sale una y luego entra la otra.
- **Ritmo:** la voz lee de corrido cada pieza (lectura entera, §4) y los cambios de imagen caen en las pausas que marca el
  guion; entre noticias del largo, 0,5 s.
- **Globos de cita SIEMPRE con su personaje** (usuario, 21-nov-2026): una cita con globo sale solo con la imagen de quien
  la dice. **Sin imagen** de esa persona en `Imagenes/Políticos`, la cita la lee el presentador **sin globo** (como
  narración, con subtítulo) y se avisa al usuario por Telegram de la imagen que falta (`presentador.sin_imagen`). Nunca
  el presentador con un globo de otro, ni una foto de otra fuente ni una cara inventada.
- **Nunca se adivina quién dice una cita** (22-nov-2026, fallo real: «Vamos a seguir votando al PSOE», de ocho veteranos
  socialistas, salió con Sánchez, y una ironía de Urtasun salió con Rufián): si la frase que la introduce no nombra a un
  único hablante con imagen, la lee el presentador sin globo. Mismo apellido no es misma persona («Cayetana Álvarez de
  Toledo» no es «Pepe Álvarez»). En el guion, quien dice la cita se nombra justo antes de ella.
- **Nunca dos globos superpuestos ni un globo encima de un personaje:** el globo de una cita se va antes de que entre el
  de la siguiente; la misma persona escrita de dos formas («Feijóo» / «Alberto Núñez Feijóo») es una sola figura (antes
  salía dos veces, una a cada lado, con los globos encima).
- **Nada se solapa, NUNCA (usuario, 22-nov-2026, «importantísimo»):** ni personajes entre ellos (tampoco el presentador
  con el personaje que entra), ni globos, ni subtítulos con globos. En cada cambio de escena (presentador ↔ personajes,
  o de un cruce a otro) **sale uno del todo y después entra el otro**: si la voz no deja hueco, se alarga el silencio
  (`presentador.HUECO_ESCENA`, 0,85 s, lo mete el montaje solo) y el guionista puede poner punto y aparte para dar ese
  respiro. El subtítulo del puente dentro de un cruce va en el hueco del globo derecho y se retira antes de que entre.
  Todo tiene que verse dinámico y natural: relevo limpio, sin esperas largas. Se revisan los cambios de escena
  fotograma a fotograma (cada 0,15 s) antes de mandar el vídeo.
- **Largo:** logo «EL HOYFORMATIVO» arriba a la derecha y título de la pieza arriba a la izquierda. **Shorts:** cabecera del
  canal con la etiqueta de formato, kicker rojo, personajes en la mitad de abajo, bocadillo o subtítulo encima, y cierre con
  la pregunta y suscríbete.
- **Sin fondos borrosos.** Una viñeta oscura suave en los bordes para que se lea el texto.
- **Miniatura del largo:** la genera OpenAI con la frase gancho incrustada y un fondo del contexto, más el recorte de quien
  dice la frase y una etiqueta roja con quién lo dice. **Los Shorts no llevan miniatura**: la elige el usuario en Studio.

## 7. Monetización (todo lo que se sube tiene que serlo)
- **Riesgo n.º 1: «contenido no auténtico».** Guion original cada día con narrativa propia, estructura variable, imágenes que
  no se repiten, metadatos únicos.
- Licencia comercial de todo: voz Azure, música propia, imágenes de `Imagenes/` (las aporta el usuario para uso en el canal),
  OpenAI (miniatura), tipografías OFL. Si falta algo, **no se sube**.
- Anuncios: nada de detalles gráficos de víctimas, cuerpos ni violencia; miniatura y título sin morbo ni gritos.
- Elecciones: nunca dar como cierto algo falso sobre cómo, cuándo o dónde votar.
- IA: la descripción dice que hay voz sintética y ayuda de IA, que los fondos, el presentador (ficticio) y las ilustraciones
  de los políticos son de IA y que las frases que se les atribuyen son citas literales publicadas por los medios. Como salen
  personas reales ilustradas, el vídeo se marca como «contenido alterado o sintético» (`subir.py`). Un personaje ilustrado
  **solo «dice» frases literales suyas comprobadas** (§2), nunca una paráfrasis. Las descripciones dicen que las frases están comprobadas y que el equipo
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
- Las ilustraciones de políticos son las de `Imagenes/Políticos` (las aporta el usuario); se usan solo para mostrar algo que
  dijeron de verdad (frase literal comprobada) y nunca para hacerles «decir» o «hacer» otra cosa.
- Música propia: sin reclamaciones de Content ID.

## 9. Proceso y control de calidad
- Mesa de control (verificador, defensor de la neutralidad, asesor de cumplimiento) con APTO/CORREGIR por pieza; prechequeo
  mecánico (citas literales, gancho, tono, coletillas, repeticiones, duración).
- **Antes de entregar cualquier vídeo se miran sus fotogramas.** El control de calidad marca CORREGIR si: el tono es plano;
  falta el karaoke o no es TikTok; una escena sale sin personaje o con la cara equivocada; hay repeticiones; un fondo no es
  político; o se incumple cualquier punto de esta guía.
- **Nada se sube a YouTube sin el OK del usuario** (21-nov-2026, para no agotar el límite diario de subidas con
  versiones que luego se rehacen): la jornada le manda cada vídeo por Telegram (`notifica.py FECHA --pide-ok largo|shorts`)
  y solo cuando lo aprueba se sube (`subir.py FECHA`, `subir.py FECHA shorts [N]`). La versión anterior se borra después
  de subir la nueva, nunca antes.
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
