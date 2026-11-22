"""GUIONES DE LOS SHORTS (decisión del usuario del 5-nov-2026): de cada jornada, hasta 3 Shorts verticales, uno por
frase con más gancho del día (sobre todo de las redes oficiales de los políticos). Gemini elige y redacta; el programa
comprueba que cada cita está LITERAL en lo ya aprobado por la mesa de control (episodio.json) o en una fuente oficial
del día (redes.md), y descarta lo que no. Reparto entre partidos: nunca todos contra el mismo.
Uso: python shorts_guion.py AAAA-MM-DD [n=3]   -> dia/<fecha>/shorts/short_N.json   (salida 2 si Gemini no responde)"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import gem

RAIZ = Path(__file__).parent
EJEMPLOS = (RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md").read_text(encoding="utf-8") if (RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md").exists() else ""   # EJEMPLOS_GANCHOS: aprende del director

PROMPT = """Eres el guionista de Shorts de «El Hoyformativo»: política española en tono DESENFADADO Y CON OPINIÓN LIGERA, estilo «La
Pulla» o «Vikingo Blanco» (lee NORMAS.md (§4)). Humor e ironía sobre TODOS por igual, SIN tomar partido. Elige las {n} FRASES MÁS IMPACTANTES (de más a menos) del día
para hacer un Short de alrededor de 1 minuto con cada una. Reglas:
- Prioriza los de la sección «GANCHOS DEL DÍA» (al principio del material; los «del director», primero): frases cortas
  con impacto, zascas y cruces con respuesta.
- La frase tiene que estar LITERAL en el material de abajo (cópiala letra a letra; un programa lo comprueba) y ser
  ENTERA palabras de quien habla: si el medio solo entrecomilla una palabra suelta («ve "irresponsable" decir...»), esa
  frase no vale (sería atribuirle palabras del periodista). Sin comillas dentro de la cita. Prioriza
  las de redes oficiales (X, Telegram, Bluesky) y las acusaciones, réplicas y descalificaciones con más gancho.
- Reparto: cada Short de un protagonista y partido distintos si es posible; nunca todos atacando al mismo partido.
- La cita, de 4 palabras o más (una réplica corta tipo «Aplícatelo» no es un Short: va como réplica del ataque).
- Cada cruce, en un solo Short: la frase que ataca y, como "replica", la respuesta DIRECTA del aludido a esa frase o a
  esa persona. Solo si el material muestra que responde (cita a quien le atacó, contesta al tuit, «responde a...»):
  copia en "prueba" el fragmento literal del material que lo muestra. Una declaración del otro partido sobre el mismo
  tema que no contesta a ese ataque NO es una réplica. Si no hay réplica directa: "replica": null (y no se menciona).
- Descalificaciones políticas literales sí; tacos e insultos vejatorios, no.
- "gancho" (8-nov-2026, el usuario: «la frase gancho tiene que tener impacto y después desarrollas»): el trozo LITERAL y
  seguido de la cita con más impacto, 3-12 palabras («Les vamos a freír a impuestos», «Alí Babá tenía 40 ladrones, y Pedro
  Sánchez tiene ya 130 imputados»). La voz ABRE el Short con él, sin presentación; si la cita ya es corta, el gancho es
  la cita entera. Que no cambie el sentido (si la cita es condicional, «si han robado…», el gancho conserva el «si»).
- VARIOS GANCHOS EN UN SHORT: si el día tiene más frases fuertes que Shorts, UNO de los Shorts puede reunir 2-3 ganchos
  de personas y partidos distintos con un hilo común (impuestos, corrupción, el voto...): ponlos en "segmentos" (cada
  uno con quien, cargo, partido, kicker, gancho, cita, destaca, fuente y un "contexto" de 2-3 frases) y deja "cita" y
  "gancho" del Short iguales a los del primero. Con varios ganchos dura 40-60 s.
- "entrada": cómo PRESENTA la voz la cita, en tono de bar y ≤ 16 palabras («Ojo a lo que suelta Ayuso en redes», «Y va
  Colau y le dice a la marquesa»). Sin «aseguró», «por su parte», «afirma».
- "contexto": 4-6 frases FLUIDAS y coloquiales (60-90 palabras: el Short dura 25-40 s). Que fluya como una conversación:
  frases de longitud variada, comas y puntos suspensivos para las pausas, conectores orales («Y claro…», «Mira…», «Fíjate…»),
  verbos coloquiales, y algo de ironía sobre la situación (nunca a favor de un bando). Cifras en DÍGITOS («47 detenidos»,
  «el 41 por ciento», «29 de noviembre»). Nada de ráfagas de frases de una palabra (con Tristán suenan abruptas)., escritas para el oído y con conectores. Tómalas y adáptalas del GUION
  APROBADO del bloque donde sale la frase (ya está verificado): qué ha pasado, a qué se refiere la frase, el dato o
  antecedente que ayuda a entenderla (quién, cuándo, cuánto) y, si el guion la da, la versión de la otra parte. Un
  programa comprueba cada frase contra el material y quita las que no estén respaldadas. Sin adjetivos ni verbos valorativos propios (nada de «arremete», «carga», «estalla»: «critica», «defiende»,
  «pide», «acusa» si la fuente lo dice). No adelanta la réplica (la voz ya dice «X le responde»), no interpreta
  intenciones ni añade lo que la persona «considera» si no está en el material.
- "categoria": el formato, uno de «POLÉMICA» (cruce de declaraciones entre políticos), «RÉPLICA» (respuesta corta y directa
  en redes a otro político), «ÚLTIMA HORA» (un hecho noticioso de hoy: decisión, anuncio, dato) o «ANÁLISIS» (explica
  datos o antecedentes). Que sea verdad: «ÚLTIMA HORA» solo si el hecho es de hoy.
- "pregunta": la pregunta final, de sí o no, ≤ 6 palabras, que NOMBRA por su apellido a quien dijo la frase y pregunta
  por la frase, sin tomar partido: «¿Tiene razón Ayuso?», «¿Se pasó Rufián?», «¿Exagera Abascal?», «¿Acierta Colau?».
  Nunca preguntas sobre el futuro ni dirigidas al espectador («¿Subirán los impuestos?», «¿Te pagarían un programa?»).
- "escenas": 6 descripciones EN INGLÉS de lo que se ve, para seis viñetas de cómic animadas DISTINTAS que cuenten la
  noticia en orden (la primera, la del gancho), cada una con algo que se mueva (gente que camina, gesticula, escribe...)
  (lugares, objetos, gente anónima; concretas; sin texto, sin carteles con letras, sin personas reales reconocibles).
- "kicker": 2-5 palabras en mayúsculas para la pantalla: quién y a quién («AYUSO, A SÁNCHEZ»).
- "destaca": la palabra de la cita que irá resaltada en amarillo.
- "portada": 2-5 palabras LITERALES de la cita, las de más gancho, para el titular enorme de la miniatura
  («HAY QUE SER COBARDE», «PRINGADO HASTA EL CHÓFER»).
- "hashtags": 8-12 sin repetir: el del protagonista (#Ayuso), el del aludido, sus partidos (#PP, #PSOE), el del tema
  (#CaraACara), #PolíticaEspañola, #NoticiasDeHoy y #ElHoyformativo. Solo de lo que sale en el Short.
- "etiquetas": 15-25: nombre completo y corto de cada persona que sale, su cargo, sus partidos, el tema con
  variantes de búsqueda, «política española», «noticias de hoy», «shorts política». Solo de lo que sale.
- "titulo": ≤ 70 caracteres, con la frase o su parte más fuerte entre comillas y quién la dice, con verbo neutro
  («dice», «afirma», «responde a»; nunca «sentencia», «zanja», «estalla», «arremete»). Sin el nombre del canal.
Responde SOLO con JSON: {{"shorts": [{{"quien": "...", "cargo": "...", "partido": "...", "a_quien": "...",
"categoria": "POLÉMICA", "kicker": "...", "entrada": "...", "gancho": "...", "cita": "...", "destaca": "...", "fuente": "X (@cuenta) / Telegram / medio...",
"enlace": "...", "contexto": "...", "replica": {{"quien": "...", "cargo": "...", "partido": "...", "cita": "...", "prueba": "..."}} o null,
"pregunta": "¿...?", "escenas": ["...", "...", "...", "...", "...", "..."], "portada": "...", "hashtags": ["#..."], "etiquetas": ["..."], "titulo": "...",
"segmentos": null o [{{"quien": "...", "cargo": "...", "partido": "...", "kicker": "...", "gancho": "...", "cita": "...",
"destaca": "...", "fuente": "...", "contexto": "..."}}]}}]}}

MATERIAL APROBADO (guion del vídeo de hoy, ya verificado):
{guion}

PUBLICACIONES OFICIALES DEL DÍA (redes.md: X, webs, Telegram, Bluesky):
{redes}"""


VALORATIVAS = ["arremet", "carga contra", "cargó contra", "cargan contra", "estall", "provoc", "respuesta", "respondi", "zasca", "humill", "destroz", "contundente", "dura crítica",
               "responde", "réplica", "contesta", "considera que", "polémic", "escándalo", "lapidari"]


VERIFICA = """Eres verificador de un informativo neutral. Para cada FRASE numerada, di si está respaldada por el MATERIAL
(los hechos, las cifras, las fechas y las atribuciones tienen que estar en él; una interpretación de intenciones, un
adjetivo valorativo o un dato que no aparece = NO respaldada). Responde SOLO JSON: {{"respaldadas": [números]}}

FRASES:
{frases}

MATERIAL:
{material}"""


def verifica_contexto(contexto, guion, redes):
    """Segunda pasada (6-nov-2026, contexto más largo): solo se quedan las frases respaldadas por el material. Si
    Gemini no responde, se quedan las dos primeras (lo que antes cabía), que son las más pegadas a la cita."""
    frases = [f for f in re.split(r"(?<=[.?!])\s+", (contexto or "").strip()) if f]
    if len(frases) <= 1:
        return contexto
    r = gem.pide(VERIFICA.format(frases="\n".join(f"{k + 1}. {f}" for k, f in enumerate(frases)),
                                 material=(guion + "\n" + redes)[:60000]), como_json=True)
    if not isinstance(r, dict) or not isinstance(r.get("respaldadas"), list):
        print("  (verificación del contexto sin respuesta: se dejan las dos primeras frases)")
        return " ".join(frases[:2])
    ok = {int(x) for x in r["respaldadas"] if str(x).isdigit()}
    quitadas = [f for k, f in enumerate(frases) if k + 1 not in ok]
    for f in quitadas:
        print(f"  contexto: quitada por no estar respaldada: «{f[:80]}»")
    return " ".join(f for k, f in enumerate(frases) if k + 1 in ok)


def enriquece_contexto(contexto, cita, G, objetivo=70):
    """13-nov-2026 (el usuario: «los Shorts salen muy cortos»): si el contexto verificado queda fino, se completa con las
    frases del BLOQUE del vídeo largo que ya están comprobadas (las que no estén ya), hasta ~`objetivo` palabras. Así el
    Short llega al mínimo (~35 s) sin inventar nada: todo sale del guion aprobado del día."""
    nc = _norm(cita)
    sec = next((s for s in G.get("secciones", []) if nc in _norm(" ".join(p.get("di", "") for p in s.get("pasos", [])))), None)
    if not sec:
        return contexto
    di = " ".join(p.get("di", "") for p in sec.get("pasos", []))
    frases = [f.strip() for f in re.split(r"(?<=[.?!»])\s+", di) if len(f.split()) >= 4]
    ya = _norm(contexto)
    out = contexto.strip()
    for f in frases:
        if len(out.split()) >= objetivo:
            break
        nf = _norm(f)
        if nf in ya or nc in nf or _norm(f[:30]) in ya:    # ni repetir ni volver a soltar la cita
            continue
        out = (out + " " + f).strip()
        ya = _norm(out)
    return out


_VACIAS = set("el la los las un una unos unas de del al a y e o u que en con por para su sus se le les lo es son ha han "
               "he hay como mas más pero ya no si sí este esta esto ese esa eso muy tan".split())


def _toks(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.findall(r"[a-z0-9]+", s)


_MULETILLAS = ["segun el", "segun ella", "segun ellos", "lo suyo", "vuelve a la carga", "ha vuelto a la carga", "y claro",
               "ojo", "mira", "agarrate", "y la explicacion es esta", "no se ha quedado callado", "le recuerda", "mientras tanto"]


VETADAS = [r"\bzasca"]   # 19-nov-2026 (usuario): «zasca» no se usa NUNCA en el guion (NORMAS.md §3)


def vetadas(voz):
    """Palabras prohibidas por la guía que aparecen en la voz (fuera de las citas literales «…»)."""
    fuera = re.sub(r"«[^»]*»", " ", voz or "").lower()
    out = [f"«{v.replace(chr(92) + 'b', '')}» (palabra prohibida: no se usa nunca)" for v in VETADAS if re.search(v, fuera)]
    try:                                                 # 20-nov-2026: y las de archivo/palabras_vetadas.json
        for x in json.loads((RAIZ / "archivo" / "palabras_vetadas.json").read_text(encoding="utf-8")):
            if x["palabra"].lower() in fuera:
                out.append(f"«{x['palabra']}» (vetada: {x.get('motivo', '')}; usa {x.get('alternativa', 'otra')})")
    except (OSError, ValueError, KeyError, TypeError):
        pass
    return out


def repeticiones(voz, n=4, muletillas=True, cierre=True):
    """19-nov-2026 (usuario: «estás repitiendo partes»): trozos del guion que se dicen DOS veces. Devuelve la lista de
    expresiones repetidas (n-gramas de n palabras con al menos 2 con contenido), sin contar el cierre fijo (desde la
    pregunta final). También avisa si una misma cita «…» (o casi) sale dos veces."""
    cuerpo = voz.rsplit("¿", 1)[0] if (cierre and "¿" in voz) else voz
    t = _toks(cuerpo)
    vistos, reps = {}, []
    for i in range(len(t) - n + 1):
        g = tuple(t[i:i + n])
        if sum(w not in _VACIAS and len(w) > 2 for w in g) < 2:
            continue
        if g in vistos and i - vistos[g] >= n and " ".join(g) not in " ".join(reps):
            reps.append(" ".join(g))
        vistos.setdefault(g, i)
    plano = " " + " ".join(t) + " "
    for m in (_MULETILLAS if muletillas else []):                                  # muletillas cortas que, dichas dos veces, suenan a repetición
        if plano.count(f" {m} ") >= 2 and m not in reps:
            reps.append(m)
    citas = [" ".join(_toks(c)) for c in re.findall(r"«([^»]+)»", cuerpo)]
    for a in range(len(citas)):
        for b in range(a + 1, len(citas)):
            if citas[a] and (citas[a] in citas[b] or citas[b] in citas[a]):
                reps.append(f"cita repetida: «{citas[a][:40]}»")
    return reps


def _sin_repetir(contexto, ya):
    """Quita del contexto las frases que vuelven a contar lo que ya dicen la entrada, la cita o la réplica (≥ 60 % de sus
    palabras con contenido ya dichas)."""
    dichas = {w for w in _toks(ya) if w not in _VACIAS and len(w) > 2}
    fuera = []
    for f in re.split(r"(?<=[.!…])\s+", (contexto or "").strip()):
        cont = [w for w in _toks(f) if w not in _VACIAS and len(w) > 2]
        if cont and sum(w in dichas for w in cont) / len(cont) >= 0.6:
            continue
        fuera.append(f)
        dichas |= set(cont)
    return " ".join(fuera).strip()


def _norm(s):
    """Minúsculas y espacios uniformes. Las comillas se CONSERVAN (todas como "): si el medio solo entrecomilla una
    palabra («ve "irresponsable" decir...»), la frase entera no casa y no se atribuye como cita."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[«»“”'‘’]", '"', s)
    return re.sub(r"\s+", " ", s).strip(' ."')


MEJORES = """Eres el guionista de Shorts de «El Hoyformativo» (tono Vikingo desenfadado, NEUTRAL: lee NORMAS.md §3-§4).
El director quiere un Short de 25-40 s con LAS MEJORES FRASES de {persona} sobre «{tema}». Elige sus {k} frases con más
impacto (las más comentadas por los medios, las más directas, las que más retratan el cara a cara), de más a menos. Reglas:
- Cada frase tiene que ser de {persona} DICHA en «{tema}» (no de otro día ni de su entorno) y estar LITERAL en el material
  de abajo, entre comillas del medio (cópiala letra a letra; un programa lo comprueba). Entera palabras suyas, 4+ palabras,
  sin comillas dentro. Nada de tacos ni insultos vejatorios. NUNCA frases de su equipo, su entorno, «fuentes» o su
  partido, ni dichas antes del debate. En "prueba" copia letra a letra el fragmento del material (20-60 palabras) que
  muestra que {persona} la dijo en «{tema}» (con su nombre o apellido y la frase).
- Para cada frase, "contexto": 1-2 frases coloquiales (15-30 palabras) que digan a qué venía (el bloque del debate, a qué
  o a quién contestaba) SOLO con datos del material. Sin adjetivos ni verbos valorativos («arremete», «humilla»,
  «destroza», «le pone en su sitio»...), sin decir quién ganó. Cifras en dígitos.
- "entrada": cómo presenta la voz el Short tras la primera frase, ≤ 14 palabras, tono de bar («Así se despachó Feijóo
  en el cara a cara»), sin «aseguró» ni «por su parte».
- "pregunta": de sí o no, ≤ 6 palabras, con su apellido («¿Convenció Feijóo?», «¿Tiene razón Sánchez?»).
- "escenas": 6 descripciones EN INGLÉS de viñetas de cómic animadas distintas (plató de debate de televisión, atriles,
  mesa, focos, público anónimo en casa viendo la tele...; sin texto ni personas reales reconocibles).
- "kicker": 2-4 palabras en mayúsculas («FEIJÓO, EN EL CARA A CARA»). "portada": 2-5 palabras LITERALES de la mejor frase.
- "titulo": ≤ 70 caracteres, verbo neutro («Las frases de Feijóo en el cara a cara»), sin el nombre del canal.
- "hashtags" 8-12 (#CaraACara, su apellido, su partido, #PolíticaEspañola, #NoticiasDeHoy, #ElHoyformativo...) y
  "etiquetas" 15-25, solo de lo que sale.
Responde SOLO con JSON: {{"quien": "{persona}", "cargo": "...", "partido": "...", "a_quien": "...", "categoria": "POLÉMICA",
"kicker": "...", "entrada": "...", "frases": [{{"cita": "...", "destaca": "...", "fuente": "medio", "prueba": "...", "contexto": "..."}}],
"pregunta": "¿...?", "escenas": ["..."], "portada": "...", "hashtags": ["#..."], "etiquetas": ["..."], "titulo": "..."}}

MATERIAL APROBADO (guion del vídeo de hoy, ya verificado):
{guion}

LO QUE PUBLICAN LOS MEDIOS (artículos del día sobre el tema):
{articulos}

PUBLICACIONES OFICIALES DEL DÍA (redes.md):
{redes}"""


def _articulos_tema(dia, claves, tope=45000):
    out, n = [], 0
    for f in sorted((dia / "articulos").glob("*.txt")) if (dia / "articulos").exists() else []:
        t = f.read_text(encoding="utf-8", errors="ignore")
        if claves and not any(c.lower() in t.lower() for c in claves):
            continue
        out.append(t[:6000])
        n += len(out[-1])
        if n > tope:
            break
    return "\n\n".join(out)[:tope]


def _atribuida(nc, ape, textos_n, ajenas, radio=250):
    """La cita está en alguna fuente con el apellido de quien la dice cerca y sin «su entorno», «fuentes de»... cerca."""
    na = _norm(ape)
    for t in textos_n:
        for m in re.finditer(re.escape(nc), t):
            cerca = t[max(0, m.start() - radio): m.end() + 80]
            if na in cerca and not any(x in t[max(0, m.start() - 120): m.start()] for x in ajenas):
                return True
    return False


def citas_inventadas(fecha, voz):
    """20-nov-2026: devuelve las citas «» de la voz que NO están literales (sin contar la puntuación) en el material del
    día: guion aprobado, redes.md, noticias.json y artículos de los medios. Así Opus no puede cambiar ni completar una cita."""
    import prechequeo as P
    ep = RAIZ / "dia" / fecha / "episodio.json"
    base = P._fuentes(fecha) + " " + (P._n(ep.read_text(encoding="utf-8")) if ep.exists() else "")
    return [c for c in re.findall(r"«([^»]+)»", voz or "") if P._n(c) not in base]


def mejores_frases(fecha, pedidos, enc, G, guion, redes):
    """20-nov-2026 (el usuario: «quiero dos [Shorts], uno de Feijóo con sus mejores frases y otro de Sánchez con sus
    mejores frases»): un Short por persona con sus 3 mejores frases LITERALES del tema del encargo (encargo.json →
    shorts_personas [{persona, tema, mejores_frases: true}]). Cada frase se comprueba literal en el guion aprobado, en
    redes.md o en los artículos de los medios del día; el contexto, contra ese mismo material."""
    dia = RAIZ / "dia" / fecha
    mono = enc.get("monografico") or {}
    art = _articulos_tema(dia, mono.get("claves") or [])
    material = guion + "\n" + art
    base = _norm(guion + "\n" + redes + "\n" + art)
    (dia / "shorts").mkdir(exist_ok=True)
    (dia / "shorts" / "imagenes_usadas.json").unlink(missing_ok=True)
    for viejo in (dia / "shorts").glob("short_*"):
        if viejo.is_file():
            viejo.unlink()
    antes = ""                                         # lo publicado el día anterior: lo dicho ANTES del acontecimiento
    try:
        import datetime as _dt
        prev = RAIZ / "dia" / (_dt.date.fromisoformat(fecha) - _dt.timedelta(days=1)).isoformat()
        antes = _norm(" ".join(f.read_text(encoding="utf-8", errors="ignore") for f in
                               [*(prev / "articulos").glob("*.txt"), prev / "redes.md", prev / "episodio.json"] if f.exists()))
    except ValueError:
        pass
    ajenas = ("entorno", "equipo", "fuentes", "núcleo", "nucleo", "colaboradores", "dirección del", "en ferraz", "en génova")
    textos_n = [_norm(t) for t in [guion, redes, *art.split("\n\nMEDIO: ")]]
    buenos, usadas = 0, set()
    for pd in pedidos:
        persona, tema = pd.get("persona", ""), pd.get("tema") or mono.get("tema", "")
        ape = persona.split()[-1] if persona else ""
        r = None
        for _ in range(2):
            r = gem.pide(MEJORES.format(persona=persona, tema=tema, k=4, guion=guion[:30000], articulos=art,
                                        redes=redes[:15000]), como_json=True)
            if isinstance(r, dict) and r.get("frases"):
                break
        if not isinstance(r, dict) or not r.get("frases"):
            print(f"  {persona}: Gemini no responde (sin Short de mejores frases)")
            continue
        frases = []
        for f in r["frases"]:
            c = (f.get("cita") or "").strip().strip("«»“”\"").strip().rstrip(".")
            nc = _norm(c)
            if len(c.split()) < 4 or re.search(r"[«»“”\"]", c):
                print(f"  descartada: «{c[:60]}» (corta o parcial)")
            elif nc not in base:
                print(f"  descartada: «{c[:60]}» no está literal en el material")
            elif any(nc in u or u in nc for u in usadas):
                print(f"  descartada: «{c[:60]}» ya sale")
            elif vetadas(f"«{c}»".replace("«", "").replace("»", "")):
                print(f"  descartada: «{c[:60]}» lleva una palabra que la voz lee mal (archivo/palabras_vetadas.json)")
            elif antes and nc in antes:
                print(f"  descartada: «{c[:60]}» ya estaba publicada el día anterior (no es del acontecimiento)")
            elif not _atribuida(nc, ape, textos_n, ajenas):
                print(f"  descartada: «{c[:60]}» no aparece junto a {ape} en las fuentes (o es de su entorno)")
            else:
                ctx = f.get("contexto") or ""
                malas = [w for w in VALORATIVAS if w in ctx.lower() and w not in ("respuesta", "responde", "respondi", "contesta")]
                ctx = "" if malas else verifica_contexto(ctx, material, redes)
                frases.append({"cita": c, "destaca": f.get("destaca", ""), "fuente": f.get("fuente", ""), "contexto": ctx})
                usadas.add(nc)
            if len(frases) >= 3:
                break
        if len(frases) < 2:
            print(f"  {persona}: solo {len(frases)} frase(s) comprobada(s): sin Short")
            continue
        ent = (r.get("entrada") or f"Así habló {ape} en el cara a cara").strip().rstrip(":?.")
        preg = (r.get("pregunta") or "").strip()
        if not (preg.startswith("¿") and preg.endswith("?") and len(preg.split()) <= 8 and ape in preg):
            preg = f"¿Convenció {ape}?"
        enlaces = ["Y otra:", "Y no se quedó ahí:", "Y para rematar:"]
        voz = f"«{frases[0]['cita']}». {ent}. {frases[0]['contexto']}".strip()
        for i, f in enumerate(frases[1:]):
            voz += f" {enlaces[i % len(enlaces)]} «{f['cita']}». {f['contexto']}".rstrip()
        voz += f" {preg} Te leo en comentarios. Y dale a suscribirte, que he visto que aún no lo has hecho."
        voz = re.sub(r"\s+", " ", voz).strip()
        import apto_anuncios as AA
        s = dict(r)
        s.update({"quien": persona, "frases": frases, "cita": frases[0]["cita"], "gancho": frases[0]["cita"],
                  "destaca": frases[0]["destaca"], "fuente": frases[0]["fuente"], "replica": None, "segmentos": None,
                  "contexto": " ".join(f["contexto"] for f in frases), "entrada": ent, "pregunta": preg, "voz": voz,
                  "mejores_frases": True})
        s.pop("segmentos")
        if ape.upper() not in (s.get("kicker") or "").upper():   # 20-nov: el kicker de Sánchez salió «FEIJÓO, ...»
            s["kicker"] = f"{ape.upper()}, EN EL CARA A CARA"
        s["titulo"] = AA.elige(s.get("titulo", ""), f"Las frases de {ape} en el cara a cara"[:95], f"{ape}: sus frases")
        s["portada"] = AA.elige(s.get("portada", ""), frases[0]["cita"], s.get("kicker", ""))
        buenos += 1
        (dia / "shorts" / f"short_{buenos}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"short_{buenos}: {s.get('kicker', '')} · {len(frases)} frases · ~{len(voz.split()) / 2.75:.0f} s")
    if not buenos:
        sys.exit(1)


def main(fecha, n=3):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    guion = "\n".join(p.get("di", "") + " " + json.dumps(p.get("ve") or {}, ensure_ascii=False)
                      for s in G["secciones"] for p in s["pasos"])
    redes = (dia / "redes.md").read_text(encoding="utf-8")[:30000] if (dia / "redes.md").exists() else ""
    enc = json.loads((dia / "encargo.json").read_text(encoding="utf-8")) if (dia / "encargo.json").exists() else {}
    obligada = ""
    pedidos = []                                       # 13-nov: uno o varios Shorts obligados (persona y, si se da, tema)
    if enc.get("short_persona"):
        pedidos.append({"persona": enc["short_persona"]})
    for x in (enc.get("shorts_personas") or []):
        pedidos.append(x if isinstance(x, dict) else {"persona": x})
    for i, pd in enumerate(pedidos):
        quien_p, tema_p = pd.get("persona", ""), pd.get("tema", "")
        obligada += (f"\n\nOBLIGATORIO: el Short {i + 1} es {quien_p}" + (f", sobre {tema_p}" if tema_p else "") +
                     f", con su frase más fuerte del día (comprobada literal en el material) y {quien_p} de protagonista.")
    if pedidos and all(pd.get("mejores_frases") for pd in pedidos):    # 20-nov: Shorts de «mejores frases»
        return mejores_frases(fecha, pedidos, enc, G, guion, redes)
    if enc.get("evita_temas"):
        obligada += f"\n\nEVITA estos temas (ya tratados o que no quiere el director): {', '.join(enc['evita_temas'])}."
    if enc.get("cruce") and enc.get("shorts_hechos"):     # 22-nov: el Short del cruce ya está montado: los demás, de otra cosa
        obligada += f"\n\nEVITA el tema «{enc.get('tema', '')}»: su Short ya está hecho."
    elif enc.get("verificada") and enc.get("cruce") and "short" in enc.get("para", ["short"]):
        # 21-nov-2026 (el usuario): Short de CRUCE DE DECLARACIONES por encargo: la frase que lo enciende y sus réplicas,
        # todas comprobadas (encargo.py); el material nuevo del día (redes.md, búsqueda en X del encargo) puede sumar más.
        buenas = [x for x in enc["cruce"] if x.get("verificada")]
        redes = "".join(f"- **{x['persona']}** ({x.get('partido', '')}; {x.get('canal', 'X')}; {x.get('papel', '')}): "
                        f"{x['frase']} ({x.get('enlace', '')}) [comprobado: {x.get('prueba', '')[:160]}]\n" for x in buenas) + redes
        obligada = (f"\n\nOBLIGATORIO (lo pide el director y está comprobado): el PRIMER Short es un CRUCE DE DECLARACIONES "
                    f"sobre «{enc['tema']}» ({enc.get('argumento', '')}), DEDICADO SOLO A ESA NOTICIA. Formato: "
                    f"{enc.get('formato', 'frase y réplica')}. Empieza por la frase que lo desata (\"cita\"), sigue con "
                    "las réplicas más fuertes (\"replica\" y, si hay más, \"segmentos\") y, si existe, la contrarréplica; "
                    "solo frases LITERALES de la lista de arriba o del material, con su autor real. Las dos partes con su "
                    "voz; sin declarar ganador." + "".join(f" OJO: {x['ojo']}" for x in buenas if x.get("ojo"))
                    + "".join(f" CONTEXTO: {c}." for c in enc.get("contexto", []))
                    + (f" EQUILIBRIO: {enc['equilibrio']}." if enc.get("equilibrio") else ""))
    elif enc.get("verificada") and enc.get("persona") and "short" in enc.get("para", ["short"]):     # encargo del director, ya comprobado
        redes = f"- **{enc['persona']}** ({enc.get('canal', 'X')}, @{enc.get('cuenta', '')}): {enc['frase']} " \
                f"({enc.get('enlace', '')}) [comprobado: {enc.get('prueba', '')}]\n" + redes
        obligada = (f"\n\nOBLIGATORIO (lo pide el director y está comprobado): el PRIMER Short es la frase «{enc['frase']}» "
                    f"de {enc['persona']} sobre «{enc.get('tema', '')}», DEDICADO SOLO A ESA NOTICIA: el contexto habla "
                    f"únicamente de ella (del guion aprobado sobre ese tema), sin mezclar otros temas.")
    fijo = enc.get("short_fijo") if enc.get("verificada") else None   # 8-nov: guion del Short escrito y comprobado a mano
    if fijo:
        obligada = ""
    r = gem.pide("ASÍ ELIGE LOS GANCHOS EL DIRECTOR (imítalo):\n" + EJEMPLOS[:6000] + "\n\n" + PROMPT.format(n=n + 2, guion=guion[:40000], redes=redes) + obligada, como_json=True)
    if isinstance(r, list):                              # a veces devuelve la lista sin envolver
        r = {"shorts": r}
    if not isinstance(r, dict) and fijo:
        r = {"shorts": []}                               # sin Gemini, al menos el del director
    if not isinstance(r, dict):
        print("Gemini no responde: hoy sin Shorts")
        sys.exit(2)
    base = _norm(guion + "\n" + redes)
    (dia / "shorts").mkdir(exist_ok=True)
    buenos, partidos, usadas = 0, set(), set()
    (dia / "shorts" / "imagenes_usadas.json").unlink(missing_ok=True)   # 11-nov: el registro de imágenes, de cero
    hechos = [int(k) for k in enc.get("shorts_hechos") or []]   # 22-nov: Shorts del encargo ya montados a mano: se quedan
    for viejo in (dia / "shorts").glob("short_*"):       # los de una vuelta anterior, fuera
        k_ = re.match(r"short_(\d+)", viejo.name)
        if viejo.is_file() and not (k_ and int(k_.group(1)) in hechos):
            viejo.unlink()
    for k_ in hechos:
        f_ = dia / "shorts" / f"short_{k_}.json"
        if f_.exists():
            h_ = json.loads(f_.read_text(encoding="utf-8"))
            buenos = max(buenos, k_)
            partidos.add(h_.get("partido"))
            for c_ in [h_.get("cita"), (h_.get("replica") or {}).get("cita")] + re.findall(r"«([^»]+)»", h_.get("voz", "")):
                if c_:
                    usadas.add(re.sub(r"^(y|e|pero|porque)\s+", "", _norm(c_)))
            print(f"short_{k_}: ya montado (encargo del director), se queda")
    if fijo:                                             # el del director va primero, tal cual (ya comprobado)
        buenos = 1
        for x in (fijo, fijo.get("medio"), fijo.get("replica")):
            if x:
                usadas.add(re.sub(r"^(y|e|pero|porque)\s+", "", _norm(x["cita"])))
        partidos.add(fijo.get("partido"))
        (dia / "shorts" / "short_1.json").write_text(json.dumps(fijo, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"short_1: {fijo['kicker']} · guion fijo del director")
    cands = r.get("shorts", [])
    try:                                               # 10-nov: el experto en YouTube puntúa y pule; primero los mejores
        import experto_youtube as EX
        cands = EX.pule_shorts(cands)
    except Exception as e:
        print(f"  (experto sin respuesta: {type(e).__name__})")
    vistos_p, orden, resto = set(), [], []                # reparto: primero un Short por partido; si faltan, repite
    for s in cands:
        (resto if s.get("partido") in vistos_p else orden).append(s)
        vistos_p.add(s.get("partido"))
    for s in orden + resto:
        if buenos >= n:
            break
        for obj in [s, s.get("replica") or {}] + [g for g in (s.get("segmentos") or []) if isinstance(g, dict)]:
            for campo in ("cita", "gancho"):                 # 10-nov: comillas que envuelven la cita entera, fuera
                v = (obj.get(campo) or "").strip()
                if len(v) > 2 and v[0] in "«“\"" and v[-1] in "»”\"" and not re.search(r"[«»“”\"]", v[1:-1]):
                    obj[campo] = v[1:-1].strip()
        if s.get("nota_experto") is not None and s["nota_experto"] < 6:   # menos, pero mejor (10-nov)
            print(f"  descartada por el experto ({s['nota_experto']:.0f}/10): «{s.get('cita', '')[:50]}»")
            continue
        if re.search(r"[«»“”\"]", s.get("cita", "")):
            print(f"  descartada: «{s.get('cita', '')[:60]}» es una cita parcial (solo entrecomilla una parte)")
            continue
        if _norm(s.get("cita")) not in base:
            print(f"  descartado: la cita «{s.get('cita', '')[:60]}» no está literal en el material")
            continue
        nc = re.sub(r"^(y|e|pero|porque)\s+", "", _norm(s.get("cita")))      # 8-nov: «Y si han...» = «Si han...»
        if len(s.get("cita", "").split()) < 4 or any(nc in u or u in nc for u in usadas):
            print(f"  descartada: «{s.get('cita', '')[:60]}» es muy corta o ya sale en otro Short")
            continue
        malas = [w for w in VALORATIVAS if w in s.get("contexto", "").lower()]
        if malas:                                       # se quita la frase que lo lleva; si no queda nada, fuera
            frases = [f for f in re.split(r"(?<=\.)\s+", s["contexto"]) if not any(w in f.lower() for w in malas)]
            print(f"  contexto con {malas}: se quita esa frase")
            if not frases:
                continue
            s["contexto"] = " ".join(frases)
        rep = s.get("replica")
        if rep and (_norm(rep.get("cita")) not in base or not rep.get("prueba") or _norm(rep["prueba"]) not in base):
            print(f"  réplica quitada (no literal o sin prueba de que contesta): «{rep.get('cita', '')[:60]}»")
            s["replica"] = None
        usadas.add(re.sub(r"^(y|e|pero|porque)\s+", "", _norm(s["cita"])))
        if s.get("replica"):
            usadas.add(re.sub(r"^(y|e|pero|porque)\s+", "", _norm(s["replica"]["cita"])))
        if s.get("partido") in partidos:
            print(f"  aviso: {s.get('partido')} repite protagonista (no había más partidos con frase válida)")
        partidos.add(s.get("partido"))
        s["contexto"] = verifica_contexto(s["contexto"], guion, redes)
        if not s.get("segmentos") and len(s["contexto"].split()) < 60:   # 13-nov: que no salga corto (mín. ~35 s)
            s["contexto"] = enriquece_contexto(s["contexto"], s["cita"], G, objetivo=75)
            print(f"  contexto completado desde el bloque del vídeo largo ({len(s['contexto'].split())} palabras)")
        if not s["contexto"]:
            print(f"  descartada: «{s.get('cita', '')[:50]}» se queda sin contexto comprobado")
            continue
        s["titulo"] = re.sub(r"\b(sentencia|zanja|estalla|arremete|carga|clama|lanza|suelta)\b", "dice", s.get("titulo", ""))
        import apto_anuncios as AA                     # 10-nov: título y portada sin tacos ni insultos (anuncios)
        s["titulo"] = AA.elige(s["titulo"], f"{s.get('quien', '')}: «{s.get('gancho') or s['cita']}»"[:95],
                               f"{s.get('kicker', '').title()}: la frase del día")
        s["portada"] = AA.elige(s.get("portada", ""), s.get("gancho", ""), s.get("kicker", ""))
        buenos += 1
        cita = s["cita"].strip().rstrip(".")
        gancho = (s.get("gancho") or "").strip().rstrip(".")
        if not gancho or _norm(gancho) not in _norm(cita):    # el gancho tiene que ser un trozo literal de la cita
            gancho = cita
        cond = re.search(r"\b(si|cuando|aunque|salvo que|en caso de que)\b", _norm(cita).split(_norm(gancho))[0])
        if gancho != cita and cond:                            # 8-nov: recortar una condición cambia el sentido
            print(f"  gancho «{gancho[:40]}» sin su condición («{cond.group(1)}…»): va la cita entera")
            gancho = cita
        s["gancho"] = gancho
        # 17-nov-2026 (usuario: «repites la frase gancho muy seguido y queda redundante»): el gancho se dice UNA vez; si la
        # cita empieza por él, después solo va el RESTO de la cita (no la cita entera otra vez).
        resto = cita
        if gancho != cita and cita.lower().startswith(gancho.lower()):
            resto = cita[len(gancho):].lstrip(" ,;:.—-–").strip()
        ent = s['entrada'].strip().rstrip(':?.').strip()
        # 19-nov-2026 (usuario: «estás repitiendo partes»): el contexto no vuelve a contar lo que ya dicen la entrada, la
        # cita o la réplica, y el enlace con el resto de la cita varía (antes siempre «Y la explicación es esta:»).
        rep_txt = (s.get("replica") or {}).get("cita", "") if isinstance(s.get("replica"), dict) else ""
        ctx = _sin_repetir(s['contexto'], f"{ent} {cita} {rep_txt}")
        enlaces = ["Y remata:", "Y sigue:", "Y lo completa así:", "Y añade:"]
        enlace = enlaces[sum(map(ord, cita)) % len(enlaces)]
        if gancho == cita:
            voz = f"{ent}: «{cita}». {ctx}"
        elif len(resto.split()) >= 3:
            voz = f"«{gancho}». {ent}. {enlace} «{resto}». {ctx}"
        else:
            voz = f"«{gancho}». {ent}. {ctx}"
        segs = []
        for g in s.get("segmentos") or []:                     # 8-nov: varios ganchos en un Short
            if not isinstance(g, dict) or _norm(g.get("cita")) not in base or not g.get("contexto"):
                continue
            gg = (g.get("gancho") or "").strip().rstrip(".")
            if not gg or _norm(gg) not in _norm(g["cita"]):
                gg = g["cita"].strip().rstrip(".")
            if gg != g["cita"].strip().rstrip(".") and re.search(r"\b(si|cuando|aunque|salvo que|en caso de que)\b",
                                                                 _norm(g["cita"]).split(_norm(gg))[0]):
                gg = g["cita"].strip().rstrip(".")
            ctx_g = verifica_contexto(g["contexto"], guion, redes)
            segs.append({"quien": g.get("quien", ""), "cargo": g.get("cargo", ""), "kicker": g.get("kicker", ""),
                         "cita": gg, "destaca": g.get("destaca", ""), "fuente": g.get("fuente", ""),
                         "contexto": f"Es {g.get('quien', '')}: «{g['cita'].strip().rstrip('.')}». " + (ctx_g or "")})
        if len(segs) >= 2:
            for g in segs:                                    # 8-nov: sin numerar los contenidos (el director)
                g["entrada"] = "«" + g["cita"][:20]
            voz = " ".join(f"«{g['cita']}». {g['contexto']}" for g in segs)
            s["segmentos"] = segs
        else:
            s.pop("segmentos", None)
        if s.get("replica") and _norm(s['replica']['cita'])[:30] not in _norm(voz):   # 19-nov: si el contexto ya la cuenta, no se repite
            voz += f" {s['replica']['quien']} le responde: «{s['replica']['cita'].strip().rstrip('.')}»."
        preg = (s.get("pregunta") or "").strip()            # 10-nov: pregunta de sí o no que invite a comentar
        ape = (s.get("quien") or "").split()[-1] if s.get("quien") else ""
        if not (preg.startswith("¿") and preg.endswith("?") and len(preg.split()) <= 8 and ape and ape in preg):
            preg = f"¿Tiene razón {ape}?" if ape else "¿Qué opinas?"      # 11-nov: siempre sobre quien lo dijo
        s["pregunta"] = preg
        voz += f" {preg} Te leo en comentarios. Y dale a suscribirte, que he visto que aún no lo has hecho."
        palabras = len(voz.split())                          # Tristán: ~2,75 palabras/s
        maximo = 170 if s.get("segmentos") else 115          # 10-nov: 25-40 s (40-60 s con varios ganchos)
        if palabras > maximo:
            print(f"  AVISO: «{s['cita'][:40]}» sale de ~{palabras / 2.75:.0f} s (objetivo ≤ {maximo / 2.75:.0f} s)")
        if enc.get("verificada") and enc.get("frase") and buenos == 1 and _norm(enc["frase"]) in _norm(s["cita"]):   # 9-nov: la del director
            s["portada"] = enc["frase"]                          # es la portada y el gancho principal
            if not s.get("segmentos"):
                s["gancho"] = enc["frase"]
                voz = f"«{enc['frase']}». " + voz.split("». ", 1)[1] if voz.startswith("«") else f"«{enc['frase']}». " + voz
        s["voz"] = voz
        (dia / "shorts" / f"short_{buenos}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"short_{buenos}: {s['kicker']} · «{s['cita'][:70]}»" + (" · con réplica" if s.get("replica") else ""))
    if not buenos:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
