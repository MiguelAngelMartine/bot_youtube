"""AGENTES CON GEMINI (decisión del usuario del 10-nov-2026: que vídeo y Shorts no pasen del 8 % del consumo semanal del
plan de Claude, sin perder calidad). Gemini (gratis; si falla, freellmpool) hace el trabajo de un puesto de la redacción
con LAS MISMAS INSTRUCCIONES que su agente de Claude (.claude/agents/<puesto>.md): donde el agente «lee» un fichero, aquí
va su contenido; donde «escribe» un fichero, Gemini devuelve su contenido y el programa lo guarda. Las comprobaciones
mecánicas (prechequeo.py, citas literales, formato) siguen igual. Si Gemini no responde, el coordinador (jornada.py)
pasa ese puesto al agente de Claude de siempre.

Uso desde Python: ejecuta("redactor", fecha, "bloque 02 ...", [ficheros], salida, "json")"""
from __future__ import annotations

import json
import re
from pathlib import Path

import gem

RAIZ = Path(__file__).parent
COMUNES = [RAIZ / "oficina" / "LIBRO_DE_ESTILO.md", RAIZ / "oficina" / "CONTRATOS.md", RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md", RAIZ / "oficina" / "GUION_ESTILO.md"]


def instrucciones(puesto):
    t = (RAIZ / ".claude" / "agents" / f"{puesto}.md").read_text(encoding="utf-8")
    return re.sub(r"^---.*?---\s*", "", t, flags=re.S)


def _lee(f, tope):
    f = Path(f)
    if not f.exists():
        return None
    t = f.read_text(encoding="utf-8", errors="ignore")
    return t if len(t) <= tope else t[:tope] + "\n[... recortado ...]"


def ejecuta(puesto, fecha, encargo, ficheros, salida=None, formato="json", tope_fichero=40000, pensar="high"):
    """Devuelve el contenido (dict/list si json, texto si md) y, si hay salida, lo guarda. None si no hay respuesta válida."""
    partes = []
    for f in list(ficheros) + COMUNES:
        t = _lee(f, tope_fichero)
        if t is not None:
            partes.append(f"=== {Path(f).relative_to(RAIZ) if Path(f).is_absolute() else f} ===\n{t}")
    salida_txt = (f"Devuelve SOLO el contenido del fichero que te toca escribir ({Path(salida).name}), "
                  + ("en JSON válido y completo, sin texto alrededor." if formato == "json" else "en Markdown, sin texto alrededor.")
                  if salida else "Devuelve SOLO tu respuesta.")
    prompt = (f"Trabajas en la redacción de «El Hoyformativo». Haces el puesto descrito abajo, con sus reglas al pie de la "
              f"letra (rigor, literalidad de las citas, neutralidad, voz para el oído). No tienes herramientas: los ficheros que "
              f"tu puesto debe leer van al final; si alguno no está, trabaja con lo que hay.\n\n"
              f"### INSTRUCCIONES DE TU PUESTO\n{instrucciones(puesto)}\n\n### ENCARGO\nFecha {fecha}. {encargo}\n\n"
              f"### FORMATO DE LA RESPUESTA\n{salida_txt}\n\n### FICHEROS\n" + "\n\n".join(partes))
    r = gem.pide(prompt, como_json=(formato == "json"), temperatura=0.3, pensar=pensar, limite_s=420,
                 modelos=[m for m in gem.MODELOS if "lite" not in m])   # el «lite» no redacta bien
    if r is None or (formato == "json" and not isinstance(r, (dict, list))) or (formato != "json" and not str(r).strip()):
        return None
    if salida:
        Path(salida).parent.mkdir(parents=True, exist_ok=True)
        Path(salida).write_text(json.dumps(r, ensure_ascii=False, indent=1) if formato == "json" else str(r).strip() + "\n",
                                encoding="utf-8")
    return r
