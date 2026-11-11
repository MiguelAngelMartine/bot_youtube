"""DIRECTOR DE ARTE con Gemini (plan gratuito, decisión del usuario del 4-nov-2026): evalúa las versiones de la
miniatura como un experto en miniaturas de YouTube y elige la mejor. Segunda opinión gratuita que además ahorra uso
del plan de Claude (el diseñador ya no tiene que comparar a ojo varias imágenes).

Uso: python director_arte.py AAAA-MM-DD miniatura_a.png miniatura_b.png [...]
  -> dia/<fecha>/revision/miniatura.md con nota, problemas y la elegida; copia la elegida a miniatura.png si su nota
     es de 7 o más y no tiene problemas graves. Sale con código 1 si ninguna llega al mínimo (hay que mejorarlas)."""
from __future__ import annotations

import base64
import io
import json
import shutil
import sys
from pathlib import Path

from PIL import Image

import investiga as I

RAIZ = Path(__file__).parent
CRITERIOS = """Eres director de arte de un canal de YouTube de noticias de política española, neutral y riguroso, y
experto en miniaturas que consiguen clics sin engañar. Te doy varias versiones de la miniatura de un vídeo; cada una
va dos veces: a tamaño completo y reducida a 320 px de ancho (como se ve en el móvil). Evalúa CADA versión de 0 a 10:
- legibilidad en el móvil (a 320 px): ¿se lee el titular de un vistazo?;
- la cara: ¿es grande, nítida y su gesto encaja con la noticia (nada de sonrisas en una mala noticia)?;
- claridad y coherencia: ¿se entiende quién dice o hace qué sin ver el vídeo?, ¿el texto puede leerse al revés?;
- composición: jerarquía clara, nada tapa la cara ni letras clave, sin recortes raros, sin restos de otras personas;
- acabado profesional (no amateur): tipografía, color, contraste, limpieza;
- veracidad y normas: que no prometa nada que el vídeo no cuente, sin morbo ni imágenes de víctimas.
Responde SOLO con JSON con esta forma:
{"versiones": [{"archivo": "...", "nota": 0-10, "legible_movil": true/false, "problemas": ["..."], "mejoras": ["..."]}],
 "elegida": "archivo", "por_que": "una frase"}"""


def _png(im):
    b = io.BytesIO()
    im.convert("RGB").save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def evalua(fecha, archivos):
    dia = RAIZ / "dia" / fecha
    contexto = ""
    if (dia / "episodio.json").exists():
        G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
        sumario = " ".join(p.get("di", "") for p in G["secciones"][0]["pasos"])
        contexto = f"Título del vídeo: {G.get('titulo_video', '')}\nLo que cuenta el vídeo (sumario): {sumario}"
    partes = [{"text": CRITERIOS + "\n\n" + contexto}]
    ref = RAIZ / "canal" / "miniatura_referencia_2.png"  # 11-nov: el estilo y el nivel que quiere el director del canal
    if ref.exists():
        partes += [{"text": "REFERENCIA DEL DIRECTOR DEL CANAL (no es una versión: es el estilo y el nivel que quiere; "
                            "puntúa más alto lo que se le acerque: titular gigante en 3 líneas con franjas de brocha "
                            "amarilla y roja, letra ancha, imagen del tema de fondo, impacto inmediato; una cara pequeña o "
                            "una foto pobre de una persona puntúa bajo):"},
                   {"inline_data": {"mime_type": "image/png", "data": _png(Image.open(ref))}}]
    for a in archivos:
        im = Image.open(dia / a)
        peq = im.resize((320, int(320 * im.height / im.width)), Image.LANCZOS)
        partes += [{"text": f"Versión «{a}», tamaño completo:"}, {"inline_data": {"mime_type": "image/png", "data": _png(im)}},
                   {"text": f"Versión «{a}», a 320 px (móvil):"}, {"inline_data": {"mime_type": "image/png", "data": _png(peq)}}]
    import requests
    k = I._clave()
    for modelo in I.MODELOS:
        for intento in range(3):
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                              headers={"x-goog-api-key": k}, timeout=300,
                              json={"contents": [{"parts": partes}],
                                    "generationConfig": {"temperature": 0.2, "responseMimeType": "application/json"}})
            if r.ok:
                txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
                return json.loads(txt), modelo
            if r.status_code in (429, 500, 503):
                import time
                time.sleep(15 * (intento + 1))
                continue
            break
    return None, None


def main(fecha, archivos):
    dia = RAIZ / "dia" / fecha
    res, modelo = evalua(fecha, archivos)
    if not res:
        print("Gemini no responde: el diseñador elige a ojo, como antes")
        sys.exit(2)
    lineas = [f"# Miniatura: evaluación del director de arte ({modelo})", ""]
    for v in sorted(res["versiones"], key=lambda v: -v["nota"]):
        lineas.append(f"## {v['archivo']}: {v['nota']}/10 · móvil: {'sí' if v.get('legible_movil') else 'NO'}")
        lineas += [f"- Problema: {p}" for p in v.get("problemas", [])] + [f"- Mejora: {m}" for m in v.get("mejoras", [])]
        lineas.append("")
    lineas.append(f"**Elegida: {res['elegida']}.** {res.get('por_que', '')}")
    (dia / "revision").mkdir(exist_ok=True)
    (dia / "revision" / "miniatura.md").write_text("\n".join(lineas) + "\n", encoding="utf-8")
    print("\n".join(lineas))
    mejor = next((v for v in res["versiones"] if v["archivo"] == res["elegida"]), None)
    if mejor and mejor["nota"] >= 7 and mejor.get("legible_movil", True):
        shutil.copyfile(dia / mejor["archivo"], dia / "miniatura.png")
        print(f"-> miniatura.png = {mejor['archivo']}")
    else:
        print("-> ninguna llega a 7 o no se lee en el móvil: aplica las mejoras y vuelve a evaluar")
        sys.exit(1)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
