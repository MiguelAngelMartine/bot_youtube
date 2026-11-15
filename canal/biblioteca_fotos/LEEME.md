# Biblioteca local de FOTOS (retratos de políticos)

Respaldo local de retratos reales, bien etiquetados, para no depender de la red ni de las caídas de las fuentes
(Wikimedia, Openverse, Pool Moncloa). Va en git para que el servidor la tenga.

## Estructura
- `catalogo.json` — índice central: `{ "<apellido>": [ ficha, ... ] }`.
- `<apellido>/<hash>.jpg` — cada retrato (nombre = hash del contenido, así no se repite).

## Ficha de cada foto (bien documentada SIEMPRE)
`hash`, `img`, `persona`, `licencia`, `autor`, `fuente`, `url`, `pagina`, `titulo`, `gesto`, `puntos` (nota de Gemien), `guardado` (fecha).
Solo entran fotos de **licencia comercial** (CC0 / dominio público / CC BY / CC BY-SA); nunca CC BY-NC-ND.

## Cómo se llena y se usa
- `fotos.mejores(...)` guarda en la biblioteca cada retrato bueno que baja (recortado a primer plano) → la biblioteca
  acumula VARIEDAD por político con el uso diario.
- Si un día falla la red o no hay foto nueva, `render_ambiente._foto_persona` tira de `biblioteca_fotos.busca(persona)`.
- `python biblioteca_fotos.py` lista cuántas fotos hay por persona.

## Regla del proyecto
**Biblioteca local y bien documentada para TODOS los recursos, siempre** (fotos, escenas de ambiente, viñetas, música…),
como respaldo ante caídas y para ganar variedad con el tiempo.
