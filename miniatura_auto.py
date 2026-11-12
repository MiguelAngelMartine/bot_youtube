"""MINIATURA SIN AGENTE (10-nov-2026: ahorro del plan de Claude y más variedad). Toma el primer titular del sumario
(el gancho del día: frase literal, palabra destacada, etiqueta y protagonista), busca a su rival (otra persona del mismo
bloque) para el cara a cara, prueba dos ESTILOS de miniatura.py que no se hayan usado en los últimos 4 días y el
director de arte (Gemini, director_arte.py) elige la mejor. Registro de estilos: archivo/estilos_miniatura.json.
Uso: python miniatura_auto.py AAAA-MM-DD"""
from __future__ import annotations

import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

import miniatura as M

RAIZ = Path(__file__).parent
REG = RAIZ / "archivo" / "estilos_miniatura.json"


def enc_rival(dia, nombre, cred, img):
    e = json.loads((dia / "encargo.json").read_text(encoding="utf-8")) if (dia / "encargo.json").exists() else {}
    r = (e.get("miniatura") or {}).get("rival") if isinstance(e.get("miniatura"), dict) else None
    return _retrato(cred, r, img) if r else ""         # sin rival salvo que se pida: la persona sola, grande


def _forzar_persona(fecha, nombre, items, G, cred, img):
    """Miniatura con una persona concreta (la pide el director). Usa el titular del sumario donde sale ella; si no sale,
    su frase gancho del día. Devuelve 0 si la hace, None si no tiene foto buena (entonces, temática)."""
    import fotos
    ape = nombre.split()[-1]
    try:                                               # retrato suyo A SOLAS y de calidad (no una foto de grupo)
        for st in (img / f"retrato_{fotos.slug(ape)}.jpg", img / f"retrato_{fotos.slug(ape)}_recorte.png"):
            st.unlink(missing_ok=True)                 # fuera el retrato y el recorte anteriores (podían ser de grupo)
        fotos.mejores(fecha, nombre, "retrato de prensa, primer plano, sola, mirando a cámara", 1, solo=True, ignora_variedad=True)
    except Exception as e:
        print(f"  (no se pudo bajar foto de {nombre}: {type(e).__name__})")
    cred = json.loads((RAIZ / "dia" / fecha / "creditos.json").read_text(encoding="utf-8")) if (RAIZ / "dia" / fecha / "creditos.json").exists() else cred
    solo = f"retrato_{fotos.slug(ape)}.jpg"
    fa = solo if (img / solo).exists() else _retrato(cred, nombre, img)
    if not fa:
        return None
    it = next((x for x in items if x.get("persona") == nombre or ape in (x.get("titular", "") + x.get("texto", ""))), None)
    titular = (it.get("titular") or it.get("texto") if it else "") or f"{ape}, a la carga"
    fondo = next((f for f in (sorted((RAIZ / "dia" / fecha / "vinetas").glob("s*_*.jpg")) or []) ), None)
    M.miniatura_titular(fecha, titular, it.get("destaca", "") if it else "",   # composición de referencia del director (14-nov)
                        ("../vinetas/" + fondo.name) if fondo else "", "miniatura.png", fa)
    print(f"miniatura (titular): {nombre} · «{titular}»")
    return 0


def _retrato(cred, nombre, img):
    fs = [f for f, c in cred.items() if c.get("persona") == nombre and (img / f).exists() and "_recorte" not in f]
    return sorted(fs, key=lambda f: -float(cred[f].get("puntos_gemini", 0) or 0))[0] if fs else ""


def main(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    img = dia / "imagenes"
    items = next((p["ve"]["items"] for p in G["secciones"][0]["pasos"] if (p.get("ve") or {}).get("tipo") == "sumario"), [])
    enc = json.loads((dia / "encargo.json").read_text(encoding="utf-8")) if (dia / "encargo.json").exists() else {}
    forced = (enc.get("miniatura") or {}).get("persona") if isinstance(enc.get("miniatura"), dict) else enc.get("miniatura_persona")
    forzada = forced or next((it.get("persona") for it in items if it.get("persona")), None)   # 13-nov: por defecto, el protagonista
    if forzada:                                        # miniatura con foto REAL de la persona (mejor que FLUX)
        rc = _forzar_persona(fecha, forzada, items, G, cred, img)
        if rc is not None:
            return rc
        print(f"  (no hay foto buena de {forzada}: miniatura temática)")
    it = next((x for x in items if x.get("persona") and _retrato(cred, x["persona"], img)), items[0] if items else {})
    import apto_anuncios as AA                         # 10-nov: la miniatura, sin tacos ni insultos personales
    if not AA.limpio(it.get("titular") or it.get("texto") or ""):
        it = next((x for x in items if AA.limpio(x.get("titular") or x.get("texto") or "")), it)
    titular = (it.get("titular") or it.get("texto") or G.get("titulo_video", "")).strip()
    persona = it.get("persona", "")
    rival = ""
    sec = G["secciones"][it["seccion"]] if isinstance(it.get("seccion"), int) and it["seccion"] < len(G["secciones"]) else None
    if sec:                                            # el aludido: otra persona con foto en el mismo bloque
        import corto as C
        otros = [n for p in sec["pasos"] if p.get("ve") for n in C.personas_de(p["ve"]) if n != persona]
        rival = next((n for n in otros if _retrato(cred, n, img)), "")
    fondo = ""                                         # de fondo, una viñeta o foto del bloque (nunca azul vacío)
    if isinstance(it.get("seccion"), int):
        cand = sorted((dia / "vinetas").glob(f"s{it['seccion']}_*.jpg")) or sorted((dia / "vinetas").glob("s*_*.jpg"))
        cand += [img / f for f in cred if f.startswith(f"s{it['seccion']}_") and (img / f).exists()]
        if cand:
            fondo = "../" + str(cand[0].relative_to(dia)) if "vinetas" in str(cand[0]) else cand[0].name
    hechas = []
    vin = sorted((dia / "vinetas").glob(f"s{it.get('seccion', 1)}_*.jpg")) or sorted((dia / "vinetas").glob("s*_*.jpg"))
    fot = [f for f, c in cred.items() if f.startswith("s") and not c.get("persona") and (img / f).exists()]
    fondos = [("../vinetas/" + v.name) for v in vin[:2]] + fot[:2]
    try:                                               # 11-nov: fondos fotográficos generados (Gemini o FLUX), sin personas reales
        import gem
        import imagen_fondo as IF
        sec_txt = " ".join(p.get("di", "") for p in sec["pasos"])[:1500] if sec else ""
        r = gem.pide(f"Para la miniatura de YouTube de esta noticia de política española, describe EN INGLÉS UNA escena "
                     f"fotográfica simbólica que la represente SIN personas reales reconocibles (manos, siluetas, gente de "
                     f"espaldas, objetos, lugares) y sin texto. Titular: «{titular}». Noticia: {sec_txt}\n"
                     f"Responde SOLO JSON: {{\"escena\": \"...\"}}", como_json=True) or {}
        esc = r.get("escena") if isinstance(r, dict) else None
        if esc:                                        # 12-nov: un solo fondo (calidad media); el lado rojo lo tiñe el código
            dest = img / "miniatura_fondo.jpg"
            motor = IF.genera(esc, dest)
            if motor:
                cred[dest.name] = {"titulo": "Imagen de fondo generada con IA", "autor": f"Imagen generada con IA ({motor})",
                                   "licencia": "generada", "fuente": motor}
                (dia / "creditos.json").write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
                fondos = [dest.name] + fondos
    except Exception as e:
        print(f"  fondos generados: {type(e).__name__}: {e}")
    fondo_t = fondos[0] if fondos else ""              # 14-nov: composición de referencia del director (SIEMPRE la misma)
    try:                                               # versión sin persona (titular gigante sobre el tema)
        M.miniatura_titular(fecha, titular, it.get("destaca", ""), fondo_t, "miniatura_titular.png")
        hechas.append(("titular", "miniatura_titular.png"))
    except Exception as e:
        print(f"  titular: {type(e).__name__}: {e}")
    foto_buena = persona and float(cred.get(_retrato(cred, persona, img), {}).get("puntos_gemini", 0) or 0) >= 8
    if foto_buena:                                     # misma composición con la foto real a la izquierda (si es muy buena)
        try:
            M.miniatura_titular(fecha, titular, it.get("destaca", ""), fondo_t, "miniatura_titular_persona.png",
                                _retrato(cred, persona, img))
            hechas.append(("titular_persona", "miniatura_titular_persona.png"))
        except Exception as e:
            print(f"  titular con persona: {type(e).__name__}: {e}")
    if not hechas:
        return 1
    r = subprocess.run([sys.executable, "director_arte.py", fecha] + [s for _, s in hechas], cwd=RAIZ)
    floja = not (dia / "miniatura.png").exists()        # ninguna llegó al 7 del director de arte
    if floja:
        shutil.copy(dia / hechas[0][1], dia / "miniatura.png")
    elegida = next((e for e, s in hechas if (dia / s).read_bytes() == (dia / "miniatura.png").read_bytes()), hechas[0][0])
    usados = (json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else [])
    REG.write_text(json.dumps((usados + [elegida])[-20:]), encoding="utf-8")
    print(f"miniatura: {elegida} · «{titular}» · {persona}" + (f" vs {rival}" if rival else ""))
    return 3 if floja else 0                            # 3: no llega al nivel; jornada.py llama al diseñador de Claude


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
