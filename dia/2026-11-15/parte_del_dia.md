# Parte del día 2026-11-15

- 09:26 · Jornada iniciada (supervisada por el usuario).

## Fase 0-1 — Recopilación y material
- Recopilación: 485 noticias de los medios (todos HTTP 200).
- Temas: 15 (encabeza campaña 29N con 43 noticias).
- Artículos: 57/114 con texto completo.
- Contexto: contexto.md (810 palabras).
- Redes: 140 publicaciones oficiales. Ganchos: 11 frases literales con impacto.
- Erratas: Gemini saturado → agente fe-de-erratas (en curso).
- Dossieres (Gemini, en curso): campana_29n, frente_amplio_campana, nucleo_nacional, nacionalismo_vasco_catalan, caso_koldo_okdiario, vivienda_politica, frases.
- Dossieres listos: campana_29n, frente_amplio_campana, nucleo_nacional, nacionalismo_vasco_catalan, vivienda_politica (Gemini/freellmpool) y caso_koldo_okdiario (agente Claude; 1 sola fuente, elDiario.es → atribuir).
- Erratas: 1 corrección (frase «me gusta la fruta» de ayer mal situada).
- «La campaña en frases»: Gemini falló → agente investigador de Claude (en curso).
12:00 coordinador en Python (Gemini; Claude solo de respaldo) en marcha
12:38 recogida y dossieres listos (9 temas)
12:38 jefe-de-edicion: consejo de redacción (decisión editorial clave), lo hace Claude
12:44 escaleta: 3 bloques y 2 breves
12:46 redactor: bloque 02 sin la calidad mínima tras 2 intentos de Gemini, lo hace Claude
12:48 redactor: bloque 04 sin la calidad mínima tras 2 intentos de Gemini, lo hace Claude
12:48 redactor: bloque 03 sin la calidad mínima tras 2 intentos de Gemini, lo hace Claude
12:49 redactor: bloque 01 sin la calidad mínima tras 2 intentos de Gemini, lo hace Claude
12:49 redacción: 4 piezas escritas y prechequeadas
12:50 mesa vuelta 1: CORREGIR en 01, 03, 04
13:00 mesa vuelta 2: CORREGIR en 01, 03, 04
13:04 verificador: bloque 01 sigue en CORREGIR tras dos vueltas, lo hace Claude
13:04 verificador: bloque 03 sigue en CORREGIR tras dos vueltas, lo hace Claude
13:04 verificador: bloque 04 sigue en CORREGIR tras dos vueltas, lo hace Claude
13:08 editor-de-cierre: Gemini no responde, lo hace Claude
13:08 FALLO en cierre
13:26 cierre 1ª versión sin bloque 02 (519 palabras); bloque 02 a la mesa (vuelta 1) para reintegrarlo
13:29 bloque 02 APTO tras 2 vueltas (retoques menores aplicados); rehago cierre
13:32 episodio.json listo (734 palabras, 4:30); sigo estándar 14-nov: prevuelo de voz y render_ambiente (supervisado, sin subir)
14:14 largo montado (render_ambiente, 4:41; FLUX caído → biblioteca de ambiente); control de calidad y miniatura en curso; sin subir todavía
14:15 miniatura generada («Al ultra que se arruga») RECHAZADA: cita cortada, sin atribución y con descalificación; pendiente rehacer
14:16 miniatura nueva «Ni un paso atrás» (sin caras ni insultos; ojo: sin comillas/autor y con ikurriñas puede confundir quién lo dice)
14:21 control de calidad CORREGIR (5 puntos); guion reescrito (815 pal.); repito prevuelo y arreglo Polaroids/escenas

## Fases 2-4 — Consejo, redacción y mesa
- Escaleta: 3 bloques de campaña + 2 breves, ~285 s. Tono Vikingo plural.
  1. «La guerra del inglés» (Sánchez-PP, Ayuso «J'aime les fruits»).
  2. «O la mafia o España» (Abascal/Tellado vs Sánchez).
  3. «Líneas rojas y pactos» (PNV, Junts, Otegi, Abascal).
  Breves: vivienda (Colau vs Sánchez) + «La campaña en frases» (Torres, Orriols).
- Fuera: Canarias/El Hierro (generalista), Hernani (suceso), caso Koldo (1 sola fuente).
- Redacción: 4 bloques escritos (Opus). Prechequeo: 01/02 OK; 03 y breves con fallo mecánico menor, corregido a mano (cuando literal / frase <30).
- Incidencia: a mitad saltó el límite de 5 h del plan de Claude (se renovó); la jornada siguió.
- Mesa de control: verificador + neutralidad + cumplimiento (en curso).
18:22 reanudo (intento 3): re-render 15:16 sin control de calidad; lo hago ahora
18:35 control de calidad CORREGIR (solo escenas: Hernani con Plaza Mayor de Madrid, carteles con letras inventadas, Canarias sin mar, edificio repetido, despedida sin pantalla final). FLUX sin cuota -> biblioteca. No subo nada; espero decisión del usuario
- Mesa de control: 2 vueltas. Veredicto final APTO en los 4 bloques. Correcciones clave: 02 (fuera «mafia» de título y primeros 30 s, cita de Sánchez a la versión literal de elDiario, fuente del lema → Vox en X), breves (fuera cita de Orriols sobre el islam por monetización). Retoques finales aplicados a mano.
- Cierre: episodio.json con Gemini (límite de 5 h de Claude agotado, renueva 18:20 Madrid), 6 secciones (~5,4 min). Sumario saneado a mano (quitada «mafia» de los primeros 30 s; Abascal→Tellado «los Kirchner»). Título: «Suspende en inglés» contra «echar a la mafia».

## Cierre, montaje y subida (manual, supervisado)
- Cierre con Gemini (límite de Claude agotado); sumario saneado a mano (sin «mafia» en los 30 s).
- Montaje con render_ambiente (escenas de ambiente + Polaroid + subtítulos), 5 min 16 s. FLUX sin cuota → biblioteca de ambiente.
- Hueco de integración resuelto: descripcion.py (episodio_descripcion.txt) y hojas.py (control visual) para render_ambiente.
- Largo subido como privado: 8Ad4vwP54ys. Miniatura con Feijóo (esquina inf-dcha, por petición).
- Shorts rehechos con guion de Opus (tono Vikingo, sin bleed, Polaroid correcta): 7lDYI8UgNoU y JL2Ko27mEeg, subidos como privados.
- ESTÁNDARES FIJADOS (código + CLAUDE.md): guion siempre Opus (largo y Shorts); la mesa no toca el estilo; jornada a las 10:30 con jornada.py; Shorts antes del largo; render_ambiente en jornada.py.
- PENDIENTE: importar los PNG transparentes del usuario (scp al servidor) y cablear la Polaroid para usarlos; regenerar la escena «Spanis» del Short 2 si se quiere.
