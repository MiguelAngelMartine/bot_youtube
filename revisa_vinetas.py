"""REVISIÓN DE VIÑETAS con Gemini (decisión del usuario del 4-nov-2026): lo que antes hacía el editor gráfico mirando
la hoja. Para cada viñeta del día: si tiene letras inventadas, banderas o símbolos de partido, personas reconocibles
que no tocan, violencia o víctimas, o no corresponde a su nota, se rehace (hasta 3 intentos) y si no, se descarta.
Para las de personas, compara las candidatas con su foto real y elige la fiel o ninguna.
Uso: python revisa_vinetas.py AAAA-MM-DD          (viñetas del día)
     python revisa_vinetas.py biblioteca          (pendientes de la biblioteca: acepta o rechaza)
Salida 2 si Gemini no responde (entonces revisa el editor gráfico a ojo, como antes)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image

import gem
import ia_vinetas as IA

RAIZ = Path(__file__).parent
CRITERIOS = """Eres el editor gráfico de un informativo de política española. Revisa cada ilustración (estilo novela
gráfica, colores planos, tinta negra) para la nota indicada. Es MALA si tiene alguno de estos problemas:
- letras, palabras, carteles o firmas legibles (el texto lo pone el programa aparte; la IA lo inventa mal);
- banderas de partidos o logotipos de partidos o medios; banderas de países que no correspondan a la nota;
- personas reconocibles o caras en primer plano (salvo que la nota sea de una persona concreta y se indique);
- violencia, sangre, víctimas, heridos, restos o morbo;
- no corresponde a lo que cuenta la nota o a la escena pedida, o tiene deformidades evidentes;
- no sigue el estilo de novela gráfica (fotorrealista, 3D, borroso)."""


def _ok_lote(items):
    """items: [(clave, ruta, nota, escena)] -> {clave: (ok, problemas)} pidiendo varias de una vez."""
    partes = [CRITERIOS + '\nResponde SOLO con JSON: {"<clave>": {"ok": true/false, "problemas": ["..."]}}']
    for clave, ruta, nota, escena in items:
        partes += [f"Clave «{clave}» · nota: «{nota}» · escena pedida: «{escena}»", gem.imagen(Image.open(ruta), 640)]
    r = gem.pide(partes, como_json=True)
    if not isinstance(r, dict):
        return None
    return {k: (bool(v.get("ok")), v.get("problemas", [])) for k, v in r.items()}


def dia_vinetas(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    notas = {c: (it, s) for c, it, s in IA.notas_con_vineta(G)}
    origen = json.loads((dia / "vinetas" / "origen.json").read_text(encoding="utf-8")) if (dia / "vinetas" / "origen.json").exists() else {}
    informe = []
    # 1) personas: elegir la candidata fiel comparando con la foto real
    for clave, (it, s) in notas.items():
        quien = it.get("persona_vineta")
        cands = sorted((dia / "vinetas" / "candidatas").glob(f"{clave}_v*.jpg"))
        if not quien or not cands or (dia / "vinetas" / f"{clave}.jpg").exists():
            continue
        foto = dia / "imagenes" / origen.get(clave, {}).get("foto", "")
        if not foto.is_file():
            continue
        partes = [f"Foto REAL de {quien}:", gem.imagen(Image.open(foto), 640),
                  "Candidatas dibujadas (estilo novela gráfica). ¿Cuál es FIEL a la persona real (misma forma de cara, "
                  "pelo, barba o no, gafas o no, edad) y con gesto sereno, sin letras ni deformidades? Ante la duda, ninguna. "
                  'Responde SOLO con JSON: {"elegida": número o null, "por_que": "..."}']
        for k, cnd in enumerate(cands):
            partes += [f"Candidata {k}:", gem.imagen(Image.open(cnd), 512)]
        r = gem.pide(partes, como_json=True)
        if not isinstance(r, dict):
            return None
        v = r.get("elegida")
        if isinstance(v, int) and 0 <= v < len(cands):
            IA.elegir(fecha, clave, int(cands[v].stem.split("_v")[-1]))
            informe.append(f"- {clave} ({quien}): elegida la candidata {v}. {r.get('por_que', '')}")
        else:
            IA.descartar(fecha, clave)
            informe.append(f"- {clave} ({quien}): ninguna fiel, sin viñeta. {r.get('por_que', '')}")
    # 2) escenas: revisar, rehacer hasta 3 veces, descartar
    for intento in range(1, 4):
        items = [(c, dia / "vinetas" / f"{c}.jpg", it.get("texto") or it.get("titular", ""), it.get("escena", ""))
                 for c, (it, s) in notas.items() if not it.get("persona_vineta") and (dia / "vinetas" / f"{c}.jpg").exists()]
        malas = []
        for i in range(0, len(items), 6):              # de 6 en 6: pocas peticiones (plan gratuito)
            res = _ok_lote(items[i:i + 6])
            if res is None:
                return None
            malas += [(c, res[c][1]) for c, *_ in items[i:i + 6] if c in res and not res[c][0]]
        if not malas:
            break
        for c, problemas in malas:
            if intento < 3:
                IA.rehacer(fecha, c, intento)
                informe.append(f"- {c}: rehecha (intento {intento}): {'; '.join(problemas)}")
            else:
                IA.descartar(fecha, c)
                informe.append(f"- {c}: descartada tras 3 intentos: {'; '.join(problemas)}")
        if intento == 3:
            break
    (dia / "revision").mkdir(exist_ok=True)
    (dia / "revision" / "vinetas.md").write_text("# Revisión de viñetas (Gemini)\n\n" + ("\n".join(informe) or "Todas correctas a la primera.") + "\n",
                                               encoding="utf-8")
    return informe


def biblioteca():
    pend = sorted((IA.BIB / "pendientes").glob("*.jpg"))
    if not pend:
        print("biblioteca: no hay pendientes")
        return []
    cat = {e["id"]: e for e in IA._catalogo()}
    acepta, rechaza = [], []
    for i in range(0, len(pend), 6):
        lote = [(f.stem, f, cat.get(f.stem, {}).get("escena", ""), cat.get(f.stem, {}).get("escena", "")) for f in pend[i:i + 6]]
        res = _ok_lote(lote)
        if res is None:
            return None
        for c, *_ in lote:
            (acepta if res.get(c, (False,))[0] else rechaza).append(c)
    if acepta:
        IA.biblioteca_aceptar(acepta)
    if rechaza:
        IA.biblioteca_rechazar(rechaza)
    return [f"biblioteca: {len(acepta)} aceptadas, {len(rechaza)} rechazadas"]


if __name__ == "__main__":
    res = biblioteca() if sys.argv[1] == "biblioteca" else dia_vinetas(sys.argv[1])
    if res is None:
        print("Gemini no responde: revisa a ojo (editor gráfico)")
        sys.exit(2)
    print("\n".join(res) or "viñetas correctas")
