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
REFERENCIA = RAIZ / "canal" / "estilo_lineaclara.jpg"   # 10-nov: línea clara     # vineta modelo del estilo del canal (elegida por el usuario)
ESCENAS = "@cf/black-forest-labs/flux-1-schnell"       # escenas: el estilo que eligio el usuario, rapido y barato
PERSONAS = "@cf/black-forest-labs/flux-2-klein-4b"     # personas: admite su foto real y la referencia de estilo
# sin la palabra "comic": con ella el modelo dibuja bocadillos con letras inventadas
# 10-nov-2026 (elegido por el usuario entre cuatro opciones): LÍNEA CLARA europea con rasgos españoles en escenas y
# personajes (balcones de forja, persianas, plazas, terrazas, gente mediterránea). Referencia: canal/estilo_lineaclara.jpg
ESTILO = ("wordless European ligne claire comic illustration, clean uniform thin black outlines, flat clean colors without "
          "gradients, richly detailed scene with depth, set in Spain with typical Spanish architecture (wrought-iron balconies, "
          "shutters, plazas, bar terraces) and ordinary Spanish people with Mediterranean features, "
          "plain surfaces without writing, every box, screen, paper and sign blank and unlabeled, silent scene: ")
PERSONA = ("Redraw the person from image 0 as a wordless European ligne claire comic illustration, using only the drawing "
           "technique of image 1 (clean uniform thin black outlines, flat clean colors without gradients). Do not copy anything "
           "else from image 1: no people, no buildings, no background from it. Keep the likeness of image 0 exactly: same face "
           "shape, same hair, same beard, same age, and do not add glasses, hats or accessories that are not in image 0. Same "
           "pose and framing as image 0, calm serious expression, drawn with respect. {escena}"
           "Plain simple background. No text, no letters, no speech bubbles.")
SOBRIO = ", muted desaturated colors, quiet respectful mood"
# 13-nov-2026 (el usuario: «escenas relacionadas con lo que se narra pero SIN personajes en primer plano»): plano general
# del lugar o del objeto, sin figuras cercanas; como mucho, siluetas lejanas y pequeñas de fondo.
ESTILO_AMBIENTE = ("wordless European ligne claire comic illustration, clean uniform thin black outlines, flat clean colors "
                   "without gradients, a richly detailed ESTABLISHING WIDE SHOT of a place or object, set in Spain with typical "
                   "Spanish architecture (wrought-iron balconies, shutters, plazas, bar terraces), sense of depth and distance. "
                   "NO people in the foreground, no characters close to the camera, no faces; at most a few tiny distant "
                   "silhouettes in the far background. Empty quiet scene, plain surfaces without writing, every box, screen, "
                   "paper and sign blank and unlabeled, silent scene: ")


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


def ilustra(escena, retrato: Path | None = None, sobrio=False, intento=0, ambiente=False):
    """escena: descripcion en ingles de lo que se ve (sin texto). retrato: foto real de la persona, si la hay.
    ambiente=True: plano general del lugar/objeto, SIN personajes en primer plano (13-nov-2026).
    intento: para pedir otra version de la misma escena. Devuelve RGB o lanza RuntimeError (sin claves)."""
    if retrato and not ambiente:
        modelo = PERSONAS
        prompt = PERSONA.format(escena=(escena.strip().rstrip(".") + ". ") if escena else "") + (SOBRIO if sobrio else "")
        fotos = [_jpg(retrato), _jpg(REFERENCIA)]
    else:
        modelo = ESCENAS
        prompt = (ESTILO_AMBIENTE if ambiente else ESTILO) + escena.strip().rstrip(".") + (SOBRIO if sobrio else "")
        fotos = []
    import variedad                                     # 8-nov: una viñeta no se repite en 7 días: otra versión
    for _ in range(6):
        clave = hashlib.sha1((modelo + prompt + str(intento)).encode() + b"".join(fotos)).hexdigest()[:20]
        f = CACHE / f"{clave}.jpg"
        if f.exists() and variedad.reciente(variedad.clave_vineta(f)):
            intento += 7
            continue
        break
    if f.exists():
        return Image.open(f).convert("RGB")
    try:
        acc, tok = _claves()
    except KeyError:
        acc = tok = None
    if acc is None or (not fotos and (RAIZ / "cache" / f"cloudflare_agotado_{_hoy_utc()}").exists()):
        if not fotos:                                    # sin Cloudflare hoy: la escena, al Space gratuito
            return _escena_hf(prompt, intento, f)
        raise RuntimeError("sin claves de Cloudflare")
    url = f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{modelo}"
    cab = {"Authorization": f"Bearer {tok}"}
    if fotos:
        campos = {"prompt": (None, prompt), "width": (None, "768"), "height": (None, "448"), "seed": (None, str(intento))}
        for k, b in enumerate(fotos):
            campos[f"input_image_{k}"] = (f"img{k}.jpg", b, "image/jpeg")
        r = requests.post(url, headers=cab, files=campos, timeout=180)
    else:
        r = requests.post(url, headers=cab, json={"prompt": prompt + (" " * intento), "steps": 8}, timeout=180)
    try:
        j = r.json()
    except ValueError:
        raise RuntimeError(f"respuesta no valida ({r.status_code})")
    img = (j.get("result") or {}).get("image")
    if not img and not fotos:                            # cuota de Cloudflare agotada o fallo: el Space gratuito
        msg = "; ".join(str(e.get("message")) for e in j.get("errors", []))
        if r.status_code == 429 or "neuron" in msg.lower() or "limit" in msg.lower():
            (RAIZ / "cache").mkdir(exist_ok=True)
            (RAIZ / "cache" / f"cloudflare_agotado_{_hoy_utc()}").touch()
        try:
            return _escena_hf(prompt, intento, f)
        except Exception as e:
            raise RuntimeError(f"Cloudflare: {msg or r.status_code}; Hugging Face: {type(e).__name__}") from None
    if not img:
        msg = "; ".join(str(e.get("message")) for e in j.get("errors", []))
        raise RuntimeError((msg or f"sin imagen ({r.status_code})").replace(acc, "<cuenta>").replace(tok, "<token>"))
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(base64.b64decode(img))
    return Image.open(f).convert("RGB")


CARICATURA = ("Redraw the person from image 0 as a polished editorial caricature for a political magazine cover: glossy "
              "semi-realistic 3D cartoon style, slightly bigger head, vivid colors, soft studio light. Keep the likeness of "
              "image 0 exactly: same face shape, same hair, same age, no glasses or accessories that are not in image 0. "
              "Chest-up portrait, body turned to the {lado}, looking to the {lado}, {gesto}. Respectful, not grotesque. "
              "Plain flat light grey background. No text, no letters.")


def caricatura(retrato: Path, lado="right", gesto="serious determined expression", intento=0):
    """Caricatura (no fotorrealista) de una persona real para la miniatura (decision del usuario del 7-nov-2026), dibujada
    desde su foto libre (CC0, dominio publico o CC BY) con FLUX.2 klein de Cloudflare. Devuelve RGB o lanza RuntimeError."""
    prompt = CARICATURA.format(lado=lado, gesto=gesto)
    foto = _jpg(retrato)
    clave = hashlib.sha1((PERSONAS + prompt + str(intento)).encode() + foto).hexdigest()[:20]
    f = CACHE / f"car_{clave}.jpg"
    if f.exists():
        return Image.open(f).convert("RGB")
    acc, tok = _claves()
    r = requests.post(f"https://api.cloudflare.com/client/v4/accounts/{acc}/ai/run/{PERSONAS}",
                      headers={"Authorization": f"Bearer {tok}"}, timeout=180,
                      files={"prompt": (None, prompt), "width": (None, "768"), "height": (None, "896"),
                             "seed": (None, str(intento)), "input_image_0": ("img0.jpg", foto, "image/jpeg")})
    try:
        img = (r.json().get("result") or {}).get("image")
    except ValueError:
        img = None
    if not img:
        raise RuntimeError(f"Cloudflare sin caricatura ({r.status_code})")
    CACHE.mkdir(parents=True, exist_ok=True)
    f.write_bytes(base64.b64decode(img))
    return Image.open(f).convert("RGB")


def _hoy_utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


HF_SPACE = "black-forest-labs/FLUX.1-schnell"           # el mismo modelo de las escenas (licencia Apache 2.0: comercial)


def _escena_hf(prompt, intento, destino):
    """Plan B gratuito (7-nov-2026): el Space público de FLUX.1-schnell en Hugging Face, con la cuota diaria de GPU
    gratuita de la cuenta del canal (HF_TOKEN en .env). Solo escenas, nunca personas (no admite foto de referencia)."""
    import shutil
    from gradio_client import Client
    env = dict(l.split("=", 1) for l in (RAIZ / ".env").read_text(encoding="utf-8").splitlines()
               if "=" in l and not l.strip().startswith("#"))
    c = Client(HF_SPACE, token=env["HF_TOKEN"].strip().strip('"'), verbose=False)
    r = c.predict(prompt=prompt, seed=intento, randomize_seed=False, width=1344, height=768, num_inference_steps=6,
                  api_name="/infer")
    CACHE.mkdir(parents=True, exist_ok=True)
    Image.open(r[0]).convert("RGB").save(destino, quality=93)
    print(f"  (viñeta hecha en Hugging Face: {destino.name})")
    return Image.open(destino).convert("RGB")


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
        import variedad
        if variedad.reciente("bib:" + e["id"]):           # 8-nov: tampoco las de la biblioteca en 7 días
            continue
        p = 2 * len(pal & _palabras(e["claves"])) + len(pal & _palabras(e["escena"]))
        if p > puntos:
            mejor, puntos = e, p
    return (mejor["id"], BIB / f"{mejor['id']}.jpg") if mejor and puntos >= 2 else None


AMBITOS = [  # (palabras del cargo, escena sin personas) -- 4-nov-2026: en vez de las iniciales cuando no hay foto libre
    (("juez", "jueza", "magistrad", "fiscal", "tribunal"), "an empty courtroom bench with a wooden gavel and scales of justice"),
    (("alcalde", "alcaldesa", "ayuntamiento", "concejal"), "the facade of a Spanish town hall with a balcony and a clock"),
    (("sindicato", "sindical", "ugt", "ccoo", "semaf"), "a union assembly hall with empty chairs and raised blank placards"),
    (("ministr", "vicepresident", "gobierno de españa", "presidente del gobierno"),
     "a long cabinet meeting table with empty leather chairs and folders"),
    (("senador", "senado"), "an empty red seat in a classical senate chamber"),
    (("diputad", "congreso", "grupo parlamentario", "parlamentari"), "an empty leather seat in a semicircular parliament chamber"),
    (("candidat", "campaña", "cabeza de lista"), "an empty rally stage with a lectern under spotlights"),
    (("president", "consejer", "junta", "generalitat", "xunta", "gobierno de"), "the stately facade of a regional government palace"),
    (("portavoz", "secretari", "líder", "lider", "coordinador"), "an empty press conference lectern with several microphones"),
]
AMBITO_DEFECTO = "an empty press conference lectern with several microphones"


def ilustracion_ambito(cargo, sobrio=False):
    """Ruta de una ilustracion del ambito de una persona sin foto libre (por su cargo), SIN personas: de la biblioteca
    si encaja y, si no, generada una vez y guardada. None si no se puede (entonces, las iniciales)."""
    c = (cargo or "").lower()
    escena = next((e for claves, e in AMBITOS if any(k in c for k in claves)), AMBITO_DEFECTO)
    b = de_biblioteca(escena, sobrio)
    if b:
        return b[1]
    destino = CACHE / f"ambito_{hashlib.sha1((escena + str(sobrio)).encode()).hexdigest()[:12]}.jpg"
    if not destino.exists():
        try:
            ilustra(escena + ", no people", None, sobrio).save(destino, quality=92)
        except Exception:
            return None
    return destino


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
        # 13-nov-2026 (el usuario: «el vídeo largo tiene que llevar el estilo de viñeta animada estándar»): si la persona
        # no tiene retrato libre y dibujable, NO se deja la escena sin viñeta (caía a foto borrosa, «parece un PowerPoint»):
        # se dibuja una viñeta de ESCENA de línea clara (sin inventar su cara, como en los Shorts), con «Ilustración IA».
        if quien and quien not in fotos:
            print(f"  {clave}: {quien} sin retrato libre: viñeta de escena de línea clara (sin su cara, no se inventa)")
            quien = None
        elif quien and not licencia_dibujable(cred.get(fotos[quien].name, {}).get("licencia")):
            print(f"  {clave}: retrato de {quien} es {cred.get(fotos[quien].name, {}).get('licencia') or 'sin licencia'} "
                  f"(solo CC0/PD/CC BY): viñeta de escena de línea clara (sin su cara, no se inventa)")
            quien = None
        try:
            if quien:
                cr = cred.get(fotos[quien].name, {})
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
