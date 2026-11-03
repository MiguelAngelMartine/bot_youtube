# Libro de estilo de *El Hoyformativo*

## Identidad (no cambia nunca)
- **Canal:** El Hoyformativo. **Presentadora:** Urni, la urna.
- **Voz (elegida por el usuario el 2-nov):** Tristán HD de Azure, velocidad normal, **sin cambios de entonación** en ningún bloque (sin voz de reserva: si Azure falla, no se sube nada, porque todo tiene que ser monetizable). Las pausas entre frases se recortan a 0,40 s y ante comas largas a 0,24 s, con fundido (`voz.py`, modo «plano»).
- **Lema:** «La política española del día, en claro» (desde el 1-nov-2026, con el nombre El Hoyformativo).
- **Colores:**
  - rojo `#C8102E`, amarillo `#F1BF00`, azul noche `#0C1426`;
  - tipografía Segoe UI (Black para titulares, Semibold para textos).
- **Miniatura (elegida por el usuario el 1-nov):** estilo de `canal/miniatura_referencia.png`, hecha para la noticia principal de cada vídeo:
  - foto real del tema de fondo y el protagonista recortado, con filo blanco fino y un gesto acorde con la noticia;
  - titular enorme en blanco con una palabra en amarillo-oro (relieve, contorno e inclinación) y etiqueta roja con el hecho;
  - gancho en la forma, literal en el fondo: citas textuales o hechos del vídeo, sin valoraciones; en tragedias, la versión sobria.
- **Estructura fija:**
  1. **arranque directo (decisión del usuario del 1-nov):** sumario de titulares a pantalla completa con el estilo de la miniatura, sin presentación ni saludo, una frase contundente por bloque y «Vamos con ello.»;
  2. golpe de marca (`marca.py`, 2,6 s): logo, nombre del canal, fecha y sintonía, coreografiados con el sonido y encadenados con el primer bloque;
  3. bloques numerados «NN / TT»;
  4. breves;
  5. despedida a pantalla completa (`cierre.py`): «Esto ha sido todo por hoy. Si te ha servido, suscríbete y activa la campanita para no perderte el resumen de mañana. Gracias por vernos. Mañana, más.», con el botón de suscripción y la campana animados al decirlo;
  6. cierre de 8 s para la pantalla final de YouTube: la mitad derecha queda libre para el vídeo sugerido y el botón de suscripción de YouTube Studio.
- Si hay **corrección** de un episodio anterior, va justo después del sumario con el rótulo «CORRECCIÓN» y en tono sobrio.

## La voz de Urni
- Cercana pero informativa. Una idea por frase y 30 palabras como mucho, pero **escrita para el oído**, no como un telegrama (ver «Escribir para el oído»).
- Cada bloque empieza con un **gancho** de 3-8 palabras («¿Qué falló?», «La oposición aprieta», «Y abre otro frente»).
- Cada bloque tiene, por este orden: qué ha pasado → quién dice qué (todas las partes) → **contexto** (por qué importa, de dónde viene) → **qué pasa ahora** (próximos pasos con fecha si la hay).
- Los números se escriben **con letras** en el texto que se lee («sesenta y nueve», «dos mil veintitrés»), para que la voz los pronuncie bien. En pantalla van con cifras.
- Las citas textuales se leen sin anunciar las comillas; en pantalla van entre «». Siempre breves (una frase) y atribuidas con nombre y cargo.
- **Prohibido:**
  - adjetivos valorativos propios («escándalo», «vergonzoso», «histórico»);
  - especular;
  - «al parecer» sin fuente;
  - frases hechas de tertulia;
  - dar por cierta una sola encuesta;
  - detalles escabrosos de víctimas.
- **Atribución:**
  - cuando solo lo publica un medio, «según El País» **en el texto de pantalla** de la nota, nunca en la voz (decisión del 1-nov-2026: la voz no nombra medios para no estar citando fuentes continuamente). La voz sí dice quién afirma algo y si no está confirmado («sin confirmación oficial», «está previsto», «hay versiones distintas»);
  - sin atribución solo si está CONTRASTADO (2+ medios de líneas distintas);
  - las acusaciones, siempre atribuidas.
- **Duración:** el episodio entero, 7-9 min (unas 1.000-1.300 palabras; con Tristán, ~2,75 palabras por segundo). Un bloque principal, 65-120 s (170-320 palabras). Desde el 2-nov-2026 el usuario prefiere algo más de duración si a cambio el texto fluye: nunca se quitan conectores para ahorrar segundos. Un breve, 10-20 s.
- **Tono «sobrio»** (muertes, accidentes, atentados): sin ganchos llamativos, música baja. (Desde el 2-nov-2026 Urni no sale en ningún vídeo; solo el logo.)

## Escribir para el oído (decisión del usuario del 2-nov-2026)
El texto se escucha, no se lee: tiene que fluir como lo contaría un buen locutor de radio, sin finales de frase abruptos.
- **Une las frases con conectores** cuando la relación entre ellas existe: «además», «también», «mientras tanto», «por su parte», «a su vez», «de hecho», «eso sí», «aun así», «por ahora», «hasta ahora», «después», «antes», «al mismo tiempo». Cada paso (`di`) continúa al anterior; no empieza de cero.
- **Nada de frases sin verbo** ni sueltas: no «Otra ante el Supremo, contra Puente.», sino «y presentó otra ante el Supremo contra Puente». No «Cincuenta y dos por huella y cuatro por ADN.», sino «cincuenta y dos de ellas, por la huella dactilar, y cuatro, por ADN».
- **Varía la longitud**: alterna frases medias (15-25 palabras) con alguna corta para el golpe. Tres frases cortas seguidas suenan a telegrama.
- **Sin dos puntos encadenados** («Vox fue primero: Abascal…»): en voz suenan a corte. Mejor «Vox se adelantó, y Abascal lo anunció…».
- **Listas de personas**, en una frase natural y con «y» al final, sin punto y coma: «También la piden Abascal, Verónica Martínez Barbero, del Frente Amplio, y Míriam Nogueras, de Junts».
- **Nada que no se pueda leer en voz alta**: ni direcciones web («Moncloa.es»), ni paréntesis, ni barras, ni siglas raras sin explicar la primera vez.
- **Transiciones entre bloques**: el primer paso de un bloque enlaza con el anterior («Y del luto pasamos a la campaña», «Mientras tanto, en Barcelona…»), sin saludos ni muletillas.
- **Límite de neutralidad (obligatorio):** un conector no puede añadir lo que la fuente no dice. «Por eso», «así que», «como consecuencia» o «tras» afirman una causa o un orden; «en cambio», «sin embargo» o «pese a» marcan un contraste. Úsalos solo si el dossier lo dice. Si no, usa conectores neutros: «además», «por su parte», «mientras tanto». Prohibidas las muletillas de tertulia («ojo», «y es que», «ni más ni menos», «atentos»).
- **Ejemplo:**
  - Telegrama: «Vox fue primero: Santiago Abascal lo anunció en una entrevista, como acusación popular. El PP lo anunció en un vídeo de Alma Ezcurra. Vox ya presentó una querella contra directivos de Adif el día del accidente. Otra ante el Supremo, contra Puente.»
  - Para el oído: «Vox se adelantó: Santiago Abascal lo contó en una entrevista, y lo hará como acusación popular. El PP, por su parte, lo anunció en un vídeo de Alma Ezcurra. Además, no es el primer paso de Vox en los tribunales, porque el mismo día del accidente ya se querelló contra directivos de Adif, y presentó otra querella ante el Supremo contra Puente.»

## Cruce de declaraciones: el «salseo» (decisión del usuario del 3-nov-2026)
**El salseo es el eje del canal, no un adorno.** Las declaraciones, la confrontación, las descalificaciones y el debate entre políticos son el día a día de la política y lo que engancha al público de YouTube; de ahí salen las frases gancho del sumario, de la miniatura y del título. Un canal que solo lee noticias no es lo que queremos.
- **Primeros 30 segundos** (sumario): valen las descalificaciones políticas literales («mentiroso», «corrupto», «traidor», «golpista»…), porque son el gancho; **no** valen tacos ni insultos vejatorios (YouTube quita los anuncios de todo el vídeo si salen al principio). Esos, más adelante en el bloque o contados sin reproducirlos.
El canal no se limita a leer noticias: cuenta **qué se dicen los protagonistas unos a otros**. Cuando un partido ataca a otro y el otro responde, ese cruce, con sus frases literales, es parte central del bloque. Da ritmo y un tono más desenfadado, sin dejar de ser riguroso y neutral.
- **Cada ataque, con su respuesta si la hay.** «Vox acusa al PSOE de…: «…». El PSOE responde: «…».» Si no hay respuesta, **solo la cita**: nunca «no consta respuesta», «no ha contestado» ni similares (decisión del usuario del 3-nov-2026: repetido queda mal). El equilibrio se consigue con las frases de las otras partes, no anunciando silencios.
- **Las frases con más gancho, pero literales:** las más directas, irónicas o duras que se hayan dicho, entre comillas en pantalla, atribuidas con nombre y cargo y con la fecha si no es de hoy. Cortas: una frase; como mucho, dos muy breves.
- **Equilibrio:** el mismo trato para todos. Se elige la frase más fuerte de **cada** parte, no la más fuerte de una y la más floja de otra. Ni la última palabra ni la frase más llamativa pueden ser siempre del mismo lado: si hay varios cruces, se alterna quién abre y quién cierra.
- **Tono cercano, verbos neutros.** Valen «responde», «contesta», «replica», «le devuelve la acusación», «y la respuesta llegó en horas», «el cruce siguió en redes», «Vox fue más allá». Prohibido todo lo que juzga quién gana: «zasca», «le dio un repaso», «humilla», «destroza», «le pone en su sitio», «se retrata».
- **Insultos y tacos:** las descalificaciones políticas se citan literales en cualquier parte, también en el sumario, la miniatura y el título. Los insultos vejatorios, solo dentro del bloque (nunca en los primeros 30 segundos, la miniatura ni el título). Los tacos fuertes, nunca: se cuenta que los hubo («con un insulto que no reproducimos»).
- **Si lo han dicho, se cita** (decisión del usuario del 3-nov-2026): da igual que haya pruebas o no de lo que afirman; la noticia es que lo han dicho. Va siempre como lo que es, la afirmación o la acusación de alguien con nombre («Vox acusa al PSOE de…», «según Abascal…»), nunca como un hecho, y **se busca la respuesta** del aludido. No hace falta añadir «sin pruebas».
- **Redes sociales:** un mensaje en la cuenta oficial de un político es una declaración más. Se cita literal como «<nombre>, en X» (y en la voz, «escribió en X»), tomado del medio que lo recoge. Nunca capturas de pantalla de X ni las fotos de los tuits: la cita va en nuestra tarjeta.
- **En pantalla:** la escena `citas` con las dos voces enfrentadas (o `persona` con `flujo`) es la natural para un cruce.

## Equilibrio
- En cada polémica: versión del Gobierno, de la oposición principal y, si la hay, de los socios. Si una parte no ha hablado, no se anuncia su silencio (nada de «no consta respuesta»): se cuenta lo que sí dijeron las demás.
- Los medios de referencia cubren todo el espectro: El País, elDiario.es, Público, La Vanguardia, RTVE, Europa Press, 20minutos, El Confidencial, El Mundo, ABC, La Razón. Un hecho que solo publica la prensa de una línea va **atribuido**.

## Catálogo de escenas (lo que el redactor puede pedir en `"ve"`)
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
| `despedida` | cierre de Urni | — | solo en el último paso |

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

## Coordenadas de referencia (lon, lat)
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
