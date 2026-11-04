"""EDITOR DE PLATAFORMA con Gemini (decisión del usuario del 4-nov-2026): título, primeras líneas de la descripción,
etiquetas, hashtags y comentario fijado. Lo que no admite errores (capítulos, fuentes, aviso de IA y créditos) no lo
toca Gemini: va tal cual desde episodio_descripcion.txt. El programa comprueba límites y formato.
Uso: python plataforma.py AAAA-MM-DD     (salida 2 si Gemini no responde: entonces, el agente editor-plataforma)"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import gem

RAIZ = Path(__file__).parent

PROMPT = """Eres el editor de plataforma de «El Hoyformativo», informativo diario de política española en YouTube,
neutral y riguroso, con un tono desenfadado basado en el cruce de declaraciones entre políticos («salseo»).
A partir del guion del vídeo de abajo, escribe:
- "titulo": ≤ 70 caracteres, SIN el nombre del canal (decisión del usuario del 4-nov-2026). Mejor si empieza por la frase más impactante del día,
  LITERAL y atribuida, que salga en el guion; si no, los 2-3 temas con el término que la gente buscaría al principio.
  Sin mayúsculas gritonas, sin exclamaciones, sin prometer nada que el vídeo no cuente. Tacos e insultos vejatorios, no.
- "lineas": 2 frases naturales que resuman las noticias principales con los nombres propios que alguien buscaría
  (son las que se ven en la búsqueda). Neutrales.
- "etiquetas": 15-25 etiquetas de cosas que SALEN en el vídeo (personas, partidos, instituciones, temas), con
  variantes de búsqueda, más «política española», «noticias España», «resumen del día», «El Hoyformativo».
  Nada de relleno ni de temas que no salen (es spam para YouTube).
- "hashtags": exactamente 3: el del tema principal, uno general (#PolíticaEspaña) y #ElHoyformativo.
- "comentario": una pregunta neutral para la comunidad sobre el tema principal que no tome partido, y una frase
  invitando a señalar errores con su fuente para la fe de erratas.
Responde SOLO con JSON con esas claves.

GUION DEL VÍDEO:
"""


def main(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    guion = "\n\n".join(f"[{s.get('titulo', '')}]\n" + " ".join(p.get("di", "") for p in s["pasos"]) for s in G["secciones"])
    r = gem.pide(PROMPT + guion, como_json=True)
    if not isinstance(r, dict) or not r.get("titulo"):
        print("Gemini no responde: usa el agente editor-plataforma")
        sys.exit(2)
    titulo = r["titulo"].strip().removesuffix(" | El Hoyformativo")
    if len(titulo) > 70:                               # se corta por la ultima palabra entera
        titulo = titulo[:70].rsplit(" ", 1)[0]
    desc_base = (dia / "episodio_descripcion.txt").read_text(encoding="utf-8")
    desc_base = desc_base.split("\n\n", 1)[1] if desc_base.startswith(G.get("titulo_video", "\0")) else desc_base
    descripcion = (" ".join(r.get("lineas", [])) + "\n\n" + desc_base.strip()
                   + "\n\nEl Hoyformativo: la política española del día, en claro y con fuentes. Nuevo episodio cada tarde.")
    etiquetas = [e.strip() for e in r.get("etiquetas", []) if e.strip()]
    while len(", ".join(etiquetas)) > 480:
        etiquetas.pop()
    hashtags = " ".join(h if h.startswith("#") else "#" + h for h in r.get("hashtags", [])[:3])
    origen = dia / "vinetas" / "origen.json"
    sintetico = origen.exists() and any(d.get("persona") and (dia / "vinetas" / f"{k}.jpg").exists()
                                        for k, d in json.loads(origen.read_text(encoding="utf-8")).items())
    md = f"""# Publicación · {G.get('fecha', fecha)}

## Título
```
{titulo}
```

## Hashtags
```
{hashtags}
```

## Descripción
```
{descripcion}
```

## Etiquetas
```
{", ".join(etiquetas)}
```

## Comentario fijado
```
{r.get('comentario', '').strip()}
```

## Lista de comprobación para YouTube Studio
- Categoría: Noticias y política. Público: no es contenido para niños. Idioma: español (España).
- Contenido alterado o sintético: {"Sí (hay personas reales dibujadas por IA; subir.py lo marca)" if sintetico else "No (la voz es sintética pero no imita a nadie, y se declara en la descripción)"}.
- Miniatura: `miniatura.png`. Subtítulos: van incrustados en el vídeo (no se sube pista).
- Pantalla final: los últimos 8 s (vídeo + suscribirse, a la derecha).

_Hecho con Gemini (plataforma.py); capítulos, fuentes, aviso de IA y créditos copiados tal cual de episodio_descripcion.txt._
"""
    (dia / "publicacion.md").write_text(md, encoding="utf-8")
    print(f"publicacion.md lista · título: {titulo} ({len(titulo)} caracteres) · {len(etiquetas)} etiquetas")


if __name__ == "__main__":
    main(sys.argv[1])
