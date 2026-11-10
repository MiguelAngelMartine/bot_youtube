"""INFORME SEMANAL (10-nov-2026, petición del usuario): cada lunes, las estadísticas de los últimos 7 días
(analitica.py) y 5 conclusiones prácticas de Gemini (qué funcionó, qué no y qué cambiar), por Telegram.
Uso: python informe_semanal.py [días=7]"""
from __future__ import annotations

import sys

import analitica
import gem
import notifica

PROMPT = """Eres analista de un canal de YouTube de política española (Shorts diarios y un vídeo largo de 4-5 min).
Con estas estadísticas, escribe en español, en lenguaje llano y sin tecnicismos, como mucho 12 líneas:
1) los 3 vídeos que mejor funcionaron y POR QUÉ (gancho, duración, % visto, me gusta, comentarios);
2) los 2 que peor y por qué;
3) 3 cambios concretos para la próxima semana (duración, tipo de gancho, preguntas, títulos, horas).
Ten en cuenta que los datos de los 2-3 últimos días aún no están completos (YouTube Analytics tarda).

ESTADÍSTICAS:
{datos}"""


def main(dias=7):
    out = analitica.main(dias)
    datos = out.read_text(encoding="utf-8")
    conclusiones = gem.pide(PROMPT.format(datos=datos[:20000]), temperatura=0.3) or "(Gemini no ha respondido: solo las cifras)"
    tabla = [l for l in datos.splitlines() if l.startswith("| 20")]
    mejores = sorted(tabla, key=lambda l: -int((l.split("|")[4].strip() or "0")))[:5]
    txt = (f"📊 Informe semanal ({dias} días)\n\n{conclusiones}\n\nMás vistos:\n" +
           "\n".join("· " + " · ".join(c.strip() for c in l.split("|")[1:6]) for l in mejores))
    tok, chat = notifica.credenciales()
    notifica.envia(f"https://api.telegram.org/bot{tok}", "sendMessage", data={"chat_id": chat, "text": txt[:4000]}, timeout=60)
    print(txt)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
