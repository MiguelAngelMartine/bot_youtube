"""FORMATO «PRESENTADOR» (21-nov-2026, decisión del usuario: «a partir de ahora se hace este formato siempre»).

- Fondos: SOLO los de Imagenes/Fondos, el que mejor corresponde a cada noticia (nada de la biblioteca ni FLUX).
- Presentador (Imagenes/Presentador): presente a la IZQUIERDA mientras el narrador lee el guion.
- Cita literal de un personaje: el presentador sale (fundido + desliz, nunca brusco) y entra el personaje
  (Imagenes/Políticos) con su frase en un bocadillo (karaoke: la palabra que suena, en amarillo) y su rótulo.
- Cruce de declaraciones: el que ataca se queda a la izquierda y el que replica entra por la DERECHA con su réplica; los
  dos bocadillos se ajustan al hueco entre ambos. Al terminar, salen y vuelve el presentador.
- La voz se graba POR TRAMOS (narración / cita) y entre tramos hay pausas medidas, para que cada cambio de imagen caiga en
  un silencio y el vídeo tenga ritmo.
- Si un personaje no tiene imagen en Imagenes/Políticos, el presentador se queda y aparece solo el bocadillo con su rótulo.

Uso: python presentador.py AAAA-MM-DD largo|N      (N = número de Short)
     python presentador.py catalogo                  (lista lo que hay en Imagenes/)"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import unicodedata
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

RAIZ = Path(__file__).parent
IMG = RAIZ / "Imagenes"
FUENTES = RAIZ / "fuentes"
FPS = 30
ROJO, AMARILLO = (200, 16, 46), (255, 205, 0)
MIN_PAL_CITA = 5          # citas más cortas («vivienda», «que es el PP») se quedan en la narración
PAUSA = {"P>Q": 0.55, "Q>puente": 0.25, "puente>Q": 0.3, "Q>Q": 0.4, "Q>P": 0.6, "seccion": 0.5}
TRANS = 0.4               # duración de entradas y salidas


# ---------------------------------------------------------------- catálogo de imágenes
def _n(s):
    s = unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s)).strip()


def _alfa(im):
    return im.mode == "RGBA" and im.getchannel("A").getextrema()[0] < 20


def _poses(ruta):
    """Una imagen puede traer varias poses en fila (lámina): se separan por las columnas vacías."""
    im = Image.open(ruta).convert("RGBA")
    a = np.asarray(im.getchannel("A")) > 20
    cols = a.any(axis=0)
    segs, ini = [], None
    for x, c in enumerate(list(cols) + [False]):
        if c and ini is None:
            ini = x
        elif not c and ini is not None:
            if x - ini > im.width * 0.06:
                segs.append((ini, x))
            ini = None
    if len(segs) <= 1:
        return [im]
    med = sorted(x1 - x0 for x0, x1 in segs)[len(segs) // 2]
    partidos = []
    for x0, x1 in segs:                                # dos poses que se tocan: se cortan por donde hay menos figura
        while x1 - x0 > med * 1.6:
            dens = a[:, x0:x1].sum(axis=0)
            lo, hi = int((x1 - x0) * 0.3), int((x1 - x0) * 0.7)
            c = x0 + lo + int(np.argmin(dens[lo:hi]))
            partidos.append((x0, c)); x0 = c
        partidos.append((x0, x1))
    segs = partidos
    return [im.crop((x0, 0, x1, im.height)) for x0, x1 in segs]


def catalogo():
    fondos = sorted(p for p in (IMG / "Fondos").glob("*") if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp"))
    pres, laminas = [], []
    for p in sorted((IMG / "Presentador").glob("*.png")):
        im = Image.open(p)
        if _alfa(im):
            ps = _poses(p)
            (pres if len(ps) == 1 else laminas).extend(ps)   # las sueltas (más resolución) primero
    pres += laminas
    pols = {}
    for p in sorted((IMG / "Políticos").rglob("*.png")):   # también subcarpetas (p. ej., «Nuevas»)
        im = Image.open(p)
        if not _alfa(im):
            continue                                   # sin fondo transparente (p. ej., fotos de grupo): no vale
        toks = _nombre_archivo(p)
        if toks and len(toks) <= 4:
            pols.setdefault(toks[-1], []).append(p)    # clave = apellido (última palabra del nombre)
            _NOMBRE[p] = toks
    return fondos, pres, pols


_NOMBRE = {}
# Apellidos que llevan varios políticos conocidos: solo se pone imagen si la cita trae también el nombre de pila.
APELLIDOS_AMBIGUOS = {"montero", "munoz", "garcia", "lopez", "martin", "perez", "gonzalez", "fernandez", "rodriguez"}


def _nombre_archivo(p):
    """«Feijoo_cuerpo_entero» → [feijoo]; «PedroSanchez» → [pedro, sanchez]; «IsabelDiazAyuso» → [isabel, diaz, ayuso]; «Mariano Rajoy» → [mariano, rajoy]."""
    base = re.sub(r"-\d+$", "", p.stem.split("_")[0])
    return _n(re.sub(r"(?<=[a-záéíóúñü])(?=[A-ZÁÉÍÓÚÑ])", " ", base)).split()


def figura_de(nombre, pols, uso):
    """Imagen del político (por apellido, sin tildes); si hay varias, va rotando para dar variedad."""
    toks = _n(nombre).split()
    for clave, rutas in pols.items():
        if clave in toks:
            # Apellidos comunes (Muñoz, Díaz…): si el archivo trae nombre de pila y la cita también, tienen que coincidir.
            resto = set(toks) - {clave}
            if clave in APELLIDOS_AMBIGUOS and not resto:
                continue                               # «Montero» a secas puede ser Irene o María Jesús: sin imagen
            # 24-nov-2026: con varias personas del mismo apellido (Irene y María Jesús Montero), la imagen es la del
            # nombre de pila que trae la cita (antes solo se miraba la primera imagen y la otra se perdía)
            if resto:
                rutas = [r for r in rutas if not set(_NOMBRE.get(r, [clave])[:-1]) or set(_NOMBRE.get(r, [clave])[:-1]) & resto]
                if not rutas:
                    continue
            # 23-nov-2026 (el usuario: «la imagen que siempre utilizas de Sánchez no es la mejor»): las recortadas de una
            # foto de grupo (Grupo/*_grupo.png, poca resolución) solo si no hay otra de esa persona
            buenas = [r for r in rutas if "_grupo" not in Path(str(r)).stem] or rutas
            k = uso.get(clave, 0)
            uso[clave] = k + 1
            return buenas[k % len(buenas)]
    return None


def elige_fondos(textos, fondos, cache=None):
    """El fondo que mejor corresponde a cada noticia (Gemini mira los nombres; si no responde, por palabras clave).
    Evita repetir el mismo fondo en noticias seguidas."""
    if cache and cache.exists():
        try:
            el = json.loads(cache.read_text(encoding="utf-8"))
            if len(el) == len(textos) and all((IMG / "Fondos" / x).exists() for x in el):
                return [IMG / "Fondos" / x for x in el]
        except ValueError:
            pass
    nombres = [f.stem for f in fondos]
    idx = None
    try:
        import gem
        r = gem.pide("Eres realizador de un informativo de política española. Para cada NOTICIA elige el FONDO (por su "
                     "número) que mejor corresponde al lugar o institución de la que habla (Gobierno/Moncloa, Congreso, "
                     "Senado, Parlamento Europeo, rueda de prensa, sede de un partido...). No repitas el mismo fondo en dos "
                     "noticias seguidas si hay otro que encaje.\nFONDOS:\n" +
                     "\n".join(f"{i}. {n}" for i, n in enumerate(nombres)) + "\n\nNOTICIAS:\n" +
                     "\n".join(f"{i}. {t[:500]}" for i, t in enumerate(textos)) +
                     '\n\nResponde SOLO JSON: {"fondos": [numero_de_fondo_por_cada_noticia]}', como_json=True)
        idx = [int(x) for x in (r or {}).get("fondos", [])]
        if len(idx) != len(textos) or any(not 0 <= x < len(fondos) for x in idx):
            idx = None
    except Exception:
        idx = None
    if idx is None:
        claves = {"moncloa": "moncloa gobierno presidente ministro consejo", "congreso": "congreso diputados sesion pleno",
                  "hemiciclo": "pleno hemiciclo votacion diputados debate", "europeo": "europa bruselas europeo ue",
                  "podio": "rueda prensa comparecencia anuncia", "senado": "senado senadores"}
        idx, prev = [], -1
        for t in textos:
            nt = _n(t)
            pts = []
            for i, n in enumerate(nombres):
                nn = _n(n)
                p = sum(nt.count(w) for k, ws in claves.items() if k in nn for w in ws.split())
                pts.append((p - (5 if i == prev else 0), -i))
            prev = max(range(len(fondos)), key=lambda i: pts[i])
            idx.append(prev)
    out = [fondos[i] for i in idx]
    if cache:
        cache.write_text(json.dumps([f.name for f in out], ensure_ascii=False), encoding="utf-8")
    return out


# ---------------------------------------------------------------- guion -> tramos
def _quien_de_cita(texto, m, defecto, conocidas):
    """Quién dice la cita m (re.Match sobre texto): el hablante explícito de su frase; si no, el de por defecto."""
    import render_ambiente as RA

    class _T:
        @staticmethod
        def en(k):
            return k
    qs = RA._citas_timeline(texto, 0, texto, _T, conocidas, defecto)
    for a, b, p in qs:
        if a <= m.start() + 1 and m.end() - 1 <= b + 1:
            return p
    return defecto


_NO_PILA = {"y", "e", "o", "ni", "pero", "ademas", "tambien", "mientras", "ahora", "hoy", "ayer", "luego", "entonces",
            "presidente", "presidenta", "ministro", "ministra", "lider", "portavoz", "candidato", "candidata", "el", "la",
            "vicepresidenta", "vicepresidente", "secretario", "secretaria", "expresidente", "exministro", "alcalde",
            "alcaldesa", "senor", "senora", "don", "dona"}


def _apellidos(frag, conocidas):
    """Personas conocidas nombradas en frag que NO son destinatario («a/contra/sobre Fulano»), en orden de aparición."""
    out = []
    for mm in re.finditer(r"\b([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)\b", frag):
        w = mm.group(1)
        if re.search(r"\b(?:a|al|contra|para|sobre|con|que|imitando a|de)\s+(?:\w+\s+){0,2}$", frag[:mm.start()]):
            continue
        previa = re.search(r"\b([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)\s+$", frag[:mm.start()])
        # 22-nov-2026: «Cayetana Álvarez» no es «Pepe Álvarez»: si delante va un nombre de pila, tiene que ser el suyo
        pila = _n(previa.group(1)) if previa and _n(previa.group(1)) not in _NO_PILA else None
        n = next((n for n, _ in conocidas if _n(n).split()[-1:] == [_n(w)] and (pila is None or pila in _n(n).split())),
                 None)
        if n and n not in out:
            out.append(n)
    return out


def _quien_antes(texto, m, conocidas):
    """Formato presentador: quién dice la cita va JUSTO ANTES, como sujeto de la frase que la introduce
    («Feijóo saca las entradas en Ceuta, y añade: «…»»). Si en esa frase hay más de un posible hablante, no se adivina."""
    ini = max([texto.rfind(x, 0, m.start()) for x in (". ", "! ", "? ", "». ")] + [-1]) + 1
    frag = re.sub(r"«[^»]*»", " ", texto[ini:m.start()])
    if not frag.strip():
        return None
    ns = _apellidos(frag, conocidas)
    return ns[0] if len(ns) == 1 else None


def _quien_despues(texto, m, conocidas):
    """El gancho abre la pieza y quién lo dice va justo DESPUÉS («…». Sánchez ataca a Feijóo). SOLO si la cita abre su
    frase (si no, la frase siguiente habla de otra cosa)."""
    ini = max([texto.rfind(x, 0, m.start()) for x in (". ", "! ", "? ", "». ", ": ")] + [-1]) + 1
    if texto[ini:m.start()].strip():
        return None
    sig = texto[m.end():m.end() + 90]
    sig = re.split(r"[.!?]\s", sig, maxsplit=1)[0]
    for w in re.findall(r"\b([A-ZÁÉÍÓÚÑ][\wáéíóúñ]+)\b", sig)[:2]:
        if re.search(r"\b(?:a|al|contra|para|sobre)\s+(?:\w+\s+){0,2}" + re.escape(w), sig):
            continue
        for n, _ in conocidas:
            if _n(n).split()[-1:] == [_n(w)]:
                return n
    return None


def tramos_de(texto, defecto="", conocidas=(), quien_de=None):
    """Parte el texto que lee la voz en tramos: {"tipo": "P"|"Q", "di", "quien"?}. Una cita literal de 4+ palabras de
    alguien identificado es un tramo Q (sale el personaje); lo demás es narración del presentador (P)."""
    out, pos = [], 0
    for m in re.finditer(r"«([^»]+)»[.,;:]?", texto):
        cita = m.group(1)
        explicita = quien_de(cita) if quien_de else None     # 23-nov-2026: si el guion dice quién la dice, vale aunque
        if len(cita.split()) < MIN_PAL_CITA and not explicita:  # sea corta («Educación socialista»)
            continue
        # 22-nov-2026 (fallo real: «Vamos a seguir votando al PSOE», de 8 veteranos, salió con Sánchez; y la ironía de
        # Urtasun «con Rufián» salió con Rufián): si la cita la introduce una frase («X firman:», «Y Fulano ironiza…:»)
        # y en ella no consta un único hablante conocido, NO se adivina: la lee el presentador. Las conjeturas
        # (_quien_de_cita, _quien_despues) solo valen cuando la cita abre su frase.
        ini_f = max([texto.rfind(x, 0, m.start()) for x in (". ", "! ", "? ", "». ")] + [-1]) + 1
        presentada = bool(re.sub(r"«[^»]*»", " ", texto[ini_f:m.start()]).strip())
        quien = (quien_de(cita) if quien_de else None) or _quien_antes(texto, m, conocidas) \
            or (None if presentada else (_quien_de_cita(texto, m, defecto, conocidas) or _quien_despues(texto, m, conocidas)))
        if not quien and presentada and out and out[-1]["tipo"] == "Q":
            # 23-nov-2026: «…». Les acusa de «…»: la frase siguiente a una cita, sin nombre nuevo y con un verbo de
            # continuidad, es del MISMO hablante (nunca con «responde/contesta/replica», que indican a otro)
            frag = re.sub(r"«[^»]*»", " ", texto[ini_f:m.start()])
            entre = texto[pos:m.start()]
            if not _apellidos(frag, conocidas) and len(re.findall(r"[.!?]\s", entre)) <= 1 \
                    and re.search(r"\b(acusa|acusan|añade|insiste|remata|sigue|advierte|avisa|critica|pide|exige|"
                                  r"denuncia|recuerda|asegura|zanja|subraya|tacha|llama)\b", frag, re.I) \
                    and not re.search(r"\b(responde|contesta|replica|le dice)\b", frag, re.I) \
                    and not re.search(r"\b(PSOE|PP|Vox|Sumar|Podemos|ERC|Junts|Bildu|PNV|Frente Amplio|Gobierno|Ferraz|"
                                      r"G[eé]nova|Moncloa|partido|ministerio|fuentes|comunicado)\b", frag):
                # 26-nov-2026 (fallo real: «El PSOE le pide desde Ferraz: «…»» salió en el globo de Feijóo): si la frase
                # trae otro sujeto (un partido, el Gobierno, una sede…), la cita NO es del hablante anterior
                quien = out[-1]["quien"]
        if not quien:
            continue
        antes = texto[pos:m.start()].strip()
        if antes:
            out.append({"tipo": "P", "di": antes})
        di = m.group(0).strip()
        if not di.endswith((".", "»")):
            di = di.rstrip(",;:") + "»" if not di.endswith("»") else di
        out.append({"tipo": "Q", "di": di.rstrip(",;:") if di.endswith(("»,", "»;", "»:")) else di, "quien": quien,
                    "cita": cita})
        pos = m.end()
    resto = texto[pos:].strip()
    if resto:
        out.append({"tipo": "P", "di": resto})
    # 23-nov-2026 (el usuario: «parte de la cita quedó fuera del globo»): si la cita va en MITAD de una frase («Les acusa de
    # «…» con el voto útil.»), la frase entera va en el globo (las comillas marcan lo literal) y el presentador no vuelve
    # solo para decir la cola. Antes: el trozo sin puntuación justo delante de las comillas; después: la cola que sigue
    # en minúscula hasta el punto (8 palabras como mucho).
    for i, g in enumerate(out):
        if g["tipo"] != "Q":
            continue
        if i > 0 and out[i - 1]["tipo"] == "P":
            prev = out[i - 1]["di"]
            corte = max(prev.rfind(x) for x in (". ", "! ", "? ", ": ", "». ", "; "))
            frag = prev[corte + 2:] if corte >= 0 else prev
            if frag and len(frag.split()) <= 5 and not frag.rstrip().endswith((":", ".", "!", "?", ";")):
                g["di"] = frag.strip() + " " + g["di"]
                out[i - 1]["di"] = prev[:corte + 1].strip() if corte >= 0 else ""
        if i + 1 < len(out) and out[i + 1]["tipo"] == "P" and not g["di"].rstrip().endswith((".", "!", "?")):
            sig = out[i + 1]["di"]
            m2 = re.match(r"([a-záéíóúñ][^.!?]*[.!?])\s*", sig)
            if m2 and len(m2.group(1).split()) <= 8:
                g["di"] = g["di"].rstrip(",;:") + " " + m2.group(1)
                out[i + 1]["di"] = sig[m2.end():].strip()
    out = [g for g in out if g["tipo"] == "Q" or g["di"]]
    # puentes y cruces: narración corta entre dos citas -> el primero se queda; si es otra persona, entra a la derecha
    for i, g in enumerate(out):
        if g["tipo"] == "P" and 0 < i < len(out) - 1 and out[i - 1]["tipo"] == "Q" and out[i + 1]["tipo"] == "Q" \
                and len(g["di"].split()) <= 12:
            g["puente"] = True
    return out


def sin_imagen(tr):
    """21-nov-2026 (el usuario): una cita con globo va SIEMPRE con el personaje que la dice. Si no hay imagen de esa
    persona en Imagenes/Políticos, la lee el presentador SIN globo (como narración) y se avisa por Telegram de la imagen
    que falta. Además, la misma persona escrita de dos formas («Feijóo», «Alberto Núñez Feijóo») es UNA sola: con dos
    nombres salía dos veces en pantalla, a cada lado, con los globos encima. Devuelve los nombres sin imagen."""
    _, _, pols = catalogo()
    uso, faltan, canon = {}, [], {}
    for g in tr:
        if g["tipo"] != "Q":
            continue
        r = figura_de(g["quien"], pols, uso)
        if r is None:
            g["tipo"], g["sin_imagen"] = "P", g["quien"]
            faltan.append(g["quien"])
            continue
        tk = _n(g["quien"]).split()                      # la PERSONA (no la imagen: hay dos de Feijóo y se alternan)
        g["pid"] = " ".join(tk) if tk and tk[-1] in APELLIDOS_AMBIGUOS else (tk[-1] if tk else str(r))
        if len(g["quien"]) > len(canon.get(g["pid"], "")):
            canon[g["pid"]] = g["quien"]
    for g in tr:
        if g.get("pid"):
            g["quien"] = canon[g["pid"]]
        g.pop("puente", None)
    for i, g in enumerate(tr):                           # puentes otra vez, con las citas que quedan
        if g["tipo"] == "P" and 0 < i < len(tr) - 1 and tr[i - 1]["tipo"] == "Q" and tr[i + 1]["tipo"] == "Q" \
                and len(g["di"].split()) <= 12 and not tr[i - 1].get("seccion_fin") and not g.get("seccion_fin"):
            g["puente"] = True                           # nunca de una noticia a otra
    return sorted(set(faltan))


def avisa_sin_imagen(fecha, pieza, faltan):
    if not faltan:
        return
    txt = (f"{pieza}: falta la imagen de {', '.join(faltan)} en Imagenes/Políticos. Su cita la ha leído el presentador "
           f"sin globo. Si la añades, se rehace con su personaje.")
    print("AVISO:", txt)
    try:
        import notifica
        notifica.aviso(fecha, "🖼️ " + txt)
    except (SystemExit, Exception) as e:
        print(f"(Telegram: {e})")


def _ordena_lados(tr):
    """Marca cada cita con su lado y su grupo: un grupo es una cita y sus réplicas seguidas (con puentes cortos)."""
    grupo = -1
    for i, g in enumerate(tr):
        if g["tipo"] != "Q":
            continue
        prev = next((tr[j] for j in range(i - 1, -1, -1) if not tr[j].get("puente")), None)
        sigue = prev is not None and prev["tipo"] == "Q" and prev.get("grupo") is not None
        if sigue and prev["quien"] != g["quien"] and prev.get("lado") == "izq" and \
                not any(x.get("lado") == "der" for x in tr if x.get("grupo") == prev["grupo"]):
            g["lado"], g["grupo"] = "der", prev["grupo"]
        elif sigue and prev["quien"] == g["quien"]:
            g["lado"], g["grupo"] = prev["lado"], prev["grupo"]
        else:
            grupo += 1
            g["lado"], g["grupo"] = "izq", grupo
    # 22-nov-2026: un tramo corto entre citas de GRUPOS distintos no es un puente: lo dice el presentador en pantalla
    # (si no, el escenario se quedaba vacío con el subtítulo hasta que entraba el siguiente)
    for i, g in enumerate(tr):
        if g.get("puente") and 0 < i < len(tr) - 1 and tr[i - 1].get("grupo") != tr[i + 1].get("grupo"):
            g.pop("puente")
    return tr


# ---------------------------------------------------------------- voz por tramos
def _locuta_entero(tramos, tmp, t_ini=0.0):
    """21-nov-2026 (estándar del usuario): la voz lee de corrido cada bloque (un Short, una sección del largo; el cierre
    aparte) y los tramos se sacan de los tiempos de sus palabras. Las pausas las pone el guion (y las comillas)."""
    import voz
    bloques, cur = [], []
    for g in tramos:
        if g.get("cierre") and cur:
            bloques.append(cur)
            cur = []
        cur.append(g)
        if g.get("seccion_fin") or g.get("cierre"):
            bloques.append(cur)
            cur = []
    if cur:
        bloques.append(cur)
    sr, ch, trozos, t = 48000, 2, [], t_ini
    for k, bl in enumerate(bloques):
        wav = tmp / f"bloque_{k:03d}.wav"
        texto = " ".join(g["di"] for g in bl)
        pal, _ = voz.locuta([{"di": texto}], "normal", wav, cola=0.0)
        with wave.open(str(wav)) as w:
            sr, ch = w.getframerate(), w.getnchannels()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)
        amp = np.abs(x[:, 0].astype(np.int32))
        fin = int(np.nonzero(amp > 300)[0][-1]) + int(0.08 * sr) if (amp > 300).any() else len(x)
        x = x[:min(len(x), fin)]
        i = 0
        for g in bl:
            n = len(g["di"].split())
            ps = pal[i:i + n] or pal[-1:]
            i += n
            g.update({"t0": t + ps[0][0], "t1": t + ps[-1][1], "pal": [(p[2], t + p[0], t + p[1]) for p in ps]})
        dur = len(x) / sr
        sig = bloques[k + 1][0] if k + 1 < len(bloques) else None
        pausa = 0.0 if sig is None else (0.3 if sig.get("cierre") else PAUSA["seccion"])
        trozos += [x, np.zeros((int(pausa * sr), ch), dtype=np.int16)]
        t += dur + pausa
    audio = np.concatenate(trozos)
    audio, extra = _huecos_de_escena(tramos, audio, sr, t_ini)
    t += extra
    with wave.open(str(tmp / "voz.wav"), "wb") as w:
        w.setnchannels(audio.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(audio.tobytes())
    env = np.abs(audio[:, 0].astype(np.float32))
    n = int(sr / FPS)
    env = np.array([env[i * n:(i + 1) * n].mean() if i * n < len(env) else 0 for i in range(len(env) // n + 2)])
    env = np.convolve(env / (env.max() + 1e-6), np.ones(4) / 4, "same")
    return t, env


HUECO_ESCENA = 0.85        # s de silencio mínimo en cada cambio de escena (sale uno del todo y luego entra el otro)


def _escena_de(g):
    """Quién está en pantalla en este tramo: el presentador, o el grupo de personajes de la cita. El puente de un cruce
    no cambia de escena."""
    if g["tipo"] == "Q":
        return ("G", g.get("grupo"))
    return None if g.get("puente") else "P"


def _huecos_de_escena(tramos, audio, sr, t_ini):
    """22-nov-2026 (el usuario: «no se puede solapar nada, ni personajes entre ellos ni bocadillos… si hay que añadir una
    pausa para que dé tiempo a que salga uno y entre otro, que se añada»). En cada cambio de escena (presentador ↔
    personajes, o de un cruce a otro) alarga el silencio de la voz hasta HUECO_ESCENA, cortando en mitad del silencio que
    ya hay, y corre los tiempos de lo que viene después. La salida tarda 0,05 + TRANS s y la entrada empieza 0,3 s antes
    de hablar: con 0,85 s no coinciden nunca."""
    cortes, prev = [], None
    for k, g in enumerate(tramos):
        esc = _escena_de(g)
        if esc is None:
            continue
        if prev is not None and esc != prev[1]:
            a = tramos[prev[0]]
            falta = HUECO_ESCENA - (g["t0"] - a["t1"])
            if falta > 0.01:
                cortes.append(((a["t1"] + g["t0"]) / 2, falta, k))
        prev = (k, esc)
    if not cortes:
        return audio, 0.0
    trozos, desde, extra = [], 0, 0.0
    ch = audio.shape[1]
    for mitad, falta, k in cortes:
        i = max(desde, min(len(audio), int((mitad - t_ini) * sr)))
        trozos += [audio[desde:i], np.zeros((int(falta * sr), ch), dtype=np.int16)]
        desde = i
        for g in tramos[k:]:                           # todo lo que viene después se corre
            g["t0"] += falta; g["t1"] += falta
            g["pal"] = [(p, a + falta, b + falta) for p, a, b in g.get("pal", [])]
        extra += falta
    trozos.append(audio[desde:])
    return np.concatenate(trozos), extra


def locuta_tramos(tramos, tmp, t_ini=0.0):
    import voz
    if getattr(voz, "LECTURA_ENTERA", False):
        return _locuta_entero(tramos, tmp, t_ini)
    sr, trozos, t = 48000, [], t_ini
    for k, g in enumerate(tramos):
        wav = tmp / f"tramo_{k:03d}.wav"
        pal, _ = voz.locuta([{"di": g["di"]}], "normal", wav, cola=0.0)
        with wave.open(str(wav)) as w:
            sr, ch = w.getframerate(), w.getnchannels()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).reshape(-1, ch)
        # recorta el silencio del final (la pausa la ponemos nosotros, medida)
        amp = np.abs(x[:, 0].astype(np.int32))
        fin = int(np.nonzero(amp > 300)[0][-1]) + int(0.08 * sr) if (amp > 300).any() else len(x)
        x = x[:min(len(x), fin)]
        dur = len(x) / sr
        g.update({"t0": t, "t1": t + dur, "pal": [(p[2], t + p[0], t + p[1]) for p in pal]})
        sig = tramos[k + 1] if k + 1 < len(tramos) else None
        if sig is None:
            pausa = 0.0
        elif g.get("seccion_fin"):
            pausa = PAUSA["seccion"]
        elif g["tipo"] == "P" and sig["tipo"] == "Q":
            pausa = PAUSA["puente>Q"] if g.get("puente") else PAUSA["P>Q"]
        elif g["tipo"] == "Q" and sig.get("puente"):
            pausa = PAUSA["Q>puente"]
        elif g["tipo"] == "Q" and sig["tipo"] == "Q":
            pausa = PAUSA["Q>Q"]
        elif g["tipo"] == "Q":
            pausa = PAUSA["Q>P"]
        else:
            pausa = 0.12
        trozos += [x, np.zeros((int(pausa * sr), ch), dtype=np.int16)]
        t += dur + pausa
    audio = np.concatenate(trozos)
    with wave.open(str(tmp / "voz.wav"), "wb") as w:
        w.setnchannels(audio.shape[1]); w.setsampwidth(2); w.setframerate(sr); w.writeframes(audio.tobytes())
    env = np.abs(audio[:, 0].astype(np.float32))
    n = int(sr / FPS)
    env = np.array([env[i * n:(i + 1) * n].mean() if i * n < len(env) else 0 for i in range(len(env) // n + 2)])
    env = np.convolve(env / (env.max() + 1e-6), np.ones(4) / 4, "same")
    return t, env


# ---------------------------------------------------------------- dibujo
def fuente(n, tam):
    return ImageFont.truetype(str(FUENTES / n), tam)


def ease(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def envuelve(txt, f, ancho):
    lineas, cur = [], ""
    for w in txt.split():
        prueba = (cur + " " + w).strip()
        if f.getlength(prueba) > ancho and cur:
            lineas.append(cur); cur = w
        else:
            cur = prueba
    return lineas + [cur]


def recorte(im, alto, corte=0.66):
    """Figura sin fondo, de la cabeza a medio muslo (plano americano), escalada a `alto`."""
    im = im.convert("RGBA") if isinstance(im, Image.Image) else Image.open(im).convert("RGBA")
    im = im.crop(im.getchannel("A").point(lambda a: 255 if a > 20 else 0).getbbox())
    im = im.crop((0, 0, im.width, int(im.height * corte)))
    k = alto / im.height
    return im.resize((max(1, int(im.width * k)), alto), Image.LANCZOS)


def sombra(fig):
    a = fig.getchannel("A").filter(ImageFilter.GaussianBlur(18))
    s = Image.new("RGBA", fig.size, (0, 0, 0, 0))
    s.putalpha(a.point(lambda v: int(v * 0.45)))
    return s


def _palabra_actual(g, t):
    return sum(1 for p in g["pal"] if p[1] <= t)


def tarjeta(g, t, activo, lado, nombre, cargo, medio, ancho, tam, max_h=None, cola_dx=None):
    """cola_dx (23-nov-2026): con lado «abajo», dónde va la flecha: (px desde la izquierda) o (-px desde la derecha), para
    que apunte al personaje que habla (antes iba siempre a la izquierda y el globo de la derecha señalaba al otro)."""
    txt = pantalla(g["di"])
    while True:
        fq = fuente("Inter-Black.ttf", tam)
        lineas = envuelve(txt, fq, ancho)
        lh = int(tam * 1.28)
        alto = len(lineas) * lh + int(tam * 2.9) + 10
        if not max_h or alto <= max_h or tam <= 28:
            break
        tam -= 2
    pie = int(tam * 1.85)
    c = Image.new("RGBA", (ancho + 80, alto), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, c.width - 1, alto - 1), 28, fill=(255, 255, 255, 240))
    d.rounded_rectangle((0, alto - pie, c.width - 1, alto - 1), 28, fill=ROJO + (255,))
    d.rectangle((0, alto - pie, c.width - 1, alto - pie + 24), fill=ROJO + (255,))
    fn, fc = fuente("Inter-Black.ttf", int(tam * 0.68)), fuente("Inter-SemiBold.ttf", int(tam * 0.52))
    d.text((40, alto - pie + int(tam * 0.18)), nombre.upper(), font=fn, fill="white")
    sub = " · ".join(x for x in (cargo, f"según {medio}" if medio else "") if x)
    d.text((40, alto - pie + int(tam * 0.98)), sub[:80], font=fc, fill=(255, 225, 225))
    k = _palabra_actual(g, t)
    y, iw = 24, 0
    for ln in lineas:
        x = 40
        for w in ln.split():
            col = (25, 25, 35) if iw < k else (150, 150, 160)
            if iw == k - 1 and activo and t <= g["t1"] + 0.05:
                d.rounded_rectangle((x - 6, y + 2, x + fq.getlength(w) + 6, y + lh - 4), 10, fill=AMARILLO + (255,))
            d.text((x, y), w, font=fq, fill=col if activo else (110, 110, 120))
            x += fq.getlength(w + " "); iw += 1
        y += lh
    cola = Image.new("RGBA", (56, 56), (0, 0, 0, 0))
    pts = {"izq": [(0, 28), (56, 0), (56, 56)], "der": [(56, 28), (0, 0), (0, 56)],
           "abajo": [(0, 0), (56, 0), (28, 56)]}[lado]
    ImageDraw.Draw(cola).polygon(pts, fill=(255, 255, 255, 240))
    if lado == "abajo":
        full = Image.new("RGBA", (c.width, c.height + 46), (0, 0, 0, 0))
        cx = 120 if cola_dx is None else (cola_dx if cola_dx >= 0 else c.width + cola_dx)
        cx = max(30, min(c.width - 86, int(cx) - 28))
        full.alpha_composite(c, (0, 0)); full.alpha_composite(cola, (cx, c.height - 10))
    else:
        full = Image.new("RGBA", (c.width + 46, c.height), (0, 0, 0, 0))
        if lado == "izq":
            full.alpha_composite(cola, (0, 50)); full.alpha_composite(c, (46, 0))
        else:
            full.alpha_composite(c, (0, 0)); full.alpha_composite(cola, (c.width - 10, 50))
    if not activo:
        full.putalpha(full.getchannel("A").point(lambda v: int(v * 0.8)))
    return full


def pantalla(txt):
    """24-nov-2026: lo que se ESCRIBE para la voz (voz.ESCRIBE, p. ej. «Estér») nunca sale en pantalla: ahí, la forma
    correcta («Ester»)."""
    import voz
    for bien, para_voz in voz.ESCRIBE.items():
        txt = re.sub(r"(?<!\w)" + re.escape(para_voz) + r"(?!\w)", bien, txt)
    return txt


def subtitulo(g, t, ancho, tam, max_lineas=3):
    f = fuente("Inter-Black.ttf", tam)
    lineas = envuelve(pantalla(g["di"]), f, ancho)
    k = _palabra_actual(g, t)
    # karaoke por páginas de max_lineas: se ve el trozo en el que va la voz
    pal_l = [len(ln.split()) for ln in lineas]
    ini, acum, pag = 0, 0, []
    for i, n in enumerate(pal_l):
        pag.append(i)
    paginas = [lineas[i:i + max_lineas] for i in range(0, len(lineas), max_lineas)]
    cuenta = 0
    for p in paginas:
        n = sum(len(x.split()) for x in p)
        if k <= cuenta + n or p is paginas[-1]:
            break
        cuenta += n
    lh = int(tam * 1.5)
    c = Image.new("RGBA", (ancho + 40, lh * len(p) + 20), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    iw, y = cuenta, 6
    for ln in p:
        x = 20
        for w in ln.split():
            d.text((x, y), w, font=f, fill=AMARILLO if iw == k - 1 else "white", stroke_width=max(4, tam // 10),
                   stroke_fill=(10, 10, 20))
            x += f.getlength(w + " "); iw += 1
        y += lh
    return c


class Escena:
    """Monta el vídeo: fondos por tramo, presentador, personajes, bocadillos y subtítulos."""

    def __init__(self, tramos, total, env, W, H, fondos_tr, cargos, medios, vertical=False):
        self.tr, self.total, self.env, self.W, self.H = tramos, total, env, W, H
        self.vertical = vertical
        _, poses, pols = catalogo()
        if not poses:
            raise SystemExit("no hay presentador en Imagenes/Presentador")
        self.cargos, self.medios = cargos, medios
        uso = {}
        # 23-nov-2026 (el usuario: «haz los personajes más grandes»): en vertical, figuras más grandes con la cabeza a la
        # misma altura (debajo de los globos) y el cuerpo cortado por el borde inferior (plano medio)
        alto = int(H * (0.86 if vertical else 0.86))
        self.alto = alto
        self.figs = {}
        for g in tramos:
            if g["tipo"] == "Q" and g["quien"] not in self.figs:
                r = figura_de(g["quien"], pols, uso)
                self.figs[g["quien"]] = recorte(r, alto) if r else None
        # el presentador cambia de pose cada vez que vuelve (variedad), en orden
        self.poses = [recorte(p, alto, 0.62) for p in poses]
        self.sombras = {}
        # fondos (uno por tramo, con fundido al cambiar)
        self.fondos = {}
        for f in set(fondos_tr):
            im = Image.open(f).convert("RGB")
            k = max(W / im.width, H / im.height) * 1.06
            self.fondos[f] = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        self.fondo_tr = fondos_tr
        vi = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vi)
        for i in range(60):
            vd.rectangle((i * 6, i * 4, W - i * 6, H - i * 4), outline=(0, 0, 0, int(120 * (1 - i / 60) ** 2)), width=6)
        if vertical:
            g_ = Image.linear_gradient("L").resize((W, 700)).point(lambda v: int(max(0, v - 90) * 1.2))
            som = Image.new("RGBA", (W, 700), (6, 10, 22, 255)); som.putalpha(g_)
            vi.alpha_composite(som, (0, H - 700))
            gt = Image.linear_gradient("L").resize((W, 260)).point(lambda v: int(max(0, 170 - v)))
            st = Image.new("RGBA", (W, 260), (6, 10, 22, 255)); st.putalpha(gt)
            vi.alpha_composite(st, (0, 0))
        self.vi = vi
        self._ventanas()

    def _ventanas(self):
        """Quién está en pantalla y cuándo: (clave, lado, t_in, t_out, pose)."""
        tr, V, pose = self.tr, [], 0
        grupos = {}
        for g in tr:
            if g["tipo"] == "Q":
                grupos.setdefault(g["grupo"], []).append(g)
        self.cruce = {k: (len({x["lado"] for x in v}) == 2) for k, v in grupos.items()}
        hecho = set()
        pres_ini = None
        for i, g in enumerate(tr):
            sin_fig = g["tipo"] == "Q" and self.figs.get(g["quien"]) is None
            es_pres = (g["tipo"] == "P" and not g.get("puente")) or sin_fig
            if es_pres and pres_ini is None:
                pres_ini = 0.0 if not V and i == 0 else g["t0"] - (0.22 if i and tr[i - 1]["tipo"] == "Q" else 0.3)
            if not es_pres and pres_ini is not None:
                V.append(("P", "izq", pres_ini, tr[i - 1]["t1"] + 0.05, pose)); pose += 1; pres_ini = None
            if g["tipo"] == "Q" and not sin_fig and g["grupo"] not in hecho:
                hecho.add(g["grupo"])
                miembros = [x for x in grupos[g["grupo"]] if self.figs.get(x["quien"]) is not None]
                fin = max(x["t1"] for x in grupos[g["grupo"]]) + 0.05
                vistos = set()
                for x in miembros:
                    if (x["quien"], x["lado"]) not in vistos:
                        vistos.add((x["quien"], x["lado"]))
                        V.append((x["quien"], x["lado"], x["t0"] - 0.3, fin, 0))
        if pres_ini is not None:
            V.append(("P", "izq", pres_ini, self.total + 5, pose))
        self.V = V
        self.grupos = grupos

    def _fig(self, clave, pose):
        return self.poses[pose % len(self.poses)] if clave == "P" else self.figs[clave]

    def _sombra(self, clave, pose, fig):
        k = (clave, pose % len(self.poses) if clave == "P" else 0)
        if k not in self.sombras:
            self.sombras[k] = sombra(fig)
        return self.sombras[k]

    FUERA = 0.32                  # parte de la figura (brazos del lado de fuera) que puede salirse por el borde en un cruce

    def _escala_video(self):
        """23-nov-2026: la escala común del vídeo. En vertical, la que hace que en el cruce más ancho cada figura quepa en
        su mitad (con hasta un 15 % por fuera del borde), sin pasar de 0,92 si hay cruces ni de 1 si no los hay."""
        if not hasattr(self, "_esc_v"):
            e = 1.0
            if self.vertical:
                for k, gr in self.grupos.items():
                    if self.cruce.get(k):
                        e = min(e, 0.92)
                        for x in gr:
                            f = self.figs.get(x["quien"])
                            if f is not None:
                                e = min(e, (self.W / 2 - 14) / (f.width * (1 - self.FUERA)))
            self._esc_v = max(0.6, e)
        return self._esc_v

    def _pos(self, clave, lado, g_cruce):
        W, H = self.W, self.H
        if self.vertical:
            if g_cruce:
                # cada figura en su mitad: el borde de dentro a 14 px del centro; lo que sobra sale por el borde de fuera
                f = self.figs.get(clave)
                fw = (f.width if f is not None else W * 0.45) * self._escala_video()
                cx = min(0.25 * W, W / 2 - 14 - fw / 2) if lado == "izq" else max(0.75 * W, W / 2 + 14 + fw / 2)
                return cx
            return 0.38 * W
        if clave == "P" or not g_cruce:
            return (0.19 if lado == "izq" else 0.81) * W
        return (0.14 if lado == "izq" else 0.86) * W

    def fondo_en(self, t):
        i = max([k for k, g in enumerate(self.tr) if g["t0"] - 0.3 <= t] or [0])
        return i

    def cuadro(self, t):
        W, H = self.W, self.H
        i = self.fondo_en(t)
        f = self.fondo_tr[i]
        fr = self._vista(f, t)
        # fundido de fondo al cambiar de noticia
        j = next((k for k in range(i, 0, -1) if self.fondo_tr[k] != self.fondo_tr[k - 1]), None)
        if j is not None and j == i:
            q = 1.0   # 26-nov: corte seco (el fundido dejaba fondos superpuestos y un presentador fantasma)
            if q < 1:
                prev = self._vista(self.fondo_tr[j - 1], t)
                fr = Image.blend(prev, fr, q)
        fr = fr.convert("RGBA")
        fr.alpha_composite(self.vi)
        n = min(int(t * FPS), len(self.env) - 1)
        habla = self.env[n]
        g_act = next((g for g in self.tr if g["t0"] - 0.35 <= t <= g["t1"] + 0.65), None)
        for clave, lado, t_in, t_out, pose in self.V:
            a = min(ease((t - t_in) / TRANS), 1 - ease((t - t_out) / TRANS))
            if a <= 0.01:
                continue
            fig = self._fig(clave, pose)
            en_cruce = clave != "P" and any(self.cruce.get(g["grupo"]) for g in self.tr
                                            if g["tipo"] == "Q" and g["quien"] == clave and g["t0"] - 0.4 <= t_out)
            hablando = any(g["t0"] <= t <= g["t1"] and ((g["tipo"] == "P" and clave == "P") or g.get("quien") == clave)
                           for g in self.tr)
            # 20-nov-2026 (el usuario: «parece que están temblando, las quiero estáticas»): los personajes están QUIETOS en
            # pantalla; solo se mueven al entrar y salir (desliz + fundido). Nada de «respirar» ni de balanceo al hablar.
            # 23-nov-2026 (el usuario: «todos los personajes del mismo tamaño»): UNA escala para todo el vídeo, la misma
            # para el presentador y para cada personaje, solo o en un cruce
            s = self._escala_video()
            if s != 1.0:
                k_ = (clave, pose % len(self.poses) if clave == "P" else 0, s)
                if k_ not in self.sombras:
                    self.sombras[k_] = fig.resize((int(fig.width * s), int(fig.height * s)), Image.LANCZOS)
                f2 = self.sombras[k_]
            else:
                f2 = fig
            dx = (1 - a) * (-90 if lado == "izq" else 90)
            cx = int(round(self._pos(clave, lado, en_cruce) + dx))
            x, y = cx - f2.width // 2, H - f2.height + 6
            if self.vertical:                             # la cabeza nunca sube más que el 46 % de la pantalla (globos)
                y = max(y, int(H * 0.46))
            sh = self._sombra(clave, pose, fig)
            if sh.size != f2.size:
                sh = sh.resize(f2.size)
            if a < 1:
                f2 = f2.copy(); f2.putalpha(f2.getchannel("A").point(lambda v, a=a: int(v * a)))
                sh = sh.copy(); sh.putalpha(sh.getchannel("A").point(lambda v, a=a: int(v * a)))
            fr.alpha_composite(sh, (x + 14, y + 10))
            fr.alpha_composite(f2, (x, y))
        self._bocadillos(fr, t)
        g = next((g for g in self.tr if g["tipo"] == "P" and g["t0"] - 0.1 <= t <= g["t1"] + 0.25), None)
        if g and not g.get("cierre"):
            if self.vertical:
                s = subtitulo(g, t, W - 120, 62)
                # 22-nov: el puente DENTRO de un cruce va en el hueco del globo derecho (que aún no ha entrado): arriba
                # pisaba el globo izquierdo
                dentro = any(self.cruce.get(k) and min(x["t0"] for x in gr) < g["t0"] < max(x["t0"] for x in gr)
                             for k, gr in self.grupos.items())
                # 23-nov-2026: puente entre dos citas FUERA de un cruce (la misma persona sigue): el globo anterior aún
                # está donde iría el subtítulo; ese tramo corto va sin subtítulo (la voz lo dice igual)
                if g.get("puente") and not dentro:
                    pass
                elif not (dentro and t > g["t1"] - 0.3):  # se va antes: el globo derecho entra 0,25 s antes de la cita
                    fr.alpha_composite(s, ((W - s.width) // 2, int(H * 0.30) if dentro else int(H * 0.39) - s.height))
            else:
                s = subtitulo(g, t, 1050, 56)
                # 23-nov-2026: en un cruce del largo el globo derecho va ABAJO, donde el subtítulo: el puente se ve solo
                # mientras ese globo no ha entrado y se retira antes; si ya está (segunda cita del mismo), va sin subtítulo
                grupo = next((gr for k, gr in self.grupos.items() if self.cruce.get(k)
                              and min(x["t0"] for x in gr) < g["t0"] < max(x["t0"] for x in gr)), None)
                if grupo is None:
                    fr.alpha_composite(s, (int(W * 0.40), H - s.height - 80))
                elif not any(x["lado"] == "der" and x["t0"] < g["t0"] for x in grupo) and t <= g["t1"] - 0.3:
                    fr.alpha_composite(s, (int(W * 0.40), H - s.height - 80))
        return fr

    def _vista(self, f, t):
        im = self.fondos[f]
        W, H = self.W, self.H
        z = 1.0                    # 23-nov-2026 (el usuario): fondo ESTÁTICO, sin zoom (el lento acercamiento saltaba cada 20 s)
        fw, fh = int(W * z), int(H * z)
        k = min(im.width / fw, im.height / fh)
        fw, fh = int(fw * min(1, k)), int(fh * min(1, k))
        fx, fy = (im.width - fw) // 2, (im.height - fh) // 2
        return im.crop((fx, fy, fx + fw, fy + fh)).resize((W, H), Image.BILINEAR)

    def _bocadillos(self, fr, t):
        W, H = self.W, self.H
        for g in self.tr:
            if g["tipo"] != "Q":
                continue
            fin_g = max(x["t1"] for x in self.grupos[g["grupo"]]) + 0.05
            sig = next((x for x in self.grupos[g["grupo"]] if x["t0"] > g["t0"] and x["lado"] == g["lado"]), None)
            if sig is not None:                       # la misma persona dice otra cita: este bocadillo se va antes
                fin_g = min(fin_g, sig["t0"] - 0.55)
                # 26-nov-2026 (fallo real: «Asalto tres, González otra vez:» pisaba el globo anterior de González): en
                # vertical, el globo derecho está donde va el subtítulo del puente; si hay un puente antes de su siguiente
                # cita, el globo se ha ido ANTES de que empiece el puente
                pu = next((x for x in self.tr if x.get("puente") and g["t1"] <= x["t0"] < sig["t0"]), None)
                if pu is not None and self.vertical and g["lado"] == "der":
                    fin_g = min(fin_g, pu["t0"] - 0.32)
            otro = next((x for x in self.tr if x["tipo"] == "Q" and x["t0"] > g["t0"] and x["grupo"] != g["grupo"]), None)
            if otro is not None:                      # 21-nov: el globo de otra cita no entra hasta que este se ha ido
                fin_g = min(fin_g, otro["t0"] - 0.6)
            a = min(ease((t - (g["t0"] - 0.25)) / 0.35), 1 - ease((t - fin_g) / 0.3))
            if a <= 0.01:
                continue
            activo = g["t0"] - 0.3 <= t <= g["t1"] + 0.3
            cruce = self.cruce.get(g["grupo"]) and all(self.figs.get(x["quien"]) is not None for x in self.grupos[g["grupo"]])
            nombre, cargo, medio = g["quien"], self.cargos.get(g["quien"], ""), g.get("medio") or self.medios.get(g["quien"], "")
            sin_fig = self.figs.get(g["quien"]) is None
            if self.vertical:
                if cruce:
                    fx_ = self._pos(g["quien"], g["lado"], True)           # centro del personaje que habla
                    cola = fx_ - 40 if g["lado"] == "izq" else -(W - 40 - fx_)
                    c = tarjeta(g, t, activo, "abajo", nombre, cargo, medio, W - 200, 46, max_h=int(H * 0.165), cola_dx=cola)
                    x, y = (40, int(H * 0.125)) if g["lado"] == "izq" else (W - 40 - c.width, int(H * 0.125) + int(H * 0.175))
                else:
                    c = tarjeta(g, t, activo, "abajo", nombre, cargo, medio, W - 180, 56, max_h=int(H * 0.27))
                    x, y = (W - c.width) // 2, int(H * 0.40) - c.height
            else:
                if cruce:
                    lados = {x["lado"]: x["quien"] for x in self.grupos[g["grupo"]]}
                    hx0 = int(W * 0.14) + self.figs[lados["izq"]].width // 2 + 10
                    hx1 = int(W * 0.86) - self.figs[lados["der"]].width // 2 - 10
                    c = tarjeta(g, t, activo, g["lado"], nombre, cargo, medio, hx1 - hx0 - 130, 46, max_h=(H - 210) // 2)
                    # 25-nov-2026: el globo izquierdo empieza bajo el rótulo de la sección (antes, a 50 px, lo pisaba)
                    x, y = (hx0, 108) if g["lado"] == "izq" else (hx1 - c.width, H - c.height - 50)
                else:
                    c = tarjeta(g, t, activo, "izq", nombre, cargo, medio, 860 if sin_fig else 760, 50,
                                max_h=int(H * 0.62))
                    x, y = int(W * 0.345), (H - c.height) // 2 - 60
            if a < 1:
                c = c.copy(); c.putalpha(c.getchannel("A").point(lambda v, a=a: int(v * a)))
            dx = int((1 - a) * (-40 if g["lado"] == "izq" else 40))
            fr.alpha_composite(c, (x + dx, y))


def _render(esc, total, salida, audio, encabezado=None, nproc=None):
    """Dibuja los fotogramas en paralelo (trozos) y une con el audio."""
    import imageio_ffmpeg
    import multiprocessing as mp
    FF = imageio_ffmpeg.get_ffmpeg_exe()
    tmp = Path(salida).parent / (Path(salida).stem + "_tmp")
    tmp.mkdir(exist_ok=True)
    nfr = int((total + 0.3) * FPS)
    nproc = nproc or max(1, min(4, (os.cpu_count() or 2) - 1))
    bordes = [nfr * k // nproc for k in range(nproc + 1)]

    def trozo(k):
        a, b = bordes[k], bordes[k + 1]
        ff = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                               f"{esc.W}x{esc.H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast",
                               "-crf", "15", "-pix_fmt", "yuv420p", str(tmp / f"t{k}.mp4")], stdin=subprocess.PIPE)
        for n in range(a, b):
            fr = esc.cuadro(n / FPS)
            if encabezado:
                encabezado(fr, n / FPS)
            ff.stdin.write(fr.convert("RGB").tobytes())
            if k == 0 and (n - a) % (FPS * 15) == 0:
                print(f"  fotograma {(n - a) * nproc}/{nfr} aprox.", flush=True)
        ff.stdin.close()
        return ff.wait()

    ctx = mp.get_context("fork")

    def hijo(k):
        try:
            os._exit(trozo(k))
        except Exception:
            import traceback
            traceback.print_exc(); os._exit(1)
    ps = [ctx.Process(target=hijo, args=(k,)) for k in range(nproc)]
    for p in ps:
        p.start()
    for p in ps:
        p.join()
    if any(p.exitcode for p in ps):
        raise RuntimeError("falló un trozo del render")
    (tmp / "lista.txt").write_text("".join(f"file 't{k}.mp4'\n" for k in range(nproc)), encoding="utf-8")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(tmp / "lista.txt"),
                    "-i", str(audio), "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",   # 23-nov: más nitidez
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k", "-shortest",
                    str(salida)], check=True)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)


def _cargos():
    try:
        import render_ambiente as RA
        return {n: re.sub(r"\s*\([^)]*\)", "", (c or "").split(";")[0]).strip() for n, c in RA._conocidas()}, \
            RA._conocidas()                            # 22-nov: sin las notas internas tras «;» (salían en el globo)
    except Exception:
        return {}, []


def _cargo_de(nombre, cargos):
    if nombre in cargos:
        return cargos[nombre]
    ape = _n(nombre).split()[-1] if nombre else ""
    return next((c for n, c in cargos.items() if _n(n).split()[-1:] == [ape]), "")


def _fuente_x(dia):
    """22-nov-2026: si una cita sale literal de un tuit de cuenta oficial (redes.json), su globo dice «X (@cuenta)»:
    es la fuente primaria. Devuelve una función cita -> fuente o None."""
    try:
        tuits = [x for x in json.loads((dia / "redes.json").read_text(encoding="utf-8")) if "(@" in x.get("quien", "")]
    except (OSError, ValueError):
        tuits = []
    # solo el texto PROPIO del tuit: el tuit que cita va entre «[cita a @…]» y es de otro (fallo real del 22-nov: la frase de
    # Sánchez salió «según X (@Mtelladof)» porque Tellado citaba su tuit)
    textos = [(_n(x["texto"].split(" [cita a @")[0]), "X (@" + x["quien"].split("(@")[1].rstrip(")") + ")") for x in tuits]

    def de(cita):
        c = _n(cita)
        return next((f for t, f in textos if len(c) > 12 and c in t), None)
    return de


# ---------------------------------------------------------------- Short (vertical)
def _cifra_img(pares):
    """Rótulo de cifra (26-nov-2026, idea del TikTok del debate a ocho): «8 ATRILES» en una línea, número en amarillo;
    con varios pares, uno detrás de otro («4 MUJERES  4 HOMBRES»). Va en el hueco entre el subtítulo (que acaba en
    0,39 H) y la cabeza del presentador (0,46 H): 120 px de alto."""
    fn, fr_ = fuente("Inter-Black.ttf", 104), fuente("Inter-Black.ttf", 54)
    medidas = [(int(fn.getlength(c)), int(fr_.getlength(r))) for c, r in pares]
    w = 34 + sum(wn + 30 + wr + 16 for wn, wr in medidas) + 44 * (len(medidas) - 1) + 30
    c = Image.new("RGBA", (w, 120), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rounded_rectangle((0, 0, w - 1, 119), 26, fill=(10, 14, 28, 228))
    x = 34
    for (cifra, rotulo), (wn, wr) in zip(pares, medidas):
        d.text((x, -12), cifra, font=fn, fill=AMARILLO + (255,))
        d.rounded_rectangle((x + wn + 12, 26, x + wn + 30 + wr + 16, 94), 14, fill=ROJO + (255,))
        d.text((x + wn + 30, 28), rotulo, font=fr_, fill=(255, 255, 255, 255))
        x += wn + 30 + wr + 16 + 44
    return c


def _cifras(lista, tr):
    """[(t0, t1, imagen)]: cada cifra sale cuando el presentador dice su palabra «cuando» y dura hasta 2,4 s, sin salir
    de su tramo (en los tramos de cita hay globo y no cabe). Formato en el JSON del Short:
    "cifras": [{"cuando": "atriles", "cifra": "8", "rotulo": "ATRILES"}] o, con varios datos seguidos en un solo rótulo,
    {"cuando": "cuatro mujeres", "pares": [["4", "mujeres"], ["4", "hombres"]]}."""
    out = []
    for c in lista:
        clave = _n(c.get("cuando", "")).split()
        for g in tr:
            if g["tipo"] != "P" or g.get("cierre") or not clave:
                continue
            pal = [(_n(w), a, b) for w, a, b in g.get("pal", [])]
            hit = next((a for k, (w, a, b) in enumerate(pal)
                        if [x for x, _, _ in pal[k:k + len(clave)]] == clave), None)
            if hit is not None:
                pares = c.get("pares") or [[c.get("cifra", ""), c.get("rotulo", "")]]
                out.append((max(g["t0"], hit - 0.15), min(g["t1"] + 0.1, hit + 2.4),
                            _cifra_img([(str(a), str(b).upper()) for a, b in pares])))
                break
    # nunca dos a la vez: la siguiente espera a que se vaya la anterior
    out.sort(key=lambda x: x[0])
    for k in range(1, len(out)):
        if out[k][0] < out[k - 1][1] + 0.1:
            out[k - 1] = (out[k - 1][0], out[k][0] - 0.1, out[k - 1][2])
    return [x for x in out if x[1] - x[0] > 0.6]


def short(fecha, n):
    import musica
    import short as SH
    dia = RAIZ / "dia" / fecha
    S = json.loads((dia / "shorts" / f"short_{n}.json").read_text(encoding="utf-8"))
    fx = _fuente_x(dia)
    tmp = dia / "shorts" / f"tmp_pres_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    import coletillas as COL                           # 24-nov-2026: coletillas sin «¡!» (la voz no cambia de tono)
    texto = COL.sin_exclamaciones(S["voz"])
    preg = (S.get("pregunta") or "").strip()
    k_fin = texto.find(preg) if preg and preg in texto else texto.find("Te leo en comentarios")
    cuerpo, cierre = (texto[:k_fin].strip(), texto[k_fin:].strip()) if k_fin > 0 else (texto, "")
    cargos, conocidas = _cargos()
    quien = S.get("quien", "")
    medios = {quien: S.get("fuente", "")}
    citas_medio = {(_n(f.get("cita"))): f.get("fuente", "") for f in S.get("frases") or []}
    medio_cita = {_n(c): f for c, f in (S.get("fuentes_citas") or {}).items()}   # 22-nov: la fuente de cada cita (cruces)
    rep = S.get("replica") or {}
    def quien_de(c):
        nc = _n(c)
        if rep and _n(rep.get("cita")) == nc:
            return rep.get("quien")
        if nc in citas_medio or _n(S.get("cita")) == nc:      # sus frases (Shorts de «mejores frases») y su cita
            return quien
        return quien_cita.get(nc)                             # 23-nov-2026: «quien_citas» {cita: persona} del guion
    quien_cita = {_n(c): q for c, q in (S.get("quien_citas") or {}).items()}
    tr = tramos_de(cuerpo, quien, conocidas, quien_de=quien_de)
    for g in tr:
        if g["tipo"] == "Q":
            g["medio"] = medio_cita.get(_n(g["cita"])) or fx(g["cita"]) or \
                citas_medio.get(_n(g["cita"]), medios.get(g["quien"], ""))
            cargos.setdefault(g["quien"], _cargo_de(g["quien"], cargos) or (S.get("cargo") if g["quien"] == quien else
                                                                            rep.get("cargo", "")))
    if cierre:
        tr.append({"tipo": "P", "di": cierre, "cierre": True})
    faltan = sin_imagen(tr)
    _ordena_lados(tr)
    total, env = locuta_tramos(tr, tmp)
    total += 1.2
    cifras = _cifras(S.get("cifras") or [], tr)
    fondos, _, _ = catalogo()
    fondo = elige_fondos([f"{S.get('titulo', '')}. {S.get('contexto', '')}"], fondos, tmp / "fondo.json")[0]
    esc = Escena(tr, total, env, 1080, 1920, [fondo] * len(tr), cargos, medios, vertical=True)
    dibujados = sorted(q for q, f in esc.figs.items() if f is not None)
    if dibujados:                                      # personas reales ilustradas: subir.py lo declara (contenido sintético)
        S["sintetico"], S["personajes"] = True, dibujados
        (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    cab = SH._cabecera(fecha, S.get("categoria", ""))
    kick = SH._kicker((S.get("kicker") or quien).upper())
    t_fin = next((g["t0"] for g in tr if g.get("cierre")), total)
    cortes = [g["t0"] - 0.3 for g in tr[1:] if g["tipo"] == "Q" or tr[tr.index(g) - 1]["tipo"] == "Q"]
    # 22-nov-2026 (el usuario): los personajes y el presentador entran y salen SIN efectos de sonido
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.2, [], efectos=(), con_sintonia=False)
    f_fuente = fuente("Inter-SemiBold.ttf", 26)

    def encabezado(fr, t):
        if t >= t_fin:
            capa = Image.new("RGBA", fr.size, (8, 12, 24, int(200 * ease((t - t_fin) / 0.3))))
            fr.alpha_composite(capa)
            SH._cierre(fr, t - t_fin, preg or "¿Qué opinas?")
        fr.alpha_composite(cab, (0, 0))
        if t < t_fin:
            fr.alpha_composite(kick, (50, 160))
        for c0, c1, im in cifras:                       # 26-nov-2026: la cifra del dato, grande, mientras se dice
            if c0 <= t <= c1:
                a_ = min(1.0, (t - c0) / 0.2, (c1 - t) / 0.2)
                sc = 0.85 + 0.15 * ease(min(1.0, (t - c0) / 0.25))
                im2 = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))))
                if a_ < 1:
                    im2.putalpha(im2.getchannel("A").point(lambda v, a_=a_: int(v * a_)))
                fr.alpha_composite(im2, ((1080 - im2.width) // 2, int(1920 * 0.39) + 10 + (im.height - im2.height) // 2))
        d = ImageDraw.Draw(fr)
        d.rectangle([0, 1920 - 12, int(1080 * min(1.0, t / total)), 1920], fill=AMARILLO)

    out = dia / "shorts" / f"short_{n}.mp4"
    _render(esc, total, out, tmp / "audio.wav", encabezado)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    avisa_sin_imagen(fecha, f"Short {n}", faltan)
    try:                                                # 23-nov-2026: tramos para el informe de retención (retencion.py)
        cl = []
        for k_, g in enumerate(tr):
            c_ = ("cierre" if g.get("cierre") else "gancho" if k_ == 0 and g["tipo"] == "Q" else "cita" if g["tipo"] == "Q"
                  else "puente" if g.get("puente") else "presentador")
            cl.append({"clase": c_, "t0": round(g["t0"], 2), "t1": round(g["t1"], 2), "quien": g.get("quien", ""),
                       "di": g["di"][:120]})
        (dia / "shorts" / f"short_{n}_tramos.json").write_text(json.dumps({"total": round(total, 2), "tramos": cl},
                                                                          ensure_ascii=False, indent=1), encoding="utf-8")
    except Exception as e:
        print(f"(tramos sin guardar: {type(e).__name__})")
    print(f"SHORT {n} (presentador): {total:.1f} s -> {out} · " +
          " | ".join(f"{g['tipo']}{'·' + g['quien'].split()[-1] if g['tipo'] == 'Q' else ''} {g['t0']:.1f}" for g in tr))


# ---------------------------------------------------------------- Largo (horizontal)
def largo(fecha):
    import musica
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    fx = _fuente_x(dia)
    secs = [s for s in G["secciones"] if not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", []))]
    tmp = dia / "tmp_presentador"
    tmp.mkdir(exist_ok=True)
    cargos, conocidas = _cargos()
    tr, sec_de = [], []
    for i, s in enumerate(secs):
        items = [it for p in s["pasos"] for it in ((p.get("ve") or {}).get("items") or []) if isinstance(it, dict)]
        ve_citas = [(p.get("ve") or {}) for p in s["pasos"] if isinstance((p.get("ve") or {}).get("cita"), str)]
        ve_citas += [p["ve"]["persona"] for p in s["pasos"] if isinstance((p.get("ve") or {}).get("persona"), dict)
                     and isinstance(p["ve"]["persona"].get("cita"), str)]   # ficha {"tipo": "persona", "persona": {...}}
        fichas = [it for it in items + ve_citas if it.get("cita")]

        def quien_de(c, fichas=fichas):
            nc = _n(c)
            for it in fichas:
                ni = _n(it["cita"])
                if nc and ni and (nc in ni or ni in nc):
                    q = it.get("nombre") or it.get("persona")
                    q = q.get("nombre") if isinstance(q, dict) else q
                    return q if isinstance(q, str) and q else None
            return None
        import coletillas as COL
        texto = COL.sin_exclamaciones(" ".join(p.get("di", "") for p in s["pasos"]).strip())
        defecto = next((p["ve"].get("persona") for p in s["pasos"] if (p.get("ve") or {}).get("persona")), "")
        if isinstance(defecto, dict):
            defecto = defecto.get("nombre") or defecto.get("persona") or ""
        defecto = defecto if isinstance(defecto, str) else ""
        # 20-nov-2026 (fallo real: «Es un dolor…» de Sánchez salió con el rótulo de Feijóo, el protagonista de la pieza):
        # en el largo NUNCA se atribuye una cita por defecto; si no consta quién la dice, no sale nadie.
        trs = tramos_de(texto, "", conocidas, quien_de=quien_de)
        for g in trs:
            if g["tipo"] == "Q":
                it = next((x for x in fichas if _n(x["cita"]) and (_n(g["cita"]) in _n(x["cita"]) or _n(x["cita"]) in _n(g["cita"]))), {})
                g["medio"] = fx(g["cita"]) or \
                    re.sub(r"^según\s+", "", it.get("medio") or (s.get("fuentes") or [""])[0] or "", flags=re.I)
                if it.get("cargo"):
                    cargos.setdefault(g["quien"], re.sub(r"\s*\([^)]*\)", "", it["cargo"]).strip())
                cargos.setdefault(g["quien"], _cargo_de(g["quien"], cargos))
        if trs:
            trs[-1]["seccion_fin"] = True
        tr += trs
        sec_de += [i] * len(trs)
    canon = {}
    for s_ in secs:
        for p in s_["pasos"]:
            for it in ((p.get("ve") or {}).get("items") or []) + [p.get("ve") or {}]:
                nm = it.get("nombre") if isinstance(it, dict) else None
                if isinstance(nm, str) and nm:
                    canon.setdefault(_n(nm), nm)
    for g in tr:
        if g["tipo"] == "Q":
            g["quien"] = canon.get(_n(g["quien"]), g["quien"])
            cargos.setdefault(g["quien"], _cargo_de(g["quien"], cargos))
    faltan = sin_imagen(tr)
    _ordena_lados(tr)
    total, env = locuta_tramos(tr, tmp)
    total += 1.0
    fondos, _, _ = catalogo()
    textos = [s.get("titulo", "") + ". " + " ".join(p.get("di", "") for p in s["pasos"]) for s in secs]
    f_sec = elige_fondos(textos, fondos, dia / "fondos_elegidos.json")
    esc = Escena(tr, total, env, 1920, 1080, [f_sec[k] for k in sec_de], cargos, {}, vertical=False)
    (dia / "personajes_presentador.json").write_text(json.dumps(sorted(q for q, f in esc.figs.items() if f is not None),
                                                                ensure_ascii=False), encoding="utf-8")
    t_sec = {}
    for g, k in zip(tr, sec_de):
        t_sec.setdefault(k, g["t0"])
    cortes = [t_sec[k] for k in sorted(t_sec)[1:]] + [g["t0"] - 0.3 for g in tr if g["tipo"] == "Q"]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.0, [], efectos=(),   # sin efectos al entrar/salir
                  con_sintonia=True)
    fl, ft = fuente("Inter-Black.ttf", 34), fuente("Inter-Black.ttf", 30)
    lw = int(fl.getlength("EL HOYFORMATIVO"))

    def encabezado(fr, t):
        d = ImageDraw.Draw(fr)
        d.rounded_rectangle((1920 - lw - 76, 36, 1920 - 40, 96), 14, fill=ROJO + (235,))
        d.text((1920 - lw - 58, 44), "EL HOYFORMATIVO", font=fl, fill="white")
        k = max([s for s, t0 in t_sec.items() if t0 - 0.3 <= t] or [0])
        tit = (secs[k].get("titulo") or "").upper()[:48]
        if tit:
            w = int(ft.getlength(tit))
            d.rounded_rectangle((40, 40, 40 + w + 40, 92), 12, fill=(10, 14, 28, 210))
            d.text((60, 47), tit, font=ft, fill=AMARILLO)

    # tiempos de cada sección (capítulos de la descripción)
    (dia / "capitulos.json").write_text(json.dumps([{"t": round(t_sec[k], 1), "titulo": secs[k].get("titulo", "")}
                                                     for k in sorted(t_sec)], ensure_ascii=False), encoding="utf-8")
    out = dia / "episodio.mp4"
    t_ini = time.time()
    _render(esc, total, out, tmp / "audio.wav", encabezado)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    avisa_sin_imagen(fecha, "Vídeo largo", faltan)
    print(f"LARGO (presentador): {total:.1f} s -> {out} en {(time.time() - t_ini) / 60:.1f} min")


if __name__ == "__main__":
    if sys.argv[1] == "catalogo":
        fo, po, pl = catalogo()
        print(f"fondos: {[f.stem for f in fo]}\nposes del presentador: {len(po)}\npolíticos: "
              f"{ {k: [p.name for p in v] for k, v in pl.items()} }")
    elif sys.argv[2] == "largo":
        largo(sys.argv[1])
    else:
        short(sys.argv[1], int(sys.argv[2]))
