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
SILENCIO = re.compile(r"no consta (su |ninguna )?respuesta|no ha (respondido|contestado)|sin respuesta (del|de la|de los)", re.I)
PROHIBIDAS = ["zasca", "le dio un repaso", "humill", "destroz", "se retrata", "escándalo", "vergonzoso", "histórico",
              "ni más ni menos", "y es que", "ojo,", "atentos"]
CIFRA = re.compile(r"\d")


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
    for w in PROHIBIDAS:
        if w.lower() in voz.lower():
            fallos.append(f"palabra o muletilla prohibida: «{w}»")
    for k, p in enumerate(pasos):
        di = p.get("di", "")
        if CIFRA.search(di):
            fallos.append(f"paso {k}: cifra escrita con números en la voz («{CIFRA.search(di).group(0)}…»): con letras")
        ve = p.get("ve") or {}
        textos = [ve.get("cuando")] + [it.get("cuando") for it in ve.get("items", []) if isinstance(it, dict)]
        resto = " ".join(q.get("di", "") for q in pasos[k:])
        for c in filter(None, textos):
            if c not in resto:
                fallos.append(f"paso {k}: el «cuando» «{c}» no está literal en el di de este paso o los siguientes")
    for frase in re.split(r"(?<=[.?!])\s+", voz):
        if len(frase.split()) > 34:
            fallos.append(f"frase de {len(frase.split())} palabras (máximo 30): «{frase[:60]}…»")
    palabras = len(voz.split())
    print(f"bloque {nn}: {palabras} palabras, ~{palabras / 2.75:.0f} s")
    print("\n".join("- " + f for f in fallos) if fallos else "OK: sin problemas mecánicos")
    return not fallos


if __name__ == "__main__":
    sys.exit(0 if chequea(sys.argv[1], sys.argv[2]) else 1)
