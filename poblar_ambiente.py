"""POBLAR LA BIBLIOTECA DE AMBIENTE (16-nov-2026, petición del usuario: «no hay variedad de fondos»).
Genera escenas de ambiente VARIADAS (línea clara a color pleno, sin personas en primer plano) con FLUX/HF y las guarda en
la biblioteca, para que el respaldo tenga mucha variedad cuando FLUX no tiene cuota. Pensado para un cron nocturno, cuando
la cuota de FLUX ya ha renovado. Solo añade lo que no esté ya (por hash).
Uso:  python poblar_ambiente.py [n=12]
"""
from __future__ import annotations

import random
import sys
import tempfile
from pathlib import Path

import biblioteca_ambiente as BA
import ia_vinetas as IA

RAIZ = Path(__file__).parent

LUGARES = [
    "a quiet narrow street in {c} with tiled facades and balconies at midday",
    "a grand plaza in {c} with a fountain and café terraces",
    "the facade of the town hall of {c} with the Spanish flag",
    "a market hall interior in {c} with iron columns and empty stalls",
    "a tree-lined avenue in {c} with street lamps and benches",
    "a riverside promenade in {c} at golden dusk",
    "a train station concourse in {c} with a high glass roof and blank boards",
    "a cathedral square in {c} with cobblestones",
    "a modern business district in {c} with glass towers",
    "a seaside boulevard in {c} with palm trees",
    "a university courtyard in {c} with arcades",
    "a theatre facade in {c} lit up at night",
]
CIUDADES = ["Madrid", "Barcelona", "Seville", "Valencia", "Bilbao", "Zaragoza", "Málaga", "Santiago de Compostela",
            "Granada", "Toledo", "San Sebastián", "Córdoba", "Salamanca", "Oviedo", "Pamplona"]
INTERIORES = [
    "a solemn courtroom interior with wooden benches and a Spanish coat of arms",
    "an empty television news studio with cameras, tripods and bright lights",
    "a grand library reading room with tall wooden shelves and warm light",
    "an ornate ministerial office with a large desk and a Spanish flag",
    "a parliamentary committee room with rows of seats and microphones",
    "a radio studio with a table, microphones and soundproof panels",
    "a hospital corridor, clean and bright, with empty gurneys",
    "a university lecture hall with tiered empty seats",
]


def descripciones(n):
    out = []
    for _ in range(n):
        if random.random() < 0.65:
            out.append(random.choice(LUGARES).format(c=random.choice(CIUDADES)))
        else:
            out.append(random.choice(INTERIORES))
    return list(dict.fromkeys(out))


def main(n=12):
    tmp = Path(tempfile.mkdtemp())
    ok = 0
    for i, esc in enumerate(descripciones(n)):
        try:
            img = IA.ilustra(esc, None, False, intento=i + 50, ambiente=True)
            ruta = tmp / f"e{i}.jpg"
            img.save(ruta, quality=92)
            if BA.guarda(ruta, esc):
                ok += 1
                print(f"[{ok}] {esc[:56]}", flush=True)
        except Exception as e:
            print(f"  (falla «{esc[:40]}»: {type(e).__name__})", flush=True)
    tot = len(list((RAIZ / "canal" / "biblioteca_ambiente" / "simples").glob("*.jpg")))
    print(f"Añadidas {ok}. Biblioteca de ambiente: {tot} escenas.")
    return ok


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 12)
