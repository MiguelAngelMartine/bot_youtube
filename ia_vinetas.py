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


# ------------------------------------------------------------------ biblioteca propia (plan B si Cloudflare falla)
# canal/biblioteca_vinetas/: viñetas genericas en el estilo del canal (lugares y objetos que se repiten; nunca personas),
# generadas poco a poco con la cuota que SOBRA tras la jornada (decision del usuario del 2-nov-2026: primero el video del
# dia, despues la biblioteca, sin pasarse nunca del limite) y revisadas antes de aceptarlas.
BIB = RAIZ / "canal" / "biblioteca_vinetas"
POR_DIA = 15                                         # tope de viñetas de biblioteca por dia
CUOTA_DIA = 10000                                    # neuronas gratis al dia (se renuevan a las 00:00 UTC)
TECHO = 8000                                         # nunca se pasa de aqui contando todo lo del dia (20 % de margen)
NEURONAS_IMAGEN = 330                                # estimacion prudente por imagen (1-nov: 13.950 neuronas, ~45 imagenes)


def gastado_hoy():
    """Neuronas gastadas hoy (dia UTC, como Cloudflare), estimadas por las imagenes nuevas en cache/vinetas/."""
    from datetime import datetime, timezone
    hoy = datetime.now(timezone.utc).date()
    n = sum(1 for f in CACHE.glob("*.jpg") if datetime.fromtimestamp(f.stat().st_mtime, timezone.utc).date() == hoy)
    return n * NEURONAS_IMAGEN, n


def _catalogo():
    import json
    return json.loads((BIB / "catalogo.json").read_text(encoding="utf-8"))


def _guarda_catalogo(cat):
    import json
    (BIB / "catalogo.json").write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")


def jornada_en_marcha():
    """jornada.sh bloquea .jornada.lock (flock) mientras trabaja; el fichero queda aunque no este en marcha."""
    import fcntl
    f = RAIZ / ".jornada.lock"
    if not f.exists():
        return False
    with open(f) as fh:
        try:
            fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
            fcntl.flock(fh, fcntl.LOCK_UN)
            return False
        except OSError:
            return True


def biblioteca_generar(maximo=POR_DIA):
    """Genera las que faltan (ni aceptadas ni pendientes de revisar) en biblioteca_vinetas/pendientes/, solo con la
    cuota que sobra hoy por debajo del TECHO, y nunca mientras la jornada esta en marcha. Para al primer aviso de cuota."""
    if jornada_en_marcha():
        print("la jornada esta en marcha: la biblioteca espera a otro dia")
        return
    gastado, n = gastado_hoy()
    maximo = min(maximo, max(0, (TECHO - gastado) // NEURONAS_IMAGEN))
    print(f"hoy (UTC): {n} imagenes, ~{gastado} neuronas de {CUOTA_DIA}; margen para la biblioteca: {maximo} viñetas")
    pend = BIB / "pendientes"
    pend.mkdir(parents=True, exist_ok=True)
    hechas = 0
    for e in _catalogo():
        if hechas >= maximo:
            break
        if (BIB / f"{e['id']}.jpg").exists() or (pend / f"{e['id']}.jpg").exists() or e.get("descartada"):
            continue
        try:
            ilustra(e["escena"], None, e["tono"] == "sobrio", intento=e.get("intento", 0)).save(pend / f"{e['id']}.jpg", quality=92)
            hechas += 1
            print(f"  {e['id']}: generada")
        except RuntimeError as err:
            print(f"  parada: {str(err)[:100]}")
            break
    _hoja_pendientes()
    total = len(_catalogo())
    print(f"{hechas} nuevas; biblioteca: {len(list(BIB.glob('*.jpg')))}/{total} aceptadas, "
          f"{len(list(pend.glob('*.jpg')))} pendientes de revisar (hoja: {pend / 'hoja.png'})")


def _hoja_pendientes():
    from PIL import ImageDraw
    from genera_video2 import fuente
    pend = sorted((BIB / "pendientes").glob("*.jpg"))
    if not pend:
        (BIB / "pendientes" / "hoja.png").unlink(missing_ok=True)
        return
    w, h = 420, 270
    sh = Image.new("RGB", (3 * w, ((len(pend) + 2) // 3) * (h + 30)), (22, 36, 64))
    d = ImageDraw.Draw(sh)
    for k, f in enumerate(pend):
        x, y = (k % 3) * w, (k // 3) * (h + 30)
        im = Image.open(f).convert("RGB")
        im.thumbnail((w - 10, h))
        sh.paste(im, (x + 5, y + 28))
        d.text((x + 6, y + 4), f.stem, font=fuente("Inter-Bold.ttf", 18), fill=(241, 191, 0))
    sh.save(BIB / "pendientes" / "hoja.png")


def biblioteca_aceptar(ids):
    for i in ids:
        (BIB / "pendientes" / f"{i}.jpg").replace(BIB / f"{i}.jpg")
        print(f"  {i}: aceptada")
    _hoja_pendientes()


def biblioteca_rechazar(ids, descartar=False):
    """Rechazada: se borra y la proxima noche se pide otra version. Tras 3 rechazos (o con descartar) se retira."""
    cat = _catalogo()
    for e in cat:
        if e["id"] in ids:
            (BIB / "pendientes" / f"{e['id']}.jpg").unlink(missing_ok=True)
            e["intento"] = e.get("intento", 0) + 1
            if descartar or e["intento"] >= 3:
                e["descartada"] = True
            print(f"  {e['id']}: rechazada" + (" y retirada" if e.get("descartada") else f" (intento {e['intento']})"))
    _guarda_catalogo(cat)
    _hoja_pendientes()


VACIAS = set("""a an the of in on at by with and or to from into over under through beside behind near its their his her
some one two three many few no without there this that is are being seen far away wide view side quiet soft light empty calm
small large big tall single closed open plain simple morning evening night daylight dusk dawn dark grey gray wooden table
room people person scene setting background day time very long rows row full madrid spain spanish
central city""".split())


def _palabras(texto):
    import re
    out = set()
    for w in re.findall(r"[a-z]+", (texto or "").lower()):
        if w in VACIAS or len(w) < 3:
            continue
        if w.endswith("ing") and len(w) > 6:
            w = w[:-3]                                              # marching -> march
        out.add(w[:-1] if w.endswith("s") and len(w) > 4 else w)    # documents -> document
    return out


def de_biblioteca(escena, sobrio, usadas=()):
    """La viñeta aceptada de la biblioteca que mejor encaja con la escena pedida (palabras en comun con su descripcion y
    sus claves), del tono adecuado y sin repetir en el mismo video. None si ninguna comparte nada."""
    if not (BIB / "catalogo.json").exists():
        return None
    pal = _palabras(escena)
    mejor, puntos = None, 0
    for e in _catalogo():
        f = BIB / f"{e['id']}.jpg"
        if not f.exists() or e["id"] in usadas or e["tono"] == ("normal" if sobrio else "sobrio"):
            continue
        p = 2 * len(pal & _palabras(e["claves"])) + len(pal & _palabras(e["escena"]))
        if p > puntos:
            mejor, puntos = e, p
    return (mejor["id"], BIB / f"{mejor['id']}.jpg") if mejor and puntos >= 2 else None


def licencia_dibujable(lic):
    """Fotos que se pueden usar para dibujar a una persona sin heredar obligaciones: CC0, dominio publico o CC BY.
    Nunca CC BY-SA (la viñeta seria obra derivada y tendria que llevar esa licencia, y con ella el video), NC ni ND."""
    l = (lic or "").upper().replace("-", " ")
    if any(x in l.split() for x in ("SA", "NC", "ND")):
        return False
    return l.startswith(("CC0", "PDM", "PUBLIC DOMAIN", "DOMINIO", "CC BY"))


def guarda_origen(dia, clave, datos):
    import json
    f = dia / "vinetas" / "origen.json"
    o = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    o[clave] = datos
    f.write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")


def credito_vineta(origen, clave):
    """Texto pequeño sobre la viñeta: siempre «Ilustración IA»; si dibuja a una persona, de qué foto sale."""
    d = (origen or {}).get(clave) or {}
    if d.get("persona"):
        return f"Ilustración IA a partir de foto de {d['autor'][:40]} ({d['licencia']})"
    return "Ilustración IA"


def preparar(dia_txt, versiones=2):
    import json
    import shutil
    import corto as C
    dia = RAIZ / "dia" / dia_txt
    if (dia / "SIN_VINETAS").exists():               # decision del director para ese dia: notas con su texto
        print(f"{dia_txt}: hoy sin viñetas por decisión del director (dia/{dia_txt}/SIN_VINETAS); las notas salen con texto")
        return
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    notas = notas_con_vineta(G)
    fotos = C.fotos_personas({it["persona_vineta"] for _, it, _ in notas if it.get("persona_vineta")}, cred, dia / "imagenes")
    (dia / "vinetas" / "candidatas").mkdir(parents=True, exist_ok=True)
    hoja = []
    usadas_bib = set()
    for clave, it, sec in notas:
        sobrio = sec.get("tono") == "sobrio"
        destino = dia / "vinetas" / f"{clave}.jpg"
        quien = it.get("persona_vineta")
        try:
            if quien:
                if quien not in fotos:
                    print(f"  {clave}: {quien} no tiene retrato en creditos.json; sin viñeta")
                    continue
                cr = cred.get(fotos[quien].name, {})
                if not licencia_dibujable(cr.get("licencia")):
                    print(f"  {clave}: el retrato de {quien} es {cr.get('licencia') or 'sin licencia'}; para dibujarla "
                          f"solo valen CC0, dominio público o CC BY: sin viñeta (la nota sale con su texto)")
                    continue
                guarda_origen(dia, clave, {"persona": quien, "foto": fotos[quien].name, "autor": cr.get("autor", ""),
                                           "licencia": cr.get("licencia", ""), "pagina": cr.get("pagina", "")})
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
                    try:
                        ilustra(it["escena"], None, sobrio).save(destino, quality=92)
                    except RuntimeError as e:
                        b = de_biblioteca(it["escena"], sobrio, usadas_bib)
                        if not b:
                            raise
                        im = Image.open(b[1]).convert("RGB")
                        if sobrio:                       # en los bloques sobrios, apagada como las demas
                            from PIL import ImageEnhance
                            im = ImageEnhance.Color(im).enhance(0.35)
                        im.save(destino, quality=92)
                        usadas_bib.add(b[0])
                        guarda_origen(dia, clave, {"biblioteca": b[0]})
                        print(f"  {clave}: Cloudflare falla ({str(e)[:50]}); de la biblioteca: {b[0]}")
                hoja.append((clave, Image.open(destino).convert("RGB")))
                print(f"  {clave}: lista")
        except RuntimeError as e:
            print(f"  {clave}: fallo ({str(e)[:80]}); sin viñeta (la biblioteca no tiene una que encaje)")
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
            o = dia / "vinetas" / "origen.json"          # rehecha sin retrato: ya no sale de ninguna foto
            if o.exists():
                d = json.loads(o.read_text(encoding="utf-8"))
                if d.pop(clave, None):
                    o.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
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
    elif a[:2] == ["biblioteca", "generar"]:
        biblioteca_generar(int(a[2]) if len(a) > 2 else POR_DIA)
    elif a[:2] == ["biblioteca", "aceptar"]:
        biblioteca_aceptar(a[2:])
    elif a[:2] == ["biblioteca", "rechazar"]:
        biblioteca_rechazar(a[2:])
    elif a[:2] == ["biblioteca", "retirar"]:
        biblioteca_rechazar(a[2:], descartar=True)
    else:
        print("uso: ia_vinetas.py preparar <fecha> | rehacer <fecha> <clave> [intento] | elegir <fecha> <clave> <version> | "
              "descartar <fecha> <clave> | biblioteca generar [n] | biblioteca aceptar|rechazar|retirar <id>...")
