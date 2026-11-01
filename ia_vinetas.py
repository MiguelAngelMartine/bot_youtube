"""ILUSTRACIONES DE LAS VINETAS con IA (Cloudflare Workers AI, plan gratuito; decision del usuario del 1-nov-2026).

- Escenas genericas: FLUX.1 schnell con la plantilla de estilo del canal (la de canal/estilo_vineta.jpg).
- Personas con nombre propio: FLUX.2 klein 4B con dos imagenes, su retrato real y la vineta de referencia (solo la tecnica de dibujo)
  con licencia libre (el de creditos.json), para que sea esa persona y no una cara inventada.
Reglas: el texto nunca lo dibuja la IA (lo pone vinetas.py en la franja de narracion); gesto sereno e igual para todos
(nada de caricaturas que ridiculicen ni de escenas que no ocurrieron); nunca victimas.
Las imagenes se guardan en cache/vinetas/: la misma escena no vuelve a gastar cuota.
Las claves estan en el .env del proyecto (CLOUDFLARE_ACCOUNT_ID y CLOUDFLARE_API_TOKEN) y nunca se imprimen."""
from __future__ import annotations

import base64
import hashlib
import io
from pathlib import Path

import requests
from PIL import Image

RAIZ = Path(__file__).parent
CACHE = RAIZ / "cache" / "vinetas"
REFERENCIA = RAIZ / "canal" / "estilo_vineta.jpg"     # vineta modelo del estilo del canal (elegida por el usuario)
ESCENAS = "@cf/black-forest-labs/flux-1-schnell"       # escenas: el estilo que eligio el usuario, rapido y barato
PERSONAS = "@cf/black-forest-labs/flux-2-klein-4b"     # personas: admite su foto real y la referencia de estilo
# sin la palabra "comic": con ella el modelo dibuja bocadillos con letras inventadas
ESTILO = ("wordless graphic novel illustration, flat limited colors, thick black ink outlines, heavy black shadows, "
          "set in Spain, plain surfaces without writing, silent scene: ")
PERSONA = ("Redraw the person from image 0 as a wordless graphic novel illustration, using only the drawing technique of "
           "image 1 (flat limited colors, thick black ink outlines, heavy solid black shadows, simple shapes). Do not copy "
           "anything else from image 1: no train, no objects, no background from it. Keep the likeness of image 0 exactly: "
           "same face shape, same hair, same beard, same age, and do not add glasses, hats or accessories that are not in "
           "image 0. Same pose and framing as image 0, calm serious expression, drawn with respect. {escena}"
           "Plain simple background. No text, no letters, no speech bubbles.")
SOBRIO = ", muted desaturated colors, quiet respectful mood"


def _claves():
    env = {}
    for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines():
        if "=" in l and not l.strip().startswith("#"):
            k, v = l.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")
    return env["CLOUDFLARE_ACCOUNT_ID"], env["CLOUDFLARE_API_TOKEN"]


def _jpg(ruta, lado=500):
    im = Image.open(ruta).convert("RGB")
    im.thumbnail((lado, lado))                       # el modelo de personas pide imagenes de menos de 512x512
    b = io.BytesIO()
    im.save(b, "JPEG", quality=92)
    return b.getvalue()


def ilustra(escena, retrato: Path | None = None, sobrio=False, intento=0):
    """escena: descripcion en ingles de lo que se ve (sin texto). retrato: foto real de la persona, si la hay.
    intento: para pedir otra version de la misma escena. Devuelve RGB o lanza RuntimeError (sin claves)."""
    if retrato:
        modelo = PERSONAS
        prompt = PERSONA.format(escena=(escena.strip().rstrip(".") + ". ") if escena else "") + (SOBRIO if sobrio else "")
        fotos = [_jpg(retrato), _jpg(REFERENCIA)]
    else:
        modelo = ESCENAS
        prompt = ESTILO + escena.strip().rstrip(".") + (SOBRIO if sobrio else "")
        fotos = []
    clave = hashlib.sha1((modelo + prompt + str(intento)).encode() + b"".join(fotos)).hexdigest()[:20]
    f = CACHE / f"{clave}.jpg"
    if f.exists():
        return Image.open(f).convert("RGB")
    acc, tok = _claves()
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{modelo}"
    cab = {"Authorization": f"Bearer {tok}"}
    if fotos:
        campos = {"prompt": (None, prompt), "width": (None, "768"), "height": (None, "448"), "seed": (None, str(intento))}
        for k, b in enumerate(fotos):
            campos[f"input_image_{k}"] = (f"img{k}.jpg", b, "image/jpeg")
        r = requests.post(url, headers=cab, files=campos, timeout=180)
    else:
        r = requests.post(url, headers=cab, json={"prompt": prompt + (" " * intento), "steps": 4}, timeout=180)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"respuesta no valida ({r.status_code})")
    img = (j.get("result") or {}).get("image")
    if not img:
        msg = "; ".join(str(e.get("message")) for e in j.get("errors", []))
        raise RuntimeError((msg or f"sin imagen ({r.status_code})").replace(acc, "<cuenta>").replace(tok, "<token>"))
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(base64.b64decode(img))
    return Image.open(f).convert("RGB")


# ------------------------------------------------------------------ jornada: preparar y elegir las vinetas del dia
# Cada nota con viñeta lleva en episodio.json "escena" (en ingles, lo que se ve) y, si sale alguien con nombre,
# "persona_vineta" (nombre exacto, con retrato libre en creditos.json). Clave de cada viñeta: s<seccion>_<paso>_<item>.
# Escenas: se generan y quedan en dia/<fecha>/vinetas/<clave>.jpg. Personas: 3 versiones en vinetas/candidatas/ y el
# editor grafico acepta una fiel (elegir) o ninguna (la nota sale sin viñeta). El render solo lee vinetas/<clave>.jpg.

def notas_con_vineta(G):
    """[(clave, item, seccion)] de todas las notas que piden viñeta."""
    out = []
    for i, s in enumerate(G["secciones"]):
        for j, p in enumerate(s["pasos"]):
            ve = p.get("ve") or {}
            if ve.get("tipo") in ("claves", "cronologia"):
                out += [(f"s{i}_{j}_{k}", it, s) for k, it in enumerate(ve["items"]) if it.get("escena")]
            elif ve.get("tipo") == "breve" and ve.get("escena"):
                out.append((f"s{i}_{j}_0", ve, s))
    return out


def preparar(dia_txt, versiones=2):
    import json
    import shutil
    import corto as C
    dia = RAIZ / "dia" / dia_txt
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    notas = notas_con_vineta(G)
    fotos = C.fotos_personas({it["persona_vineta"] for _, it, _ in notas if it.get("persona_vineta")}, cred, dia / "imagenes")
    (dia / "vinetas" / "candidatas").mkdir(parents=True, exist_ok=True)
    hoja = []
    for clave, it, sec in notas:
        sobrio = sec.get("tono") == "sobrio"
        destino = dia / "vinetas" / f"{clave}.jpg"
        quien = it.get("persona_vineta")
        try:
            if quien:
                if quien not in fotos:
                    print(f"  {clave}: {quien} no tiene retrato en creditos.json; sin viñeta")
                    continue
                if destino.exists():
                    continue
                for v in range(versiones):
                    try:
                        IA_im = ilustra(it["escena"], fotos[quien], sobrio, intento=v)
                        IA_im.save(dia / "vinetas" / "candidatas" / f"{clave}_v{v}.jpg", quality=92)
                        hoja.append((f"{clave} v{v} · {quien}", IA_im))
                    except RuntimeError as e:
                        print(f"  {clave} v{v}: rechazada ({str(e)[:60]})")
                hoja.append((f"{clave} · FOTO REAL", Image.open(fotos[quien]).convert("RGB")))
                print(f"  {clave}: {quien}, candidatas listas: hay que elegir una fiel")
            else:
                if not destino.exists():
                    ilustra(it["escena"], None, sobrio).save(destino, quality=92)
                hoja.append((clave, Image.open(destino).convert("RGB")))
                print(f"  {clave}: lista")
        except RuntimeError as e:
            print(f"  {clave}: fallo ({str(e)[:80]}); sin viñeta")
    if hoja:
        from PIL import ImageDraw
        from genera_video2 import fuente
        w, h = 420, 270
        sh = Image.new("RGB", (3 * w, ((len(hoja) + 2) // 3) * (h + 30)), (22, 36, 64))
        d = ImageDraw.Draw(sh)
        for k, (et, im) in enumerate(hoja):
            x, y = (k % 3) * w, (k // 3) * (h + 30)
            im = im.copy()
            im.thumbnail((w - 10, h))
            sh.paste(im, (x + 5, y + 28))
            d.text((x + 6, y + 4), et, font=fuente("Inter-Bold.ttf", 18), fill=(241, 191, 0))
        sh.save(dia / "vinetas" / "hoja.png")
    print(f"{len(notas)} notas con viñeta -> {dia / 'vinetas'} (hoja de contacto: vinetas/hoja.png)")


def elegir(dia_txt, clave, version):
    import shutil
    dia = RAIZ / "dia" / dia_txt
    shutil.copyfile(dia / "vinetas" / "candidatas" / f"{clave}_v{version}.jpg", dia / "vinetas" / f"{clave}.jpg")
    print(f"{clave}: aceptada la versión {version}")


def rehacer(dia_txt, clave, intento=1):
    """Otra version de una escena (por ejemplo, si salen letras inventadas o no ilustra bien el dato)."""
    import json
    dia = RAIZ / "dia" / dia_txt
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    for c, it, sec in notas_con_vineta(G):
        if c == clave:
            ilustra(it["escena"], None, sec.get("tono") == "sobrio", intento=intento).save(dia / "vinetas" / f"{clave}.jpg", quality=92)
            print(f"{clave}: rehecha (intento {intento})")
            return
    print(f"{clave}: no existe")


def descartar(dia_txt, clave):
    f = RAIZ / "dia" / dia_txt / "vinetas" / f"{clave}.jpg"
    f.unlink(missing_ok=True)
    print(f"{clave}: sin viñeta (la nota sale con su texto)")


if __name__ == "__main__":
    import sys
    a = sys.argv[1:]
    if a[:1] == ["preparar"]:
        preparar(a[1])
    elif a[:1] == ["elegir"]:
        elegir(a[1], a[2], int(a[3]))
    elif a[:1] == ["rehacer"]:
        rehacer(a[1], a[2], int(a[3]) if len(a) > 3 else 1)
    elif a[:1] == ["descartar"]:
        descartar(a[1], a[2])
    else:
        print("uso: ia_vinetas.py preparar <fecha> | rehacer <fecha> <clave> [intento] | elegir <fecha> <clave> <version> | descartar <fecha> <clave>")
