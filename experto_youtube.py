"""EXPERTO EN YOUTUBE Y MARKETING (10-nov-2026, el usuario: «menos pero de más calidad; tiene que parecer hecho a mano
por un humano con mucha experiencia en vídeos de YouTube y experto en marketing digital»). Gemini, con ese papel,
revisa cada pieza antes del montaje: puntúa el gancho y pule título, gancho, portada y pregunta. Todo lo que propone
pasa las reglas del canal: el gancho y la portada tienen que ser trozos LITERALES de la cita (sin cambiar el sentido),
el título y la portada sin tacos ni insultos (apto_anuncios), verbos neutros y sin tomar partido. Si no las cumple, se
queda lo de antes."""
from __future__ import annotations

import re
import unicodedata

import apto_anuncios as AA
import gem

SHORT = """Eres un productor de YouTube Shorts con 10 años de experiencia y experto en marketing digital, en un canal de
política española neutral y riguroso. Te paso varios Shorts candidatos del día. Para CADA uno:
- "nota" (0-10): fuerza del gancho para detener el scroll en el primer segundo (frase corta, directa, con nombre propio y
  conflicto), interés general y potencial de comentarios. Sé exigente: 8+ solo si es de verdad muy fuerte.
- "gancho": el trozo LITERAL de la cita (palabra por palabra, 3-10 palabras) con más impacto. No cambies ni una palabra.
  Si la cita es condicional («si…»), conserva la condición.
- "portada": 2-5 palabras LITERALES de la cita para el titular enorme de la portada.
- "titulo": ≤ 70 caracteres, como lo escribiría un experto: la frase o su parte más fuerte entre comillas y quién la dice,
  verbo neutro («dice», «responde», «afirma»), sin tacos ni insultos personales, sin clickbait engañoso, con #Shorts al final.
  NO añadas lugares, fechas ni hechos que no estén en la cita o el contexto.
- "pregunta": de sí o no, ≤ 6 palabras, sin tomar partido, que provoque comentarios («¿Tiene razón Ayuso?»).
Responde SOLO JSON: {{"shorts": [{{"n": 1, "nota": 0, "gancho": "...", "portada": "...", "titulo": "...", "pregunta": "..."}}]}}

CANDIDATOS:
{candidatos}"""

LARGO = """Eres un estratega de YouTube con 10 años de experiencia y experto en marketing digital, en un canal de política
española neutral y riguroso. Este es el vídeo de hoy (4-5 min). Escribe 5 títulos candidatos y elige el mejor:
- ≤ 70 caracteres; empieza por la frase literal más fuerte del día entre «» o por el conflicto con nombres propios;
- verbos neutros, sin tacos ni insultos personales, sin clickbait engañoso, sin el nombre del canal;
- que el que lo vea en el móvil entienda quién se enfrenta a quién y quiera saber más;
- NO añadas lugares, fechas, cifras ni hechos que no estén literalmente en los titulares o bloques de abajo (si no
  sabes dónde se dijo algo, no lo digas).
Responde SOLO JSON: {{"candidatos": ["..."], "mejor": "..."}}

TÍTULO ACTUAL: {titulo}
TITULARES DEL SUMARIO: {sumario}
BLOQUES: {bloques}"""


def _n(t):
    t = unicodedata.normalize("NFKC", t or "").lower()
    return re.sub(r"\s+", " ", re.sub(r"[«»“”\"'‘’.,;:¡!¿?]", " ", t)).strip()


def _literal(trozo, cita):
    return bool(trozo) and _n(trozo) in _n(cita) and len(trozo.split()) >= 2


def pule_shorts(candidatos):
    """Devuelve los candidatos ordenados por nota del experto, con sus mejoras aplicadas si cumplen las reglas."""
    if not candidatos:
        return candidatos
    txt = "\n".join(f"{k + 1}. {c.get('quien', '')} ({c.get('partido', '')}): «{c.get('cita', '')}» · contexto: "
                    f"{c.get('contexto', '')[:300]} · título propuesto: {c.get('titulo', '')}" for k, c in enumerate(candidatos))
    r = gem.pide(SHORT.format(candidatos=txt), como_json=True, temperatura=0.3, pensar="high",
                 modelos=[m for m in gem.MODELOS if "lite" not in m]) or {}
    for p in (r.get("shorts") or []) if isinstance(r, dict) else []:
        try:
            c = candidatos[int(p.get("n", 0)) - 1]
        except (ValueError, IndexError, TypeError):
            continue
        c["nota_experto"] = float(p.get("nota", 0) or 0)
        cita = c.get("cita", "")
        if _literal(p.get("gancho"), cita) and not re.search(r"\b(si|cuando|aunque)\b", _n(cita).split(_n(p["gancho"]))[0]):
            c["gancho"] = p["gancho"].strip().rstrip(".")
        if _literal(p.get("portada"), cita) and AA.limpio(p["portada"]):
            c["portada"] = p["portada"].strip()
        t = (p.get("titulo") or "").strip()
        if t and len(t) <= 100 and AA.limpio(t) and not re.search(r"\b(sentencia|zanja|estalla|arremete|carga|clama|suelta)\b", t, re.I):
            c["titulo"] = t
        q = (p.get("pregunta") or "").strip()
        if q.startswith("¿") and q.endswith("?") and len(q.split()) <= 8:
            c["pregunta"] = q
    return sorted(candidatos, key=lambda c: -c.get("nota_experto", 0))


def mejor_titulo(titulo, sumario, bloques):
    r = gem.pide(LARGO.format(titulo=titulo, sumario=" | ".join(sumario)[:1500], bloques=" | ".join(bloques)[:1500]),
                 como_json=True, temperatura=0.4, pensar="high", modelos=[m for m in gem.MODELOS if "lite" not in m]) or {}
    m = (r.get("mejor") or "").strip() if isinstance(r, dict) else ""
    material = _n(titulo + " " + " ".join(sumario) + " " + " ".join(bloques))
    nuevas = [w for w in re.findall(r"\b[A-ZÁÉÍÓÚÑ][\wáéíóúñ]+", m) if _n(w) not in material and m.find(w) > 0]
    if nuevas:                                         # nombres o lugares que no están en el vídeo: no se usa
        print(f"  título del experto descartado (añade {nuevas}): {m}")
        m = ""
    if m and len(m) <= 100 and AA.limpio(m) and not re.search(r"\b(sentencia|zanja|estalla|arremete|carga|clama|suelta)\b", m, re.I):
        return m
    return titulo
