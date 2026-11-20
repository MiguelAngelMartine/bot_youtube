"""VARIEDAD DE COLETILLAS (16-nov-2026, petición del usuario): las coletillas/chascarrillos de la paleta
(NORMAS.md (§4)) no deben repetirse entre vídeos del mismo día o del día siguiente. Este módulo registra las que
se usan (archivo/coletillas_usadas.json) y le da al redactor la lista de las que NO debe repetir (ventana de 2 días).
  - detecta(texto): coletillas de la paleta presentes en un texto.
  - registra(fecha, *textos): las apunta con su fecha.
  - evitar(dias=2): coletillas usadas en los últimos `dias` días (las que el redactor debe evitar).
  - escribe_evitar(ruta, dias=2): deja un .txt para pasarlo al redactor (va en comunes()).
Uso CLI:  python coletillas.py registra AAAA-MM-DD   (escanea los vídeos de ese día)
          python coletillas.py                       (imprime las coletillas a evitar ahora)
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).parent
REG = RAIZ / "archivo" / "coletillas_usadas.json"

# clave de detección (fragmento distintivo, en minúsculas y sin tildes) -> nombre de la coletilla para avisar al redactor.
CLAVES = {
    r"sindios": "esto es un sindiós",
    r"pulpo en un garaje": "más perdido que un pulpo en un garaje",
    r"cara de boniato": "cara de boniato",
    r"pinta regulera": "pinta regulera",
    r"encrucijada existencial": "encrucijada existencial",
    r"tieso que la mojama|la mojama": "más tieso que la mojama",
    r"fantasia mas turbia": "qué fantasía más turbia",
    r"bacanal de sinsentidos": "bacanal de sinsentidos",
    r"cuerpo como un botijo|como un botijo": "cuerpo como un botijo",
    r"escandalo de criatura": "qué escándalo de criatura",
    r"gremlin": "más agobiado que un gremlin en una sauna",
    r"ciervo con flequillo": "más raro que un ciervo con flequillo",
    r"menudo percal|\bpercal\b": "menudo percal",
    r"sinvivir": "sinvivir de categoría",
    r"despropos": "despropósito de dimensiones industriales",
    r"liao la mundial|se ha liao": "se ha liao la mundial en el convento",
    r"al turron": "al turrón",
    r"punto pelota": "así y punto pelota",
    r"movida mas gorda": "qué movida más gorda",
    r"ni tan mal": "ni tan mal",
    r"yendo de las manos": "se nos está yendo de las manos",
    r"estamos apanados|apanados": "estamos apañados",
    r"aguante su vela": "cada palo que aguante su vela",
    r"poco aprieta": "quien mucho abarca, poco aprieta",
    r"perro flaco": "a perro flaco, todo son pulgas",
    r"el que se pica": "el que se pica, ajos come",
    r"barruntaba el percal": "se barruntaba el percal",
    r"estacazo": "no se veía venir el estacazo",
    r"sobaco de un grillo": "más negro que el sobaco de un grillo",
    r"mascaba el pescao": "se mascaba el pescao",
    r"ni el tato": "ni el tato daba un duro",
    r"solar despues de la guerra": "como un solar después de la guerra",
    r"meterle mano al asunto": "no había por dónde meterle mano",
    r"revenio": "se ha descubierto el pastel y estaba revenío",
    r"vaya repaso": "vaya repaso",       # («zasca» no es coletilla: está prohibida siempre, ver prechequeo.PROHIBIDAS)
    r"no lo has visto venir": "esto no lo has visto venir",
    r"de traca": "de traca",
}
_RE = [(re.compile(k), v) for k, v in CLAVES.items()]


def _norm(s):
    return unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()


def detecta(texto):
    t = _norm(texto)
    return {v for r, v in _RE if r.search(t)}


def _carga():
    try:
        return json.loads(REG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def registra(fecha, *textos):
    col = set().union(*(detecta(t) for t in textos)) if textos else set()
    if not col:
        return set()
    datos = _carga()
    ya = {(d["fecha"], d["coletilla"]) for d in datos}
    for c in col:
        if (fecha, c) not in ya:
            datos.append({"fecha": fecha, "coletilla": c})
    REG.parent.mkdir(parents=True, exist_ok=True)
    REG.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return col


VENTANA = 5   # 17-nov-2026 (usuario): una coletilla usada no se repite hasta pasados varios días (antes 2)
SOLO_VIDEO = set()   # coletillas con límite de 1 por vídeo pero sin ventana de días (ahora ninguna)


def evitar(dias=VENTANA):
    hoy = date.today()
    limite = hoy - timedelta(days=dias)
    out = set()
    for d in _carga():
        try:
            f = date.fromisoformat(d["fecha"])
        except (ValueError, KeyError):
            continue
        if f >= limite and d["coletilla"] not in SOLO_VIDEO:
            out.add(d["coletilla"])
    return sorted(out)


def cuenta(*textos):
    """{coletilla: veces} en el conjunto de textos (para cazar repeticiones DENTRO del mismo vídeo)."""
    from collections import Counter
    n = Counter()
    for t in textos:
        tt = _norm(t)
        for r, v in _RE:
            n[v] += len(r.findall(tt))
    return {k: v for k, v in n.items() if v}


def problemas(*textos, dias=VENTANA, excluir_fecha=None):
    """Coletillas repetidas en el vídeo o ya usadas en los últimos días (sin contar las de `excluir_fecha`, p. ej. hoy
    si ya se registró este mismo vídeo). Devuelve una lista de avisos en llano; vacía si está limpio."""
    usadas = set()
    hoy = date.today()
    for d in _carga():
        try:
            f = date.fromisoformat(d["fecha"])
        except (ValueError, KeyError):
            continue
        if f >= hoy - timedelta(days=dias) and d["fecha"] != excluir_fecha and d["coletilla"] not in SOLO_VIDEO:
            usadas.add(d["coletilla"])
    av = []
    for c, n in cuenta(*textos).items():
        if n > 1:
            av.append(f"«{c}» sale {n} veces en el vídeo (máximo 1)")
        elif c in usadas:
            av.append(f"«{c}» ya se usó en los últimos {dias} días")
    return av


def escribe_evitar(ruta, dias=VENTANA):
    ev = evitar(dias)
    txt = ("COLETILLAS YA USADAS en los últimos días — NO las repitas, elige OTRAS de la paleta (NORMAS.md, §4):\n"
           + ("\n".join(f"- {c}" for c in ev) if ev else "(ninguna; puedes usar cualquiera de la paleta)") + "\n")
    Path(ruta).write_text(txt, encoding="utf-8")
    return ev


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "registra":
        fecha = sys.argv[2]
        dia = RAIZ / "dia" / fecha
        textos = []
        ep = dia / "episodio.json"
        if ep.exists():
            G = json.loads(ep.read_text(encoding="utf-8"))
            textos += [p.get("di", "") for s in G.get("secciones", []) for p in s.get("pasos", [])]
        for sj in (dia / "shorts").glob("short_*.json") if (dia / "shorts").exists() else []:
            try:
                textos.append(json.loads(sj.read_text(encoding="utf-8")).get("voz", ""))
            except (OSError, ValueError):
                pass
        col = registra(fecha, *textos)
        print(f"{fecha}: registradas {len(col)} coletillas: {', '.join(sorted(col)) or '—'}")
    else:
        print("Coletillas a evitar (2 días):")
        print("\n".join("- " + c for c in evitar()) or "(ninguna)")
