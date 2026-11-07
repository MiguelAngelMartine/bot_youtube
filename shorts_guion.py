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

PROMPT = """Eres el editor de Shorts de «El Hoyformativo», informativo de política española en YouTube: neutral y riguroso,
pero con gancho (el «salseo»: los cruces de declaraciones entre políticos). Elige las {n} FRASES MÁS IMPACTANTES (de más a menos) del día
para hacer un Short de 40-50 segundos con cada una. Reglas:
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
- "entrada": cómo lo dice la voz antes de la cita, ≤ 14 palabras, neutra («Isabel Díaz Ayuso, sobre Sánchez, en X:»).
- "contexto": 4-5 frases (70-90 palabras), escritas para el oído y con conectores. Tómalas y adáptalas del GUION
  APROBADO del bloque donde sale la frase (ya está verificado): qué ha pasado, a qué se refiere la frase, el dato o
  antecedente que ayuda a entenderla (quién, cuándo, cuánto) y, si el guion la da, la versión de la otra parte. Un
  programa comprueba cada frase contra el material y quita las que no estén respaldadas. Sin adjetivos ni verbos valorativos propios (nada de «arremete», «carga», «estalla»: «critica», «defiende»,
  «pide», «acusa» si la fuente lo dice). No adelanta la réplica (la voz ya dice «X le responde»), no interpreta
  intenciones ni añade lo que la persona «considera» si no está en el material.
- "kicker": 2-5 palabras en mayúsculas para la pantalla: quién y a quién («AYUSO, A SÁNCHEZ»).
- "destaca": la palabra de la cita que irá resaltada en amarillo.
- "titulo": ≤ 70 caracteres, con la frase o su parte más fuerte entre comillas y quién la dice, con verbo neutro
  («dice», «afirma», «responde a»; nunca «sentencia», «zanja», «estalla», «arremete»). Sin el nombre del canal.
Responde SOLO con JSON: {{"shorts": [{{"quien": "...", "cargo": "...", "partido": "...", "a_quien": "...",
"kicker": "...", "entrada": "...", "cita": "...", "destaca": "...", "fuente": "X (@cuenta) / Telegram / medio...",
"enlace": "...", "contexto": "...", "replica": {{"quien": "...", "cargo": "...", "partido": "...", "cita": "...", "prueba": "..."}} o null,
"titulo": "..."}}]}}

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


def _norm(s):
    """Minúsculas y espacios uniformes. Las comillas se CONSERVAN (todas como "): si el medio solo entrecomilla una
    palabra («ve "irresponsable" decir...»), la frase entera no casa y no se atribuye como cita."""
    s = unicodedata.normalize("NFKC", s or "").lower()
    s = re.sub(r"[«»“”'‘’]", '"', s)
    return re.sub(r"\s+", " ", s).strip(' ."')


def main(fecha, n=3):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    guion = "\n".join(p.get("di", "") + " " + json.dumps(p.get("ve") or {}, ensure_ascii=False)
                      for s in G["secciones"] for p in s["pasos"])
    redes = (dia / "redes.md").read_text(encoding="utf-8")[:30000] if (dia / "redes.md").exists() else ""
    enc = json.loads((dia / "encargo.json").read_text(encoding="utf-8")) if (dia / "encargo.json").exists() else {}
    obligada = ""
    if enc.get("verificada") and "short" in enc.get("para", ["short"]):     # encargo del director, ya comprobado
        redes = f"- **{enc['persona']}** ({enc.get('canal', 'X')}, @{enc.get('cuenta', '')}): {enc['frase']} " \
                f"({enc.get('enlace', '')}) [comprobado: {enc.get('prueba', '')}]\n" + redes
        obligada = (f"\n\nOBLIGATORIO (lo pide el director y está comprobado): el PRIMER Short es la frase «{enc['frase']}» "
                    f"de {enc['persona']} sobre «{enc.get('tema', '')}», con el contexto del guion aprobado sobre ese tema.")
    r = gem.pide(PROMPT.format(n=n + 2, guion=guion[:40000], redes=redes) + obligada, como_json=True)
    if isinstance(r, list):                              # a veces devuelve la lista sin envolver
        r = {"shorts": r}
    if not isinstance(r, dict):
        print("Gemini no responde: hoy sin Shorts")
        sys.exit(2)
    base = _norm(guion + "\n" + redes)
    (dia / "shorts").mkdir(exist_ok=True)
    buenos, partidos, usadas = 0, set(), set()
    for viejo in (dia / "shorts").glob("short_*"):       # los de una vuelta anterior, fuera
        if viejo.is_file():
            viejo.unlink()
    cands = r.get("shorts", [])
    vistos_p, orden, resto = set(), [], []                # reparto: primero un Short por partido; si faltan, repite
    for s in cands:
        (resto if s.get("partido") in vistos_p else orden).append(s)
        vistos_p.add(s.get("partido"))
    for s in orden + resto:
        if buenos >= n:
            break
        if re.search(r"[«»“”\"]", s.get("cita", "")):
            print(f"  descartada: «{s.get('cita', '')[:60]}» es una cita parcial (solo entrecomilla una parte)")
            continue
        if _norm(s.get("cita")) not in base:
            print(f"  descartado: la cita «{s.get('cita', '')[:60]}» no está literal en el material")
            continue
        if len(s.get("cita", "").split()) < 4 or _norm(s.get("cita")) in usadas:
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
        usadas.add(_norm(s["cita"]))
        if s.get("replica"):
            usadas.add(_norm(s["replica"]["cita"]))
        if s.get("partido") in partidos:
            print(f"  aviso: {s.get('partido')} repite protagonista (no había más partidos con frase válida)")
        partidos.add(s.get("partido"))
        s["contexto"] = verifica_contexto(s["contexto"], guion, redes)
        if not s["contexto"]:
            print(f"  descartada: «{s.get('cita', '')[:50]}» se queda sin contexto comprobado")
            continue
        s["titulo"] = re.sub(r"\b(sentencia|zanja|estalla|arremete|carga|clama|lanza|suelta)\b", "dice", s.get("titulo", ""))
        buenos += 1
        cita = s["cita"].strip().rstrip(".")
        voz = f"{s['entrada'].rstrip(':').strip()}: «{cita}». {s['contexto'].strip()}"
        if s.get("replica"):
            voz += f" {s['replica']['quien']} le responde: «{s['replica']['cita'].strip().rstrip('.')}»."
        voz += " Todo el cruce, y el resto de la política del día, en el vídeo de hoy."
        s["voz"] = voz
        (dia / "shorts" / f"short_{buenos}.json").write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"short_{buenos}: {s['kicker']} · «{s['cita'][:70]}»" + (" · con réplica" if s.get("replica") else ""))
    if not buenos:
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 3)
