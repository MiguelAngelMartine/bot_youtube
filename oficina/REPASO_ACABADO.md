# Repaso de acabado del vídeo largo (1-nov-2026)

El usuario pidió que todo el vídeo, de principio a fin, tenga un semblante profesional y cuidado al detalle.
Repaso hecho sobre el episodio de prueba del 31-oct (`dia/prueba-inicio`), mirando 65 fotogramas: el principio, la mitad y el final de cada escena.

## Ya resuelto
- Arranque: sumario de titulares a pantalla completa (`titulares.py`) y golpe de marca coreografiado (`marca.py`).
- Cierre: despedida a pantalla completa con suscripción y campanita, y pantalla final (`cierre.py`).
- Urni ya no asoma en un primer bloque sobrio.
- Render: de ~31 a ~11 min por vídeo de 6 min en el servidor (4 procesos, OpenCV, caché de voz y música).

## Pendiente, por orden de importancia
1. **Subtítulos palabra a palabra.** Salen 1-2 palabras sueltas en grande («el», «de la», «por la»). Es el lenguaje de TikTok y en el horizontal se ve poco serio.
   Propuesta: quitarlos del largo y subir el `.srt` a YouTube como subtítulos (ya se genera), o una línea de frase completa, discreta, abajo.
2. **Tablero medio vacío y descompensado.** Las piezas se amontonan arriba a la izquierda y queda mucho azul vacío: una cifra sola en una esquina, el mapa a la izquierda y nada a la derecha. Hasta el final de cada escena hay un 40-50 % de hueco.
   Propuesta: que la cámara encuadre lo que hay en cada momento y que la composición final de cada escena esté centrada y equilibrada.
3. **La cámara corta piezas al acercarse.** Por ejemplo, «OY, EL ADIÓS» o una nota cortada por el borde. Solución: limitar el encuadre para que nunca deje una pieza a medias.
4. **Letra manuscrita en todas las notas**, también en la tragedia. En el móvil cuesta leerla y da un aire informal.
   Propuesta: letra limpia (Inter o Barlow) en las notas informativas; la manuscrita, solo para algún apunte puntual.
5. **Textos ilegibles por pequeños.** La columna «FUENTES», los «Fuente: ...» de las notas, los créditos de las polaroids y la fecha de la cabecera. Hace falta un tamaño mínimo legible en el móvil, o pasar las fuentes a un rótulo inferior más grande.
6. **Columna izquierda desaprovechada.** Un recuadro pequeño de fuentes y Urni abajo; en los bloques sobrios se queda vacía.
7. **Fotos y polaroids.**
   - Polaroid sin foto con iniciales en color (Garriga: «IG» en verde): parece un hueco por rellenar. Mejor solo la etiqueta con el nombre.
   - Sánchez sonriendo en un bloque grave: el gesto tiene que ir con la noticia (ya está en las normas del editor gráfico).
   - El sello «NO DIMITE» tapa la cara de Puente.
8. **Detalles.**
   - Las cifras grandes podrían contar hasta su valor.
   - Los iconos de los breves (vela, megáfono, mazo) parecen genéricos.
   - Las cortinillas entre bloques son simples comparadas con el arranque nuevo.
   - El desenfoque al cambiar de escena dentro de un bloque se ve como cinco copias superpuestas del tablero, no como un movimiento suave.
