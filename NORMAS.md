# Normas del canal (obligatorias en cada vídeo)

Objetivo: canal diario de política española **monetizable**, **neutral**, con **hechos reales y contrastados** y **sin riesgos legales**.
Revisadas el 1-nov-2026 con las páginas oficiales de YouTube, Creative Commons y el BOE (enlaces al final).
Esto NO es asesoramiento jurídico: antes de activar la monetización conviene una consulta breve con un abogado de propiedad intelectual.

## 1. Veracidad (lo que sale en el vídeo es real)
- Cada dato debe venir de **al menos dos medios distintos**, o ir **atribuido** al único medio que lo publica. Desde el 1-nov-2026 la atribución a medios va en pantalla («según El País» en la nota y el recuadro «FUENTES»), no en la voz; la voz sí marca lo no confirmado.
- Nada de cifras, fechas o citas que no estén en las noticias del día. Si hay duda, se quita.
- Las **declaraciones** van entre comillas o en estilo indirecto, siempre con nombre y cargo de quien las hace.
- Una sola encuesta **no** es una tendencia: se presenta como la lectura de esa encuestadora.
- Las **fotos** tienen que corresponder a lo que se está narrando. Nunca una persona que no aparece en la noticia
  (caso real: se quitó una foto de Ada Colau en el bloque de Puente porque no salía en ninguna noticia).
- Prohibidas las imágenes generadas por IA que parezcan hechos reales.

## 2. Neutralidad
- Fuentes de líneas editoriales distintas (El País, El Mundo, ABC, elDiario.es, La Vanguardia, Europa Press, 20minutos, El Confidencial, RTVE, La Razón, Público).
- En cada polémica: **la versión del Gobierno y la de la oposición**, y la de los socios si la hay.
- Sin adjetivos valorativos propios ("escándalo", "vergonzoso"...). Los calificativos solo en boca de quien los dice.
- El tiempo y el orden de los bloques se deciden por la relevancia informativa, no por el partido.
- El **análisis propio** es de contexto ("por qué importa", "qué pasa ahora", "qué dice la ley"), nunca de opinión.

## 3. Monetización de YouTube (Programa de Socios)
- **Riesgo n.º 1: "contenido no auténtico"** (antes "repetitivo", cambio del 15-jul-2025). YouTube no monetiza
  "image slideshows, templated storylines... with minimal or no narrative" ni contenido que "feels interchangeable from video to video".
  Medidas:
  - El guion es **original cada día**, con narrativa propia y contexto (no solo leer titulares).
  - Cada bloque lleva **algo de elaboración propia**: dato en grande, cronología, cita destacada, mapa, «qué pasa ahora».
  - **Estructura variable** según el día (número de bloques, tema de apertura, formato de cada pieza); solo se repiten la entrada y el cierre (permitido).
  - Los metadatos (título, descripción, capítulos) son únicos y describen bien el contenido.
- **Anuncios (advertiser-friendly)**: se pueden monetizar tragedias "not exploitative or dismissive" y temas de interés público.
  Limitan ingresos: detalles gráficos de víctimas, cuerpos, choques impactantes, enfrentamientos violentos con la policía.
  Medidas: lenguaje sobrio, sin detalles escabrosos ni imágenes de víctimas o del impacto; miniatura y título sin morbo ni gritos.
- **Elecciones**: nunca dar como hecho algo falso sobre cómo, cuándo o dónde votar (sin ingresos y posible infracción).
- **Divulgación de IA**: la voz es sintética y genérica (no imita a nadie), así que por la voz la casilla "contenido alterado o sintético" no es obligatoria.
  Aun así, la descripción siempre dice: "Resumen elaborado con ayuda de IA... Voz sintética."
- **Viñetas hechas con IA** (resuelto el 2-nov-2026):
  - YouTube solo exige declarar lo **realista** que pueda confundirse con algo real; las viñetas son dibujo de novela gráfica, claramente no realista. Aun así, **si una viñeta dibuja a una persona real, `subir.py` marca el vídeo como «contenido alterado o sintético»** (según YouTube, declararlo no limita la audiencia ni los ingresos) y la descripción lo dice. Si la API no lo admite, avisa para marcarlo a mano antes de publicar.
  - Cada viñeta lleva en pantalla «Ilustración IA» y, si dibuja a una persona, «a partir de foto de <autor> (<licencia>)». Así cumple también el deber europeo de transparencia de la IA.
  - Las personas solo se dibujan a partir de fotos **CC0, de dominio público o CC BY**: la viñeta es obra derivada de la foto, y una foto **CC BY-SA** obligaría a dar la viñeta (y con ella el vídeo) con esa misma licencia. Si el retrato es SA, NC o ND, `ia_vinetas.py` no la dibuja y la nota sale con su texto.
  - Solo se dibuja a una persona cuando la nota cuenta algo que dijo o hizo ella (nunca algo inventado ni ridiculizante): protege su derecho al honor y a la propia imagen; es información de interés público sobre un cargo público.
  - Modelos: FLUX.1 schnell y FLUX.2 klein 4B (Apache 2.0, uso comercial permitido) en Cloudflare Workers AI.
- Requisitos para entrar en el programa: 1.000 suscriptores + 4.000 horas de visualización en 12 meses
  (o 10 M de visualizaciones de Shorts en 90 días), verificación en dos pasos y cuenta de AdSense.

## 4. Derechos de autor
- **Texto**: los hechos no tienen derechos, la redacción sí. Se cuenta con **palabras propias**, sin calcar frases ni la estructura del artículo.
  Nunca se lee ni se muestra un artículo, titular o captura de un medio.
- **Citas de políticos**: frases cortas, entre comillas, atribuidas, de declaraciones públicas.
- **Fotos**: solo de licencia libre y con crédito en pantalla y en la descripción.
  - Preferencia: **CC0 / dominio público / CC BY** y fuentes oficiales que permiten la reutilización citando (La Moncloa, Congreso, Senado).
  - **CC BY-SA**: se puede usar, pero el zoom o el recorte podrían contar como modificación. Mientras no se resuelva, se indica
    "foto adaptada" en la descripción, y se prefieren las alternativas CC BY o CC0.
  - **Nunca** fotos de periódicos, agencias (EFE, Europa Press...), Getty ni capturas de televisión.
  - Retratos de políticos: solo en el contexto de la noticia en que aparecen (derecho a la propia imagen).
- **Fotos** (retratos en polaroid y fotos de escena): solo de licencia libre (Openverse/Wikimedia), con «Foto de archivo», el autor y la licencia en pantalla, y la lista completa en la descripción. Nunca víctimas ni personas ajenas a la noticia.
- **Música**: compuesta por el propio programa (musica.py), sin muestras ajenas, así que no puede haber reclamaciones de Content ID.
- **Voz**: Tristán HD de Azure Speech (Microsoft), servicio oficial con uso comercial permitido también en el plan gratuito F0 (desde el 2-nov-2026).
  No hay voz de reserva en producción: edge-tts no tiene licencia comercial, así que si Azure falla no se sube nada ese día.
- **Todo lo que se sube a YouTube tiene que ser monetizable** (norma del usuario del 2-nov-2026): voz Azure, música propia, fotos CC0/dominio público/CC BY/CC BY-SA, viñetas FLUX (Apache 2.0) y tipografías OFL.

## 5. Revisión humana antes de publicar
El usuario ve el vídeo completo antes de subirlo y comprueba:
1. Que ningún dato le chirríe; si duda, se mira la fuente.
2. Que las fotos encajan con lo narrado.
3. El tono neutral.
4. La miniatura y el título.

## Fuentes
- Contenido no auténtico y reutilizado: https://support.google.com/youtube/answer/1311392
- Contenido alterado o sintético: https://support.google.com/youtube/answer/14328491
- Directrices para anunciantes: https://support.google.com/youtube/answer/6162278
- Requisitos del Programa de Socios: https://support.google.com/youtube/answer/72851
- Preguntas frecuentes de Creative Commons: https://creativecommons.org/faq/
- Ley de Propiedad Intelectual (arts. 32 y 33): https://www.boe.es/buscar/act.php?id=BOE-A-1996-8930
