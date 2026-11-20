"""PRECHEQUEO mecánico de un bloque antes de la mesa de control (ahorro de tokens sin perder calidad, 3-nov-2026).
Lo que se puede comprobar sin criterio lo comprueba el servidor; así la mesa no gasta vueltas en ello.
Uso: python prechequeo.py AAAA-MM-DD NN      -> imprime los problemas del bloque dia/<fecha>/bloques/NN.json (o «OK»)"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
MEDIOS = ["El País", "elDiario", "Público", "La Vanguardia", "RTVE", "Europa Press", "20minutos", "20 minutos",
          "El Confidencial", "El Mundo", "ABC", "La Razón", "EFE", "Telecinco", "Antena 3", "laSexta", "La Sexta",
          "Cadena SER", "COPE", "Onda Cero", "El Español", "OKdiario", "Vozpópuli", "The Objective"]
SILENCIO = re.compile(r"no consta (su |ninguna )?(respuesta|réplica)|no ha (respondido|contestado|replicado)|sin (respuesta|réplica)|no hubo (respuesta|réplica)", re.I)
PROHIBIDAS = ["zasca"]   # 19-nov-2026 (usuario): «zasca» NO se usa NUNCA. El resto del sarcasmo y las frases hechas son el sello
# del canal y NO se prohíben por estilo; la pluralidad (que la guasa caiga sobre todos) la juzga la mesa, no un filtro de palabras.
CIFRA = re.compile(r"\d")
# 15-nov-2026 (petición del usuario): el tono Vikingo con chascarrillos es OBLIGATORIO en TODOS los vídeos; si un bloque
# tiene menos de 2 coletillas/conectores con gancho, suena a lector de titulares plano y vuelve al redactor.
COLETILLAS = [r"mira", r"\bojo\b", r"f[íi]jate", r"ag[áa]rrate", r"atenci[óo]n", r"resulta que", r"y claro",
              r"va y (dice|suelta|contesta|responde|promete)", r"menudo", r"vaya tela", r"de traca", r"casi nada",
              r"sin medias tintas", r"a todo gas", r"para enmarcar", r"no lo has visto venir", r"y de paso",
              r"y encima", r"\btotal,", r"as[íi] est[áa] la cosa", r"ni corto ni perezoso", r"y mientras",
              r"pero espera", r"se le ha quedado", r"a ver qui[ée]n", r"la que se ha liado", r"como lo o[íi]s",
              r"de las que (se recuerdan|hacen historia)", r"con rima incluida", r"traer tela", r"traen tela",
              r"con sal y pimienta", r"melon[ae]s? de la campa", r"al l[íi]o"]
COLETILLAS_RE = [re.compile(x, re.I) for x in COLETILLAS]


def _n(t):
    import unicodedata
    t = unicodedata.normalize("NFKC", t or "").lower()
    t = re.sub(r"[«»“”\"'‘’]", " ", t)
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", t)).strip()


_FUENTES = {}


def _fuentes(fecha):
    if fecha not in _FUENTES:
        dia = RAIZ / "dia" / fecha
        fs = [*sorted((dia / "articulos").glob("*.txt")), dia / "redes.md", dia / "noticias.json"]
        _FUENTES[fecha] = _n(" ".join(f.read_text(encoding="utf-8", errors="ignore") for f in fs if f.exists()))
    return _FUENTES[fecha]


def chequea(fecha, nn):
    b = json.loads((RAIZ / "dia" / fecha / "bloques" / f"{nn}.json").read_text(encoding="utf-8"))
    pasos = b.get("pasos") or [p for s in b.get("secciones", []) for p in s.get("pasos", [])]
    voz = " ".join(p.get("di", "") for p in pasos)
    fallos = []
    for m in MEDIOS:                                    # la voz no nombra medios (van en pantalla)
        if re.search(r"\b" + re.escape(m) + r"\b", voz):
            fallos.append(f"la voz nombra un medio: «{m}» (va en pantalla con «según», no en el di)")
    for m in SILENCIO.finditer(voz):
        fallos.append(f"anuncia un silencio: «{m.group(0)}» (si no hay respuesta, solo la cita)")
    try:                                                 # 20-nov-2026: y las de archivo/palabras_vetadas.json (la voz las lee mal)
        vet = [x["palabra"] for x in json.loads((RAIZ / "archivo" / "palabras_vetadas.json").read_text(encoding="utf-8"))]
    except (OSError, ValueError, KeyError, TypeError):
        vet = []
    for w in PROHIBIDAS + vet:
        if w.lower() in voz.lower():
            fallos.append(f"palabra o muletilla prohibida: «{w}»")
    for k, p in enumerate(pasos):
        di = p.get("di", "")
        ve = p.get("ve") or {}      # 12-nov: las cifras en la voz van en DÍGITOS (nuevo estilo); ya no se marcan
        textos = [ve.get("cuando")] + [it.get("cuando") for it in ve.get("items", []) if isinstance(it, dict)]
        resto = " ".join(q.get("di", "") for q in pasos[k:])
        for c in filter(None, textos):
            if c not in resto:
                fallos.append(f"paso {k}: el «cuando» «{c}» no está literal en el di de este paso o los siguientes")
    fuentes = _fuentes(fecha)                           # 20-nov-2026: un rótulo «completó» una cita parcial de Sánchez
    if fuentes:
        citas = re.findall(r"«([^»]+)»", voz)
        for p in pasos:
            ve = p.get("ve") or {}
            citas += [x.get("cita") for x in [ve] + [it for it in ve.get("items", []) if isinstance(it, dict)]
                      if isinstance(x.get("cita"), str)]
        for c in citas:
            c = c.strip().strip("«»\"“”").strip().rstrip(".")
            if len(c.split()) >= 3 and _n(c) not in fuentes:
                fallos.append(f"cita «{c[:70]}» no está LITERAL en las fuentes del día (artículos, redes): cópiala letra a "
                              "letra como la publica el medio, sin completarla ni retocarla, o quítala")
    for m in re.finditer(r"»[,.]?\s+(?:dijo|dice|afirmó|afirma|aseguró|asegura|según|ha dicho|ha afirmado|añadió|sentenció)\b", voz):
        fallos.append(f"atribución DESPUÉS de la cita («{m.group(0)}»): en el formato presentador quién la dice va JUSTO "
                      "antes de la cita (NORMAS.md §4, «Escribir para el presentador»)")
    for frase in re.split(r"(?<=[.?!])\s+", voz):
        if len(frase.split()) > 34:
            fallos.append(f"frase de {len(frase.split())} palabras (máximo 30): «{frase[:60]}…»")
    gracia = sum(1 for r in COLETILLAS_RE if r.search(voz))   # tono Vikingo: coletillas/conectores con gancho
    if gracia < 2:
        fallos.append(f"suena plano: solo {gracia} coletilla(s)/conector(es) con gancho (mínimo 2; tono Vikingo "
                      "obligatorio, no un lector de titulares). Añade chascarrillos repartidos por igual.")
    palabras = len(voz.split())
    print(f"bloque {nn}: {palabras} palabras, ~{palabras / 2.75:.0f} s")
    print("\n".join("- " + f for f in fallos) if fallos else "OK: sin problemas mecánicos")
    return not fallos


if __name__ == "__main__":
    sys.exit(0 if chequea(sys.argv[1], sys.argv[2]) else 1)
