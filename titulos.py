"""CONTROL DE ATRIBUCIÓN EN LOS TÍTULOS (23-nov-2026; fallo real: el título automático del largo decía «Sánchez va ahora
de corderito» frente a Cayetana Álvarez de Toledo, como si la frase fuera de Sánchez). Si el título lleva una cita «…»,
mira de quién es (con la lista de citas del vídeo) y exige que su apellido salga en el título; si no sale, o si sale
otro hablante antes que él, rehace el título como «Apellido: «cita»». Uso: revisa(titulo, [(cita, quien), ...])."""
from __future__ import annotations

import re
import unicodedata


def _n(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", "".join(c for c in t if not unicodedata.combining(c)))).strip()


def _apellido(nombre):
    p = (nombre or "").split()
    if len(p) >= 4 and _n(p[-2]) == "de":                 # Cayetana Álvarez de Toledo -> «Cayetana» (como se la conoce)
        return p[0]
    return p[-1] if p else ""


def quien_dijo(frag, citas):
    f = _n(frag)
    for c, q in citas:
        cn = _n(c)
        if f and cn and (f in cn or cn in f):
            return q
    return None


def revisa(titulo, citas, sufijo=""):
    """Devuelve (titulo_bueno, aviso o "")."""
    m = re.search(r"«([^»]+)»", titulo) or re.search(r"\"([^\"]+)\"", titulo)
    if not m:
        return titulo, ""
    q = quien_dijo(m.group(1), citas)
    if not q:
        return titulo, ""
    antes, despues = _n(titulo[:m.start()]), _n(titulo[m.end():])
    claves = [k for k in {_n(x) for x in q.split() if len(x) > 3} | {_n(_apellido(q))} if k]
    destinatario = r"(?:^|\s)(?:a|al|contra|frente a|ante|sobre|para|con)\s+(?:\w+\s+){0,2}$"
    for k in claves:
        i = antes.find(k)
        if i >= 0 and not re.search(destinatario, antes[:i] + " "):
            return titulo, ""
    # «frase»: Quien a Otro  /  «frase», dice Quien: el PRIMER nombre tras la frase es el de quien la dijo
    otros = [k for _, o in citas if o and o != q for k in {_n(x) for x in o.split() if len(x) > 3} | {_n(_apellido(o))} if k]
    toks = despues.split()
    for i, w in enumerate(toks):
        if w in claves or w in otros:
            if w in claves and (i == 0 or toks[i - 1] not in ("a", "al", "contra", "frente", "ante", "con", "para", "sobre")):
                return titulo, ""
            break
    nuevo = f"«{m.group(1).strip()}»: {_apellido(q)}"      # 23-nov-2026: primero la frase, después quién
    if sufijo:
        nuevo += sufijo
    return nuevo, f"título rehecho: la frase es de {q} y el título no lo decía bien («{titulo}»)"


if __name__ == "__main__":
    cs = [("Sánchez va ahora de corderito. Pero no cuela", "Cayetana Álvarez de Toledo"),
          ("Al político se le exige ser respetuoso", "Pedro Sánchez")]
    for t in ["«Sánchez va ahora de corderito» frente a Cayetana Álvarez de Toledo",
              "Cayetana, a Sánchez: «Va ahora de corderito»",
              "Sánchez responde a Cayetana: «Al político se le exige ser respetuoso»"]:
        print(revisa(t, cs))
