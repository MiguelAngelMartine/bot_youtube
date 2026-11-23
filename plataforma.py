"""EDITOR DE PLATAFORMA con Gemini (decisión del usuario del 4-nov-2026): título, primeras líneas de la descripción,
etiquetas, hashtags y comentario fijado. Lo que no admite errores (capítulos, fuentes, aviso de IA y créditos) no lo
toca Gemini: va tal cual desde episodio_descripcion.txt. El programa comprueba límites y formato.
Uso: python plataforma.py AAAA-MM-DD     (salida 2 si Gemini no responde: entonces, el agente editor-plataforma)"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import gem

RAIZ = Path(__file__).parent

PROMPT = """Eres el editor de plataforma de «El Hoyformativo», informativo diario de política española en YouTube,
neutral y riguroso, con un tono desenfadado basado en el cruce de declaraciones entre políticos («salseo»).
A partir del guion del vídeo de abajo, escribe:
- "titulo": ≤ 60 caracteres, SIN el nombre del canal (decisión del usuario del 4-nov-2026). 23-nov-2026: PRIMERO la
  expresión de gancho del día entre comillas, LITERAL, y DESPUÉS los personajes, empezando por QUIEN LA DIJO («Va ahora de
  corderito»: Cayetana a Sánchez); nunca la frase con el nombre del aludido solo, ni la fórmula «"frase" afirma X».
  Sin mayúsculas gritonas, sin exclamaciones, sin prometer nada que el vídeo no cuente. Tacos e insultos vejatorios, no.
  Verbos neutros («dice», «responde a», «critica», «pide»); nunca «carga contra», «arremete», «estalla», «sentencia»,
  «zanja», «destroza», «humilla».
- "lineas": 2 frases naturales que resuman las noticias principales con los nombres propios que alguien buscaría
  (son las que se ven en la búsqueda). Neutrales.
- "etiquetas": 35-45 etiquetas (decisión del usuario del 7-nov-2026: más palabras clave). Todas de cosas que SALEN en
  el vídeo: cada político con nombre completo y con el nombre por el que se le busca («Isabel Díaz Ayuso», «Ayuso»),
  su cargo («presidente del Gobierno»), cada partido con sus siglas y nombre, instituciones, lugares y cada tema con
  sus variantes de búsqueda («caso Koldo», «Koldo García»), más las generales: «política española», «noticias
  España», «actualidad política», «resumen del día», «noticias de hoy», «El Hoyformativo» (y «elecciones» o «campaña
  electoral» si el vídeo habla de ellas). Nada de personas ni temas que no salgan (YouTube lo trata como spam).
- "hashtags": entre 12 y 15 (nunca más de 15: YouTube los ignoraría todos). Los 3 primeros son los que se ven sobre
  el título: el del tema principal, el del protagonista principal y #PolíticaEspañola. Después, uno por cada político
  y partido importante que sale (#Sánchez, #Feijóo, #Ayuso, #PSOE, #PP, #Vox…), los de los temas (#CasoKoldo…),
  #NoticiasDeHoy, #ActualidadPolítica y #ElHoyformativo al final. Sin espacios dentro, sin repetir.
- "comentario": una pregunta neutral para la comunidad sobre el tema principal que no tome partido, y una frase
  invitando a señalar errores con su fuente para la fe de erratas.
Responde SOLO con JSON con esas claves.

GUION DEL VÍDEO:
"""


def main(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    guion = "\n\n".join(f"[{s.get('titulo', '')}]\n" + " ".join(p.get("di", "") for p in s["pasos"]) for s in G["secciones"])
    # 22-nov-2026 (el usuario: llegar al máximo de búsquedas): las búsquedas REALES de YouTube que describen este vídeo
    import palabras_clave as PK
    PK.carga(max_dias=3, refrescar=True)
    temas = [s.get("titulo", "") for s in G["secciones"]]
    busc, hs_busc = PK.para_video(guion, temas=re.findall(r"[A-ZÁÉÍÓÚÑ][\wáéíóúñ]{3,}", " ".join(temas))[:6], max_tags=30)
    extra = ("\n\nBÚSQUEDAS REALES DE YOUTUBE que describen este vídeo (de más a menos buscadas; úsalas tal cual en "
             "etiquetas y, cuando encajen de forma natural, en las «lineas» y el título): " + "; ".join(busc)) if busc else ""
    r = gem.pide(PROMPT + guion + extra, como_json=True)
    if not isinstance(r, dict) or not r.get("titulo"):
        print("Gemini no responde: usa el agente editor-plataforma")
        sys.exit(2)
    titulo = r["titulo"].strip().removesuffix(" | El Hoyformativo")
    if len(titulo) > 70:                               # se corta por la ultima palabra entera
        titulo = titulo[:70].rsplit(" ", 1)[0]
    desc_base = (dia / "episodio_descripcion.txt").read_text(encoding="utf-8")
    desc_base = desc_base.split("\n\n", 1)[1] if desc_base.startswith(G.get("titulo_video", "\0")) else desc_base
    descripcion = (" ".join(r.get("lineas", [])) + "\n\n" + desc_base.strip()
                   + "\n\nEl Hoyformativo: la actualidad, en un minuto. Frases literales y comprobadas en su fuente, con todas "
                   "las partes. Contenido revisado por el equipo editorial antes de publicarse.")
    etiquetas = [e.strip() for e in r.get("etiquetas", []) if e.strip()]
    vist = {PK._n(e) for e in etiquetas}                # las búsquedas reales, primero; luego las del redactor
    etiquetas = [b for b in busc if PK._n(b) not in vist] + etiquetas
    etiquetas = list(dict.fromkeys(etiquetas))
    while len(", ".join(etiquetas)) > 480:
        etiquetas.pop()
    for mal, bien in ((r"\b(carga|cargan|arremete|arremeten|estalla|estallan) contra\b", "critica a"),
                      (r"\b(sentencia|zanja|suelta|clama)\b", "dice")):
        titulo = re.sub(mal, bien, titulo)               # verbos valorativos fuera (libro de estilo)
    import apto_anuncios as AA                         # 10-nov: sin tacos ni insultos personales en el título (anuncios)
    sumario = [it.get("titular", "") for p in G["secciones"][0]["pasos"] for it in (p.get("ve") or {}).get("items", [])]
    titulo = AA.elige(titulo, G.get("titulo_video", ""), *sumario, "Los cruces de la política española de hoy")
    try:                                               # 10-nov: el estratega de YouTube elige el mejor de 5 títulos
        import experto_youtube as EX
        titulo = EX.mejor_titulo(titulo, sumario, [x.get("titulo", "") for x in G["secciones"][1:]])
    except Exception as e:
        print(f"(experto sin respuesta: {type(e).__name__})")
    try:                                               # 23-nov-2026: la frase del título, con el nombre de quien la dijo
        import titulos as TT
        cs = []
        for s_ in G["secciones"]:
            for p_ in s_.get("pasos", []):
                ve = p_.get("ve") or {}
                for it in (ve.get("items") or []) + [ve, ve.get("persona") if isinstance(ve.get("persona"), dict) else {}]:
                    if isinstance(it, dict):
                        q = it.get("persona") if isinstance(it.get("persona"), str) else it.get("nombre")
                        c = it.get("titular") or it.get("cita")
                        if isinstance(q, str) and isinstance(c, str) and q and c:
                            cs.append((c.strip("«»\""), q))
        titulo, aviso_t = TT.revisa(titulo, cs)
        if aviso_t:
            print("  " + aviso_t)
    except Exception as e:
        print(f"(control de título sin hacer: {type(e).__name__})")
    vistos, hs = set(), []
    rh = list(r.get("hashtags", []))
    rh = rh[:3] + [h for h in hs_busc if h.lower() not in {x.lower() for x in rh}] + rh[3:]   # los más buscados, tras los 3 visibles
    for h in rh:                                       # máximo 15 (con más, YouTube los ignora todos), sin repetir
        h = "#" + re.sub(r"[\s#]+", "", str(h))
        if len(h) > 1 and h.lower() not in vistos:
            vistos.add(h.lower())
            hs.append(h)
    if "#elhoyformativo" not in vistos:
        hs = hs[:14] + ["#ElHoyformativo"]
    hashtags = " ".join(hs[:15])
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
