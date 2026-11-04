"""RECOPILADOR con Gemini: agrupa las noticias del día por tema (sustituye al agente; decisión del usuario del
4-nov-2026). Lee la lista compacta, pide a Gemini solo los números de cada tema y temas.py arma temas.json.
Uso: python temas_gemini.py AAAA-MM-DD     (salida 2 si Gemini no responde: entonces, el agente recopilador)"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import gem

RAIZ = Path(__file__).parent

PROMPT = """Eres el recopilador de un informativo diario de política española neutral. Abajo tienes las noticias del
día, una por línea: número | medio | titular | resumen. Agrúpalas por TEMA.
- Solo política española y sus consecuencias: Gobierno, partidos, Parlamento, justicia con dimensión política,
  elecciones y campaña, grandes sucesos con responsabilidad pública, movilizaciones.
- Descarta deportes, loterías, horóscopo, sucesos sin dimensión política, tiempo, ocio y política extranjera que no
  afecte a España.
- Un tema = un asunto concreto («la investigación de Urda» y «la presión sobre Puente» son temas distintos).
- Máximo 15 temas; ordénalos de más a menos medios distintos.
- Cada noticia, como mucho en un tema. Usa SOLO números que existan en la lista.
Responde SOLO con JSON: [{"id": "palabra_corta_sin_tildes", "tema": "título claro", "resumen": "2-3 frases",
"noticias": [números]}]

NOTICIAS:
"""


def main(fecha):
    dia = RAIZ / "dia" / fecha
    subprocess.run([sys.executable, str(RAIZ / "temas.py"), "lista", fecha], check=True)
    lista = (dia / "noticias_lista.txt").read_text(encoding="utf-8")
    res = gem.pide(PROMPT + lista, como_json=True)
    if not isinstance(res, list) or not res:
        print("Gemini no responde: usa el agente recopilador")
        sys.exit(2)
    (dia / "temas_borrador.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    subprocess.run([sys.executable, str(RAIZ / "temas.py"), "arma", fecha], check=True)


if __name__ == "__main__":
    main(sys.argv[1])
