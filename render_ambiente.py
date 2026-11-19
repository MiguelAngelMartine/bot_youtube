"""RENDER ESTILO AMBIENTE (13-nov-2026, aprobado por el usuario): escenas de línea clara ANIMADAS a pantalla completa,
SIN personajes en primer plano, acordes a lo que se narra, con la cabecera EH y el recuadro de la frase sincronizado.
La escena cambia cuando empieza la frase que la describe. Animación: LTX (animar_ia) donde hay cuota; si no, cámara 2,5D
(motion_comic). Reemplaza al estilo anterior (panel + fondo borroso) para los Shorts; base del rediseño del vídeo largo.
Uso: python render_ambiente.py AAAA-MM-DD N   (Short N del día)"""
from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path

import cv2
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

import animar_ia
import corto as C
import episodio as E
import genera_video as V1
import genera_video2 as G2
import ia_vinetas as IA
import motion_comic as MC
import musica
import short as SH
import voz
from genera_video2 import AMARILLO, BLANCO, ROJO, fuente

AN, AL, FPS = 1080, 1920, 30
RAIZ = Path(__file__).parent


def _escena_viva(ruta_img, movimiento, animar, w=AN, h=AL):
    """Devuelve (frames|None, fps, base). Si animar y hay cuota, clip LTX; si no, None (se usa motion_comic sobre `base`)."""
    base = ImageOps.fit(Image.open(ruta_img).convert("RGB"), (int(w * 1.12), int(h * 1.12)), Image.LANCZOS,
                        centering=(0.5, 0.42))
    if os.environ.get("EH_SIN_LTX"):   # LTX (animar_ia) a veces degenera el clip en caras/logos inventados: solo cámara 2,5D
        animar = False
    if animar:
        try:
            mp4 = animar_ia.clip(ruta_img, movimiento)
            if mp4:
                cap, frs = cv2.VideoCapture(str(mp4)), []
                while True:
                    ok, fr_ = cap.read()
                    if not ok:
                        break
                    frs.append(Image.fromarray(cv2.cvtColor(fr_, cv2.COLOR_BGR2RGB)))
                if frs:
                    return frs, (cap.get(5) or 24), base
        except Exception as e:
            print(f"  (sin animación LTX para {Path(ruta_img).name}: {type(e).__name__})")
    return None, 0, base


def _vista(esc, t_scene, dur_scene, k, w=AN, h=AL):
    """La escena a pantalla completa en el instante t_scene (desde que entra). LTX si lo hay; si no, cámara 2,5D."""
    frs, cfps, base = esc
    if frs:
        j = int(t_scene * cfps)
        if j < len(frs):
            v = ImageOps.fit(frs[j], (w, h), Image.BILINEAR)
        else:                                              # sin marcha atrás: el último fotograma con acercamiento lento
            z = 1.0 + 0.03 * min(t_scene - len(frs) / cfps, 5.0)
            u = frs[-1]
            cw, ch = int(u.width / z), int(u.height / z)
            u = u.crop(((u.width - cw) // 2, (u.height - ch) // 2, (u.width + cw) // 2, (u.height + ch) // 2))
            v = ImageOps.fit(u, (w, h), Image.BILINEAR)
        return v.convert("RGBA")
    return MC.anima(base, None, t_scene, w, h, semilla=k, dur=dur_scene + 2).convert("RGBA")


FALLBACK_ESC = ["the neoclassical facade of the Spanish Congress of Deputies with its lions and columns, empty street",
                "the facade of the Spanish Senate building in Madrid with Spanish flags, sober daylight",
                "an empty parliamentary chamber with curved rows of seats and a speaker's podium",
                "a modern conference centre entrance with glass and steel, Spanish and European flags",
                "the facade of a Spanish political party headquarters building with flags, empty street in front",
                "an empty government press room with a podium, microphones and a Spanish flag"]
# 17-nov-2026 (usuario): fondos de sitios relacionados con la política o paisajes urbanos sobrios; la búsqueda en la biblioteca
# se inclina hacia lo institucional añadiendo estas palabras a la consulta.
_LIB_POLITICA = ("parliament congress senate government palace ministry headquarters party city hall town hall "
                 "chamber podium press conference institutional flag")


def escenas_ambiente(S, n_esc=5):
    """Planos de AMBIENTE (lugares, objetos, símbolos) sin personas, acordes al tema del Short. Gemini; si falla, genéricos."""
    try:
        import gem
        base = f"Tema: {S.get('quien', '')}: «{S.get('cita', '')}». Contexto: {S.get('contexto', '')}"
        pr = (f"Para un vídeo de política española en estilo viñeta de línea clara, describe EN INGLÉS {n_esc} PLANOS DE "
              "AMBIENTE (establishing shots) relacionados con el tema, SIN personas en primer plano y SIN caras, SIEMPRE de "
              "LUGARES RELACIONADOS CON LA POLÍTICA (17-nov-2026, el usuario): el Senado, el Congreso de los Diputados, la "
              "Moncloa, palacios de congresos, sedes de partidos, parlamentos autonómicos, ayuntamientos, ministerios, salas "
              "de prensa, hemiciclos vacíos, atriles y escenarios de mitin, urnas, o paisajes urbanos SOBRIOS (avenidas y "
              "plazas institucionales). NUNCA playas, puertos, terrazas de bar, mercados ni calles turísticas o pintorescas. "
              "Cada uno una frase concreta y visual, sin texto "
              "legible. Responde SOLO JSON: {\"escenas\": [\"...\"]}.\n\n" + base)
        r = gem.pide(pr, como_json=True) or {}
        esc = [e.strip() for e in (r.get("escenas") or []) if isinstance(e, str) and e.strip()]
        if len(esc) >= 2:
            return esc[:n_esc]
    except Exception as e:
        print(f"  (escenas de ambiente por defecto: {type(e).__name__})")
    return FALLBACK_ESC[:n_esc]


# ---- Polaroid de la persona que dice la frase, integrada en el fondo cómic (13-nov-2026, aprobado por el usuario) ----
import colorsys


def _acento(crop):
    """Color de acento en armonía con el fondo: el dominante del recorte, más saturado y con cuerpo."""
    c = crop.convert("RGB").resize((1, 1), Image.LANCZOS).getpixel((0, 0))
    h, s, v = colorsys.rgb_to_hsv(*[x / 255 for x in c])
    s = min(1.0, s * 1.5 + 0.25)
    v = min(1.0, max(0.45, v * 0.95))
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return (int(r * 255), int(g * 255), int(b * 255))


def _nombre_corto(n):
    """Nombre que cabe en la barra/Polaroid: «Luiz Inácio Lula da Silva» -> «Lula da Silva»."""
    w = (n or "").split()
    if len(n or "") <= 20 or len(w) <= 2:
        return n
    return " ".join(w[-3:] if w[-2].islower() else w[-2:])


def polaroid_armonica(foto, nombre, cargo, credito, ancho, acento, giro=-3):
    nombre = _nombre_corto(nombre)
    """Polaroid con la FOTO REAL de quien dice la frase, marco en armonía con el fondo (color de acento). Sin celo, a doble
    tamaño que en los primeros vídeos. Devuelve RGBA ya inclinada (`giro` grados)."""
    alto_f = int(ancho * 0.80)
    im = Image.new("RGBA", (ancho + 60, alto_f + 210), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([26, 34, ancho + 42, alto_f + 206], radius=14, fill=(0, 0, 0, 90))          # sombra
    d.rounded_rectangle([16, 24, ancho + 32, alto_f + 198], radius=12, fill=(250, 248, 243, 255))   # tarjeta hueso
    d.rounded_rectangle([16, 24, ancho + 32, alto_f + 198], radius=12, outline=acento + (255,), width=10)  # marco de acento
    f = Image.open(foto).convert("RGB")
    rr = max((ancho - 20) / f.width, (alto_f - 20) / f.height)
    f = f.resize((math.ceil(f.width * rr), math.ceil(f.height * rr)), Image.LANCZOS)
    x0, y0 = (f.width - (ancho - 20)) // 2, int((f.height - (alto_f - 20)) * 0.22)
    d.rectangle([34, 42, 34 + ancho - 20, 42 + alto_f - 20], fill=acento + (255,))                  # orla de acento
    im.paste(f.crop((x0, y0, x0 + ancho - 20, y0 + alto_f - 20)), (38, 46))
    fn = fuente("Inter-Black.ttf", 52)
    while fn.getlength((nombre or "").upper()) > ancho - 10 and fn.size > 28:
        fn = fuente("Inter-Black.ttf", fn.size - 2)
    d.text(((ancho + 48) / 2, alto_f + 62), (nombre or "").upper(), font=fn, fill=(20, 22, 28, 255), anchor="mt")
    if cargo:
        d.text(((ancho + 48) / 2, alto_f + 124), cargo, font=fuente("Inter-SemiBold.ttf", 32), fill=acento + (255,), anchor="mt")
    d.text(((ancho + 48) / 2, alto_f + 170), (credito or "Foto de archivo")[:46], font=fuente("Inter-Regular.ttf", 20),
           fill=(140, 140, 150, 255), anchor="mt")
    return im.rotate(giro, expand=True, resample=Image.BICUBIC)


_ACC = str.maketrans("áéíóúüÁÉÍÓÚÜàèìòùÀÈÌÒÙäëïöÄËÏÖñÑçÇ", "aeiouuAEIOUUaeiouAEIOUaeioAEIOnNcC")


def _norm(s):
    return (s or "").translate(_ACC).lower()                # sin acentos, misma longitud (los índices siguen valiendo)


def _conocidas():
    """Personas conocidas (de archivo/personas.json): [(nombre, cargo)]. Para atribuir cada cita a quien la dice."""
    import json
    f = RAIZ / "archivo" / "personas.json"
    p = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    return [(n, (v or {}).get("cargo", "")) for n, v in p.items()]


_SPEAK = (r"(?:dice|dijo|asegura|afirma|senala|responde|replica|contesta|espeta|suelta|lanza|acusa|carga|avisa|advierte|"
          r"reprocha|insiste|remata|sentencia|declara|apunta|zanja|clama|exige|proclama|ironiza|anuncia|defiende|critica|"
          r"tacha|llama|ataca|pregunta|recuerda|subraya|denuncia|celebra|lamenta|admite|reconoce|pide|exclama|grita|habla|hablan|escribe|expresa)")

# palabras en mayúscula que NO son nombres de persona (para no confundir «España: «...»» con un hablante)
_NO_NOMBRE = {"El", "La", "Los", "Las", "Un", "Una", "Lo", "Y", "O", "Pero", "En", "Con", "Sin", "Por", "Para", "Según",
              "Hoy", "Ayer", "Mañana", "Ahora", "Mientras", "Así", "Además", "También", "No", "Sí", "Esto", "Eso", "Esa",
              "Este", "Esta", "Ese", "Aquí", "Allí", "Cuando", "Donde", "Mira", "Ojo", "Atención", "España", "Madrid",
              "Cataluña", "Gobierno", "Congreso", "Senado", "Moncloa", "Marruecos", "Europa", "Justicia", "Estado",
              "Resulta", "Toma", "Vaya", "Agárrate", "Encima", "Luego", "Total", "Claro", "Bueno", "Pues", "Vamos"}
_VERBOS_HABLA = set("dice dijo asegura afirma senala responde replica contesta espeta suelta lanza acusa carga avisa "
                    "advierte reprocha insiste remata sentencia declara apunta zanja clama exige proclama ironiza anuncia "
                    "defiende critica tacha llama ataca pregunta recuerda subraya denuncia celebra lamenta admite reconoce "
                    "pide exclama grita abre habla hablan".split())


def _citas_timeline(texto, c0, btxt, T, conocidas, quien_def):
    """Línea de tiempo de las CITAS («...») del bloque: (t_ini, t_fin, persona). La persona es QUIEN DICE la cita: por
    defecto el hablante declarado (quien_def); solo se asigna a otro apellido conocido si de verdad es quien habla (verbo de
    habla cerca, o pegado a la cita), nunca el DESTINATARIO («a/contra Fulano: ...»). Citas cortas se alargan; seguidas de la
    misma persona, se funden."""
    import re as _re
    nbt = _norm(btxt)
    nq = _re.sub(r"«[^»]*»", lambda x: " " * len(x.group()), nbt)   # sin el interior de las citas (para hallar la frase)
    apes = [(_norm(n.split()[-1]), n) for n, _ in conocidas if len(n.split()[-1]) >= 4]
    # 19-nov-2026 (fallo real: Koldo García en la cita de José Ignacio García): si varios conocidos comparten apellido, solo
    # vale el que tiene su NOMBRE DE PILA justo delante del apellido en el texto.
    from collections import Counter as _Ct
    _comp = _Ct(a for a, _ in apes)

    def _pila_ok(n, p):
        ape = _norm(n.split()[-1])
        if _comp[ape] < 2:
            return True
        pila = {_norm(w) for w in n.split()[:-1]}
        antes_ = nbt[max(0, p - 30):p].split()[-3:]
        return bool(pila & set(antes_))

    def _destinatario(p):   # el apellido es el destinatario del ataque, no quien habla («a/contra Pedro Sánchez»)
        return bool(_re.search(r"\b(?:a|al|contra|hacia|sobre|para|que)\s+(?:\w+\s+){0,2}$", nbt[max(0, p - 26):p]))

    qs = []
    for m in _re.finditer(r"«([^»]{3,})»", btxt):
        a, b = T.en(c0 + m.start()), T.en(c0 + m.end())
        best, cand, candpos = quien_def, None, -1
        # 15-nov: solo vale un hablante de LA MISMA FRASE que la cita (sin contar el interior de otras citas)
        ini_f = max([nq.rfind(x, 0, m.start()) for x in ".!?;"] + [-1]) + 1
        for ape, n in apes:
            for mm in _re.finditer(r"\b" + _re.escape(ape) + r"\b", nbt[:m.start()]):
                p = mm.start()
                if p < ini_f or _destinatario(p) or not _pila_ok(n, p):
                    continue
                despues = nbt[mm.end():mm.end() + 22]
                antes = nbt[max(0, p - 18):p]
                hablante = (_re.match(r"\s*(?:\w+\s+){0,2}" + _SPEAK + r"\b", despues) is not None   # «Fulano … responde»
                            or _re.search(r"\b(?:" + _SPEAK + r"|segun)\s+$", antes) is not None       # «responde/según Fulano»
                            or (m.start() - mm.end()) <= 4                                             # «Fulano: «...»»
                            or _re.search(r"\b" + _SPEAK + r"\b", nq[mm.end():m.start()]) is not None)  # verbo de habla en la frase
                if hablante and p > candpos:
                    candpos, cand = p, n
        if cand:
            best = cand
        else:
            # Sin hablante conocido identificado: si en la frase de la cita hay OTRO nombre propio como SUJETO (un ponente no
            # registrado, p. ej. en «La campaña en frases»), NO se pone la foto del hablante por defecto (mejor ninguna que la
            # equivocada). Se ignoran los nombres que son destinatario («a/contra/sobre Fulano»).
            ini = max([btxt.rfind(x, 0, m.start()) for x in ".!?»"] + [-1]) + 1
            if _re.search(r"\b(?:PSOE|PP|PNV|Vox|Sumar|Junts|ERC|Podemos|Bildu|Gobierno)\b", btxt[max(ini_f, ini):m.start()]):
                best = ""      # la dice un partido/institución, no la persona por defecto
            ape_def = _norm(quien_def.split()[-1]) if quien_def else ""
            for mm in _re.finditer(r"\b([A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,})\b", btxt[ini:m.start()]):
                w = mm.group(1)
                if w in _NO_NOMBRE or _norm(w) in _VERBOS_HABLA or _norm(w) == ape_def or _destinatario(ini + mm.start()):
                    continue
                best = ""
                break
        qs.append([a, b, best])
    MIN, GAP = 2.3, 1.3
    out = []
    for a, b, p in qs:
        b = max(b, a + MIN)
        if out and out[-1][2] == p and a - out[-1][1] < GAP:   # dos citas seguidas de la misma persona: se mantiene
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b, p])
    return out


def _barra_nc(nombre, cargo, ancho=560):
    import re as _re
    cargo = _re.sub(r"\s*\([^)]*\)", "", cargo or "").strip()      # 18-nov: sin notas internas «(cargo SIN VERIFICAR...)»
    if "VERIFICAR" in cargo.upper():
        cargo = ""
    bar = Image.new("RGBA", (ancho, 80), (0, 0, 0, 0)); db = ImageDraw.Draw(bar)
    db.rounded_rectangle([0, 0, ancho, 80], radius=12, fill=(16, 26, 46, 240)); db.rectangle([0, 0, 9, 80], fill=ROJO + (255,))
    db.text((26, 13), _nombre_corto(nombre).upper()[:24], font=fuente("Inter-Black.ttf", 30), fill=BLANCO)
    if cargo:
        db.text((26, 52), cargo.upper()[:36], font=fuente("Inter-SemiBold.ttf", 18), fill=AMARILLO + (255,))
    return bar


def _luz_de_escena(cut, color):
    """17-nov-2026 (integración): el recorte toma un 7 % del color de la escena y una luz de borde suave de ese color,
    para que parezca iluminado por el mismo ambiente y no pegado encima."""
    a = cut.getchannel("A")
    rgb = Image.blend(cut.convert("RGB"), Image.new("RGB", cut.size, color), 0.07)
    luz = tuple(min(255, int(c * 0.55 + 255 * 0.45)) for c in color)
    borde = ImageChops.subtract(a, a.filter(ImageFilter.MinFilter(9))).filter(ImageFilter.GaussianBlur(4))
    borde = ImageChops.multiply(borde.point(lambda v: int(v * 0.5)), a)
    out = Image.merge("RGBA", (*rgb.split(), a))
    capa = Image.new("RGBA", cut.size, luz + (0,)); capa.putalpha(borde)
    out.alpha_composite(capa)
    return out


def _recorte_integrado(nombre, alto, luz=None):
    """Opción A (ESTÁNDAR 15-nov): recorte real SIN FONDO de la persona, con sombra suave, para ir INTEGRADO delante de la
    escena (no Polaroid). Devuelve RGBA (con su sombra, pad incluido) o None si no hay recorte curado."""
    try:
        import biblioteca_fotos as BF
        r, _ = BF.mejor_recorte(nombre)
        if not (r and Path(r).exists()):
            return None
        cut = Image.open(r).convert("RGBA")
        cut = cut.resize((max(1, int(cut.width * alto / cut.height)), alto), Image.LANCZOS)
        if luz:                                            # solo el largo (17-nov): color y luz de la escena
            cut = _luz_de_escena(cut, tuple(luz[:3]))
        pad = 60
        a = Image.new("L", (cut.width + 2 * pad, cut.height + 2 * pad)); a.paste(cut.getchannel("A"), (pad, pad))
        som = a.filter(ImageFilter.GaussianBlur(24)).point(lambda v: int(v * 0.6))
        base = Image.new("RGBA", a.size)
        base.alpha_composite(Image.merge("RGBA", (*Image.new("RGB", a.size).split(), som)), (-12, 16))
        base.alpha_composite(cut, (pad, pad))
        return base
    except Exception as e:
        print(f"  (recorte integrado {nombre}: {type(e).__name__})")
        return None


def _es_institucion(n):
    return bool(__import__("re").match(r"(?i)\s*(tribunal|supremo|gobierno|congreso|senado|audiencia|fiscal[ií]a|abogac[ií]a|junta|consejo|ministerio)\b", n or ""))


def _polas_persona(dia, fecha, quotes, acento, ancho_f, ancho_s, cargos=None, alto_rec=0, luz=None):
    """Imagen de la persona para ir DELANTE de la escena (estándar «opción A», 15-nov). PRIMERO el recorte curado sin fondo
    (integrado, con sombra); si no hay, Polaroid de respaldo. Devuelve (full, small, barras): full/small = imágenes grande y
    pequeña; barras[n] = barra de nombre/cargo (None si la Polaroid ya la lleva baked)."""
    cargos = cargos or {}
    full, small, barras = {}, {}, {}
    for n in dict.fromkeys(p for _, _, p in quotes):
        if not n or n in full:
            continue
        if _es_institucion(n):                             # 18-nov: instituciones sin retrato (salió un cuadro de El Salvador)
            continue
        cargo = cargos.get(n, "")
        rec = _recorte_integrado(n, alto_rec, luz=luz) if alto_rec else None
        if rec is not None:                                # opción A: recorte integrado + barra aparte
            full[n] = rec
            small[n] = rec.resize((int(rec.width * ancho_s / ancho_f), int(rec.height * ancho_s / ancho_f)), Image.LANCZOS)
            barras[n] = _barra_nc(n, cargo)
            continue
        foto, cargo2, cred = _foto_persona(dia, fecha, n, cargo)   # respaldo: Polaroid (la barra va baked)
        if not foto:
            continue
        try:
            full[n] = polaroid_armonica(foto, n, cargo2 or cargo, cred, ancho_f, acento, giro=-3)
            small[n] = polaroid_armonica(foto, n, cargo2 or cargo, cred, ancho_s, acento, giro=4)
            barras[n] = None
        except Exception as e:
            print(f"  (Polaroid de {n}: {type(e).__name__})")
    return full, small, barras


def _sub_es_clave(w):
    """Palabra clave del subtítulo (va en AMARILLO): parte de una cita «...», cifra o nombre propio."""
    import re as _re
    wl = w.strip("«»().,:;¡!¿?\"'-— ")
    return bool("«" in w or "»" in w or _re.search(r"\d", w) or (len(wl) > 3 and wl[:1].isupper() and not wl.isupper()))


def _sub_chunks(c0, btxt, T, nmax=4, cmax=26):
    """Trocea el texto que lee la voz en grupos cortos tipo karaoke, con su ventana de tiempo (absoluta) según los tiempos de
    palabra (T). Devuelve [[t_ini, t_fin, [palabras]], ...]. Dentro de «...» no corta hasta cerrar la cita."""
    import re as _re
    pals = [(m.group(0), T.en(c0 + m.start())) for m in _re.finditer(r"\S+", btxt)]
    trozos, cur, dentro = [], [], False
    for w, ts in pals:
        cur.append((w, ts))
        if "«" in w and "»" not in w:
            dentro = True
        elif "»" in w:
            dentro = False
        linea = " ".join(x[0] for x in cur)
        fin = cur[-1][0].endswith((".", "!", "?", "…"))
        if not dentro and (fin or len(cur) >= nmax or len(linea) >= cmax):
            trozos.append(cur); cur = []
    if cur:
        trozos.append(cur)
    out = []
    for k, c in enumerate(trozos):
        a = c[0][1]
        b = trozos[k + 1][0][1] if k + 1 < len(trozos) else a + 1.6
        out.append([a, b, [x[0] for x in c]])
    return out


def _dibuja_sub(fr, t, chunks, modo, zona=None):
    """Dibuja el subtítulo karaoke AL PIE (sin caja), texto del guion en BLANCO con las palabras clave en AMARILLO y borde
    negro para legibilidad. El trozo activo es el que contiene el instante t. Estándar en todos los vídeos."""
    if not chunks:
        return
    seg = next((c for c in chunks if c[0] <= t < c[1]), None)
    if not seg and chunks and t >= chunks[-1][1] and t < chunks[-1][1] + 0.8:
        seg = chunks[-1]                                   # mantener el último un pelín
    if not seg:
        return
    W, H = fr.size
    tam = 72 if modo == "short" else 64      # subtítulo karaoke más grande (15-nov-2026, petición del usuario)
    f = fuente("Inter-Black.ttf", tam)       # 15-nov-2026: ESTÁNDAR karaoke estilo TikTok (sans bold), no cómic
    d = ImageDraw.Draw(fr)
    zx0, zx1 = zona or (0, W)
    maxw = (zx1 - zx0) * 0.94 if zona else W * 0.9
    while True:
        lineas, cur = [], []
        for w in seg[2]:
            prueba = " ".join([x[0] for x in cur] + [w])
            if cur and d.textlength(prueba, font=f) > maxw:
                lineas.append(cur); cur = []
            cur.append((w, _sub_es_clave(w)))
        if cur:
            lineas.append(cur)
        # 17-nov: en el largo, máximo 2 líneas (con 3-4 subía hasta tapar la cara del personaje): se reduce la letra
        if not zona or len(lineas) <= 2 or tam <= 44:
            break
        tam -= 4
        f = fuente("Inter-Black.ttf", tam)
    lh = int(tam * 1.22)
    y0 = (H - 165 - lh * len(lineas)) if modo == "short" else (H - 92 - lh * len(lineas))
    for li, linea in enumerate(lineas):
        tot = d.textlength(" ".join(x[0] for x in linea), font=f)
        x = zx0 + (zx1 - zx0 - tot) / 2
        y = y0 + li * lh
        for w, yel in linea:
            d.text((x, y), w, font=f, fill=(AMARILLO if yel else BLANCO) + (255,), stroke_width=7, stroke_fill=(0, 0, 0, 255))
            x += d.textlength(w + " ", font=f)


def _ease(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def _activa_largo(t, quotes, full, small, persona_dom, t_ini):
    """(persona, persona_previa_en_cruce) en el instante t del largo; None antes del bloque."""
    if t_ini is not None and t < t_ini:
        return None, None
    i = next((k for k, (a, b, p) in enumerate(quotes) if a - 0.12 <= t <= b), None)
    if i is not None and quotes[i][2] in full:
        a, b, p = quotes[i]
        prev = quotes[i - 1] if i > 0 else None
        conv = bool(prev and prev[2] != p and a - prev[1] < 1.4 and prev[2] in small)
        return p, (prev[2] if conv else None)
    if isinstance(persona_dom, list):                    # 18-nov: la persona del PASO que suena (nunca la de otro paso)
        pp = next((q for a, b, q in persona_dom if a - 0.12 <= t <= b), None)
        return (pp if pp in full else None), None
    return (persona_dom if persona_dom in full else None), None


_BBOX = {}


def _bbox_alfa(img):
    k = id(img)
    if k not in _BBOX:
        _BBOX[k] = img.getchannel("A").point(lambda v: 255 if v > 140 else 0).getbbox() or (0, 0, img.width, img.height)
    return _BBOX[k]


def _con_alfa(img, f):
    if f >= 0.995:
        return img
    o = img.copy(); o.putalpha(img.getchannel("A").point(lambda v: int(v * f))); return o


def _dibuja_persona_largo(fr, t, quotes, full, small, barras, persona_dom, t_ini):
    """17-nov-2026 (usuario: «el rótulo cae encima de ellos», «queda forzado, tiene que ser más fluido y profesional»).
    El personaje del largo ENTRA deslizando con fundido (0,5 s, frenada suave), al cambiar de persona la anterior SALE
    mientras entra la nueva, y mientras habla tiene un acercamiento lento y continuo (nunca congelado). El rótulo de
    nombre/cargo va AL LADO del recorte (nunca encima de la cara o el cuerpo), entra 0,2 s después con un barrido y queda
    por encima de la franja del karaoke."""
    W, H = fr.size
    barras = barras or {}
    p, prevp = _activa_largo(t, quotes, full, small, persona_dom, t_ini)
    # cuándo entró la persona actual y quién estaba antes (hasta 0,6 s atrás, a pasos de fotograma)
    t_ent, saliente = None, None
    for k in range(1, 19):
        q, _ = _activa_largo(t - k / 30, quotes, full, small, persona_dom, t_ini)
        if q != p:
            t_ent = t - (k - 1) / 30
            saliente = q
            break
    dt = 9.0 if t_ent is None else t - t_ent           # segundos desde que entró (9 = ya asentado)
    if t_ent is None:                                   # entró hace más de 0,6 s: busca cuándo, para el acercamiento lento
        dt = 0.6
        for k in range(1, 40):
            q, _ = _activa_largo(t - 0.6 - k * 0.25, quotes, full, small, persona_dom, t_ini)
            if q != p:
                break
            dt = 0.6 + k * 0.25

    def pinta(nombre, img, lado, prog, desde, con_barra):
        e = _ease(prog)
        ea = _ease(prog * 2.8)                                  # opaca enseguida: sin cara «fantasma» sobre el fondo
        esc_ = (0.95 + 0.05 * e) * (1 + 0.025 * min(1.0, desde / 10.0))     # entra creciendo y luego acercamiento lento
        im = img.resize((max(1, int(img.width * esc_)), max(1, int(img.height * esc_))), Image.BILINEAR) \
            if abs(esc_ - 1) > 0.004 else img
        im = _con_alfa(im, ea)
        bx0, by0, bx1, by1 = _bbox_alfa(img)
        bx0, bx1 = int(bx0 * esc_), int(bx1 * esc_)
        if lado == "izq":
            x = 30 - int((1 - e) * 220)
        else:
            x = W - im.width - 30 + int((1 - e) * 220)
        y = H - im.height + 40 + int((1 - e) * 24)
        fr.alpha_composite(im, (x, y))
        b = barras.get(nombre)
        if con_barra and b is not None:
            eb = _ease((desde - 0.2) / 0.45) if prog >= 1 else 0.0
            if eb > 0:
                ancho = max(1, int(b.width * eb))
                bb = _con_alfa(b.crop((0, 0, ancho, b.height)), min(1.0, eb * 1.4))
                by = H - 395                                   # por encima de la franja del karaoke
                if lado == "izq":
                    bxp = min(x + bx1 - 20, W - b.width - 40)  # pegado al hombro derecho, sin pisar la figura
                    fr.alpha_composite(bb, (bxp, by))
                else:
                    bxp = max(40, x + bx0 - b.width + 20)
                    fr.alpha_composite(bb, (bxp + (b.width - ancho), by))

    SAL, ENT = 0.22, 0.5
    if saliente and saliente in full and dt < SAL:           # relevo: la anterior sale deslizando hacia fuera...
        pinta(saliente, full[saliente], "izq", 1 - dt / SAL, 9.0, False)
    if not p:
        return
    ret = SAL if saliente else 0.0                           # ...y la nueva entra cuando ya ha salido (sin fundir caras)
    if dt < ret:
        return
    prog = min(1.0, (dt - ret) / ENT)
    dt = dt - ret
    # Siempre UNA persona y siempre a la izquierda (el recuadro de la cita va a la derecha): en un cruce, la que contesta
    # releva a la anterior con el fundido de entrada/salida, en vez de amontonar dos recortes que pisaban el recuadro.
    pinta(p, full[p], "izq", prog, dt, True)


def _dibuja_polas(fr, t, quotes, full, small, modo, caja=None, barras=None, persona_dom=None, t_ini=None):
    """ESTÁNDAR «opción A» (15-nov): SIEMPRE un personaje en la escena. Dibuja el recorte integrado (o Polaroid de respaldo)
    de la persona ACTIVA —la que dice la cita en el instante t, o la persona dominante/referida del bloque si no hay cita—,
    anclado abajo (largo: izquierda; short: arriba), con su barra de nombre/cargo. En un cruce, también la anterior."""
    W, H = fr.size
    barras = barras or {}
    i = next((k for k, (a, b, p) in enumerate(quotes) if a - 0.12 <= t <= b), None)
    if i is not None and quotes[i][2] in full:             # cita ATRIBUIDA: la persona que la dice
        a, b, p = quotes[i]
        prev = quotes[i - 1] if i > 0 else None
        conversa = bool(prev and prev[2] != p and a - prev[1] < 1.4 and prev[2] in small and p in full)
        estado = "double" if conversa else "single"
        a_ini = a
    else:                                                  # cita sin atribuir o sin cita: la persona dominante (nunca vacío)
        p = persona_dom if (not isinstance(persona_dom, list) and persona_dom in full) else None
        estado = "single" if p else "none"
        a_ini = t - 1.0

    def esc(img, s):
        return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR) if abs(s - 1) > 0.004 else img

    def pop(a):
        return 0.9 + 0.1 * (1 - (1 - min(1.0, (t - a) / 0.4)) ** 2)

    if modo == "largo":
        _dibuja_persona_largo(fr, t, quotes, full, small, barras, persona_dom, t_ini)
        return
    if estado == "none":
        return

    # short (vertical): persona arriba
    if estado == "double":
        prev = quotes[i - 1]; ps = small.get(prev[2])
        if ps:
            fr.alpha_composite(ps, (20, 230))
        cim = esc(full[p], pop(a_ini)); fr.alpha_composite(cim, (W - cim.width - 20, 200))
        if barras.get(p) is not None:
            fr.alpha_composite(barras[p], (30, 200 + cim.height - 70))
    else:
        cim = esc(full[p], pop(a_ini)); fr.alpha_composite(cim, ((W - cim.width) // 2, 200))
        if barras.get(p) is not None:
            fr.alpha_composite(barras[p], ((W - barras[p].width) // 2, 200 + cim.height - 70))


def _foto_persona(dia, fecha, nombre, cargo=""):
    """Foto real, de CALIDAD y con VARIEDAD (nada repetido en 7 días), de la persona para su Polaroid. Usa la del día si la
    hay; si no, la baja con fotos.mejores (descarta caras pequeñas; Gemini elige la mejor). Devuelve (ruta, cargo, credito)."""
    import json
    cred_f = dia / "creditos.json"
    cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}

    # 15-nov-2026 (petición del usuario): PRIMERO los recortes transparentes CURADOS por el usuario (identidad verificada
    # por él, sin artefactos). Se componen sobre una tarjeta de estudio para que la Polaroid quede como una foto limpia.
    try:
        import biblioteca_fotos as BF
        rec, ficha = BF.mejor_recorte(nombre)
        if rec and Path(rec).exists():
            from PIL import Image
            cut = Image.open(rec).convert("RGBA")
            w, h = cut.size
            fondo = Image.new("RGBA", (w, h), (206, 214, 228, 255))                 # gris-azul claro
            oscuro = Image.new("RGBA", (w, h), (120, 132, 156, 255))
            fondo = Image.composite(oscuro, fondo, Image.linear_gradient("L").resize((w, h)))   # degradado de estudio
            fondo.alpha_composite(cut)
            (dia / "imagenes").mkdir(parents=True, exist_ok=True)
            nom = f"retrato_{_norm(nombre.split()[-1])}_png.jpg"
            fondo.convert("RGB").save(dia / "imagenes" / nom, quality=92)
            cred[nom] = dict(ficha or {}, persona=nombre, autor=(ficha or {}).get("autor") or "archivo del canal",
                             licencia=(ficha or {}).get("licencia") or "uso editorial", puntos_gemini=9)
            cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
            return dia / "imagenes" / nom, ((ficha or {}).get("cargo") or cargo), "Foto: archivo del canal"
    except Exception as e:
        print(f"  (recorte curado no disponible para {nombre}: {type(e).__name__})")

    def busca():
        fs = [(f, c) for f, c in cred.items() if _norm(c.get("persona")) == _norm(nombre) and "_recorte" not in f
              and (dia / "imagenes" / f).exists()]
        fs.sort(key=lambda fc: -float(fc[1].get("puntos_gemini", 0) or 0))
        return fs[0] if fs else None

    hit = busca()
    if not hit:
        import fotos
        for iv in (False, True):      # 1º con variedad (7 días); si no hay foto buena, mejor UNA REPETIDA que ninguna Polaroid
            try:
                fotos.mejores(fecha, nombre, "serio, primer plano, mirando a cámara", 2, solo=True, ignora_variedad=iv)
                cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else cred
                hit = busca()
            except Exception as e:
                print(f"  (sin foto de {nombre}{' (repitiendo)' if iv else ''}: {type(e).__name__})")
            if hit:
                if iv:
                    print(f"  {nombre}: sin foto nueva esta semana; se repite una buena para no quedarnos sin Polaroid")
                break
    if not hit:                                            # 15-nov: RESPALDO sin red: biblioteca local de fotos
        try:
            import shutil

            import biblioteca_fotos as BF
            got = BF.busca(nombre, 1)
            if got:
                ruta_bib, ficha = got[0]
                (dia / "imagenes").mkdir(parents=True, exist_ok=True)
                nom = f"retrato_{_norm(nombre.split()[-1])}_bib.jpg"
                shutil.copyfile(ruta_bib, dia / "imagenes" / nom)
                cred[nom] = dict(ficha, persona=nombre, puntos_gemini=ficha.get("puntos") or 6)
                cred_f.write_text(json.dumps(cred, ensure_ascii=False, indent=1), encoding="utf-8")
                hit = busca()
                print(f"  {nombre}: foto de la BIBLIOTECA local (sin red / sin foto nueva)")
        except Exception as e:
            print(f"  (biblioteca de fotos no disponible para {nombre}: {type(e).__name__})")
    if not hit:
        return None, cargo, ""
    f, c = hit
    cr = f"Foto: {c.get('autor', '')[:30]} · {c.get('licencia', 'CC')}"
    return dia / "imagenes" / f, (c.get("cargo") or cargo), cr


def _escena_openai(destino, esc, sobrio=False, orient="16:9"):
    """Escena de ambiente de LÍNEA CLARA generada por OpenAI (excepción, cuando FLUX y HF no tienen cuota). Prompt RICO en
    detalle del lugar de la noticia, sin personas en primer plano ni texto. Devuelve True si la generó."""
    import imagen_fondo as IF
    size = "1024x1536" if orient == "9:16" else "1536x1024"
    extra = (" Muted desaturated palette, quiet respectful mood." if sobrio else "")
    prompt = (IA.ESTILO_AMBIENTE + esc.strip().rstrip(".") +
              ". Highly detailed graphic-novel ESTABLISHING WIDE SHOT: a specific, recognizable Spanish setting with clear "
              "foreground, midground and background; architecture, street furniture, flags, lecterns, facades, urban textures "
              "and atmospheric light that make the news context instantly readable at a glance; strong depth and composition. "
              "Absolutely no people in the foreground, no human faces, no readable text, letters, numbers or logos." + extra)
    tmp = Path(destino).with_suffix(".oai.png")
    if not IF._openai(prompt, tmp, size=size):
        return False
    Image.open(tmp).convert("RGB").save(destino, quality=92)
    try:
        tmp.unlink()
    except OSError:
        pass
    return True


# 15-nov: escenas de la biblioteca que NO sirven (pantallas/logos/grafitis/fotos inventados) y escenas más vascas (Hernani)
_LIB_MALAS = ("ec3eb2", "caabea", "69598c", "dad97a", "232cd0", "c82c99", "0c963d", "06bf54", "a76f43", "41a12f")
_LIB_VASCAS = ("f433e5", "dff736", "6d1f15", "17d0bc")


def _lib_elige(esc, usadas_lib):
    """Escena de la biblioteca para `esc`: sin las malas, sin repetir en el vídeo (ni otro Congreso si ya salió uno) y, si la
    escena es vasca, primero las de plaza/calle empedrada. Devuelve (ruta_img, ruta_clip|None, id) o None."""
    import biblioteca_ambiente as BIB
    cat = {e["id"][:6]: e for e in (BIB._catalogo() or [])}
    if "basque" in esc.lower() or "bilbao" in esc.lower():
        for k in _LIB_VASCAS:
            e = cat.get(k)
            if e and e["id"] not in usadas_lib and (BIB.BIB / e["img"]).exists():
                return BIB.BIB / e["img"], None, e["id"]
    malas = {e["id"] for k, e in cat.items() if k in _LIB_MALAS}
    got = BIB.busca(f"{esc} {_LIB_POLITICA}", usadas=set(usadas_lib) | malas)   # 17-nov: prioridad a lo institucional
    if got and got[2] in malas:
        return None
    return got


def _usadas_dia(dia):
    """16-nov-2026 (usuario: «no hay variedad de fondos»): escenas de ambiente de la biblioteca ya usadas HOY por otros
    vídeos de la jornada, para NO repetir el mismo fondo entre el largo y los Shorts."""
    try:
        return set(json.loads((Path(dia) / "escenas_usadas.json").read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _guarda_usadas_dia(dia, usadas):
    try:
        (Path(dia) / "escenas_usadas.json").write_text(json.dumps(sorted(usadas), ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _consigue_escena(destino, esc, usadas_lib, sobrio=False, intento=3, orient="16:9"):
    """Intenta SIEMPRE una imagen nueva con FLUX (máxima variedad); si FLUX falla, la mejor de la biblioteca de ambiente.
    Devuelve (ruta, origen) con origen en {"nueva","lib_clip","lib_simple"}, o (None, None).
    Excepción (EH_ESCENAS_OPENAI=1): se genera con OpenAI como primera opción (días sin cuota de FLUX/HF)."""
    import biblioteca_ambiente as BIB
    Path(destino).parent.mkdir(parents=True, exist_ok=True)     # 18-nov: sin la carpeta, el guardado fallaba (FileNotFoundError) y todo caía a biblioteca
    if Path(destino).exists():
        return destino, "nueva"
    if os.environ.get("EH_ESCENAS_OPENAI"):
        try:
            if _escena_openai(destino, esc, sobrio, orient):
                return destino, "nueva"
            print(f"  (OpenAI no genera «{esc[:36]}»; pruebo FLUX/biblioteca)")
        except Exception as ex:
            print(f"  (OpenAI falla «{esc[:36]}»: {type(ex).__name__}); pruebo FLUX/biblioteca)")
    try:
        IA.ilustra(esc, None, sobrio, intento=intento, ambiente=True).save(destino, quality=92)
        return destino, "nueva"
    except Exception as ex:
        print(f"  (FLUX falla «{esc[:36]}»: {type(ex).__name__}); biblioteca de ambiente")
    got = _lib_elige(esc, usadas_lib)
    if got:
        usadas_lib.add(got[2])
        for e in (BIB._catalogo() or []):          # un Congreso/Plaza Mayor ya usado cuenta para todos sus parecidos
            for w in ("congress", "plaza mayor", "court of auditors"):
                if w in e.get("desc", "").lower() and w in next((x.get("desc", "").lower() for x in BIB._catalogo() if x["id"] == got[2]), ""):
                    usadas_lib.add(e["id"])
        return got[0], ("lib_clip" if got[1] else "lib_simple")
    return None, None


def _guarda_lib(ruta, esc, esc_viva):
    """Guarda la escena en la biblioteca: animada si tiene su clip de vídeo IA, simple si no."""
    try:
        import biblioteca_ambiente as BIB
        clip = Path(ruta).with_suffix(".mp4")
        BIB.guarda(ruta, esc, clip=clip if (esc_viva[0] and clip.exists()) else None)
    except Exception as e:
        print(f"  (biblioteca no guardó {Path(ruta).name}: {type(e).__name__})")


def short(fecha, n):
    dia = RAIZ / "dia" / fecha
    S = json.loads((dia / "shorts" / f"short_{n}.json").read_text(encoding="utf-8"))
    tmp = dia / "shorts" / f"tmp_amb_{n}"
    tmp.mkdir(parents=True, exist_ok=True)
    texto = S["voz"]
    pal, dur = voz.locuta([{"di": texto}], "normal", tmp / "voz.wav", cola=0.3)
    T = E.Tiempos(texto, pal, 0.0)
    total = dur + 1.2
    # cierre (pantalla final) desde la pregunta
    preg = (S.get("pregunta") or "¿Qué opinas?").strip()
    k_fin = next((texto.find(x) for x in (preg, "Te leo en comentarios") if x in texto), -1)
    t_fin = T.en(k_fin) if k_fin >= 0 else dur - 3.0

    # escenas de ambiente (lugares/objetos/símbolos, SIN personas en primer plano) acordes al tema.
    # Si el guion trae su propio «ambiente» (lo escribe el redactor), se usa; si no, lo genera Gemini.
    # SIEMPRE se intenta una imagen nueva con FLUX (variedad); la nueva se guarda en la biblioteca; si FLUX falla, biblioteca.
    escenas_txt = [e for e in (S.get("ambiente") or []) if isinstance(e, str) and e.strip()][:5] or escenas_ambiente(S, 5)
    rutas, descs, usadas_lib = [], [], _usadas_dia(dia)   # no repetir fondos entre vídeos de la jornada
    mov = S.get("movimiento", "camera slowly pushes in, subtle natural motion, flags and banners sway")
    for k, esc in enumerate(escenas_txt):
        d = dia / "vinetas" / f"short{n}_env_{k}.jpg"
        r, origen = _consigue_escena(d, esc, usadas_lib, orient="9:16")
        if r:
            rutas.append((r, origen)); descs.append(esc)
    if not rutas:
        raise SystemExit(f"short {n}: sin escenas de ambiente")
    _guarda_usadas_dia(dia, usadas_lib)                    # registra las de la biblioteca usadas hoy (variedad entre vídeos)
    escenas = []
    for kk, ((r, origen), esc) in enumerate(zip(rutas, descs)):
        animar = origen == "lib_clip" or (origen == "nueva" and kk < 3)   # LTX en lo nuevo (cuota) o reusar el clip guardado
        ev = _escena_viva(r, mov, animar=animar)
        escenas.append(ev)
        if origen == "nueva":
            _guarda_lib(r, esc, ev)
    rutas = [r for r, _ in rutas]

    # tiempos de cada frase y reparto de escenas (una por frase, repartidas hasta el cierre)
    frases = [f for f in re.split(r"(?<=[.?!])\s+", texto[:k_fin] if k_fin >= 0 else texto) if f.strip()]
    t_frase, pos = [], 0
    for f in frases:
        kf = texto.find(f[:20], pos)
        t_frase.append(T.en(kf) if kf >= 0 else 0.0)
        pos = (kf if kf >= 0 else pos) + len(f)
    if t_frase:
        t_frase[0] = 0.0
    ne = len(escenas)
    esc_de_frase = [min(ne - 1, int(i * ne / max(1, len(frases)))) for i in range(len(frases))]
    cambios = []                                           # (t_inicio, idx_escena)
    for i, te in enumerate(t_frase):
        if not cambios or esc_de_frase[i] != cambios[-1][1]:
            cambios.append((te, esc_de_frase[i]))
    cortes = [c[0] for c in cambios[1:]]

    cab = SH._cabecera(fecha, S.get("categoria", ""))
    kick = SH._kicker((S.get("kicker") or S.get("quien", "")).upper())
    sub_chunks = _sub_chunks(0, texto[:k_fin] if k_fin >= 0 else texto, T)   # subtítulo karaoke al pie
    # 16-nov-2026 (usuario): recuadro de cita SOLO para frases cortas (gancho); en las citas largas, solo karaoke (si no,
    # recuadro y karaoke muestran lo mismo a la vez y se pisan).
    cajas = {i: (SH._caja(f.strip(), ancho=940, tam=40) if len(f.split()) <= 9 else None) for i, f in enumerate(frases)}

    # Polaroids de quien dice cada CITA (foto real, calidad + variedad), en armonía con el fondo; aparecen con la cita y se
    # quitan al acabarla; en un cruce, la anterior se queda pequeña al lado hasta que termina la segunda (como una charla).
    base0 = escenas[0][2]
    acento_s = _acento(base0.crop((0, int(base0.height * 0.45), base0.width, int(base0.height * 0.75))))
    conocidas = _conocidas()
    quotes = _citas_timeline(texto, 0, texto[:k_fin] if k_fin >= 0 else texto, T, conocidas, S.get("quien", ""))
    pol_full, pol_small, barras = _polas_persona(dia, fecha, quotes, acento_s, 600, 410, dict(conocidas),
                                                 alto_rec=int(AL * 0.46))
    _qp = [p for *_, p in quotes if p]
    pdom = max(_qp, key=_qp.count) if _qp else S.get("quien", "")
    if pdom and pdom not in pol_full:                      # siempre un personaje en el Short
        rec = _recorte_integrado(pdom, int(AL * 0.52))
        if rec is not None:
            pol_full[pdom] = rec; barras[pdom] = _barra_nc(pdom, dict(conocidas).get(pdom, ""))

    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.4, [], efectos=[(x, "whoosh") for x in cortes],
                  con_sintonia=False)

    def esc_en(t):
        k = max([j for j, (tc, _) in enumerate(cambios) if tc <= t] or [0])
        t0 = cambios[k][0]
        t1 = cambios[k + 1][0] if k + 1 < len(cambios) else t_fin
        return k, cambios[k][1], t - t0, max(1.0, t1 - t0)

    def frase_idx(t):
        return max([i for i, te in enumerate(t_frase) if te <= t] or [0])

    def cuadro(t):
        if t >= t_fin:                                     # pantalla final
            fr = _vista(escenas[cambios[-1][1]], (t_fin - cambios[-1][0]) + (t - t_fin), 6, cambios[-1][1])
            fr.alpha_composite(Image.new("RGBA", (AN, AL), (8, 12, 24, 210)))
            fr.alpha_composite(cab, (0, 0))
            SH._cierre(fr, t - t_fin, preg)
            return fr
        kc, ie, tl, dk = esc_en(t)
        fr = _vista(escenas[ie], tl, dk, ie)
        if kc > 0 and tl < 0.45:                            # transición: la nueva entra deslizando
            q = G2.suave(tl / 0.45)
            ip = cambios[kc - 1][1]
            prev = _vista(escenas[ip], (t - cambios[kc - 1][0]), 6, ip)
            comp = Image.new("RGBA", (AN, AL))
            comp.paste(prev, (int(-AN * 0.25 * q), 0))
            comp.alpha_composite(fr, (int(AN * (1 - q)), 0))
            fr = comp
        # oscurecer abajo para el texto
        g = Image.linear_gradient("L").resize((AN, 760)).point(lambda v: int(max(0, v - 80) * 1.35))
        som = Image.new("RGBA", (AN, 760), (6, 10, 22, 255))
        som.putalpha(g)
        fr.alpha_composite(som, (0, AL - 760))
        gt = Image.linear_gradient("L").resize((AN, 230)).point(lambda v: int(max(0, 170 - v)))   # sombra arriba (cabecera legible)
        st = Image.new("RGBA", (AN, 230), (6, 10, 22, 255))
        st.putalpha(gt)
        fr.alpha_composite(st, (0, 0))
        fr.alpha_composite(cab, (0, 0))
        _dibuja_polas(fr, t, quotes, pol_full, pol_small, "short", barras=barras, persona_dom=pdom)   # recorte integrado
        caja = cajas[frase_idx(t)]                                   # recuadro de la frase (solo si es corta)
        if caja is not None:
            caja_y = AL - 400 - caja.height
            fr.alpha_composite(kick, (50, caja_y - kick.height - 14))  # etiqueta (kicker) encima del recuadro
            fr.alpha_composite(caja, ((AN - caja.width) // 2, caja_y))
        else:                                                        # cita larga: solo karaoke; el kicker, en sitio fijo
            fr.alpha_composite(kick, (50, AL - 470))
        _dibuja_sub(fr, t, sub_chunks, "short")                      # subtítulo karaoke al pie (blanco + amarillo)
        d = ImageDraw.Draw(fr)
        d.text((AN // 2, AL - 70), f"Fuente: {S.get('fuente', '')}"[:70], font=fuente("Inter-SemiBold.ttf", 26),
               fill=(210, 216, 230, 255), anchor="mm")
        d.rectangle([0, AL - 12, int(AN * min(1.0, t / total)), AL], fill=AMARILLO + (255,))
        return fr

    out = dia / "shorts" / f"short_{n}.mp4"
    ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN}x{AL}",
                           "-r", str(FPS), "-i", "-", "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast",
                           "-crf", "21", "-pix_fmt", "yuv420p", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                           "-c:a", "aac", "-b:a", "160k", "-shortest", str(out)], stdin=subprocess.PIPE)
    for fi in range(int(math.ceil(total * FPS))):
        ff.stdin.write(cuadro(fi / FPS).tobytes())
    ff.stdin.close()
    ff.wait()
    S["duracion"] = round(total, 1)
    (dia / "shorts" / f"short_{n}.json").write_text(json.dumps(S, ensure_ascii=False, indent=1), encoding="utf-8")
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"SHORT {n} (ambiente): {total:.1f} s -> {out}")



# ===================== VÍDEO LARGO (16:9) con el mismo estilo =====================
AN2, AL2 = 1920, 1080


def _cabecera16(fecha, n, total, titulo, fuentes):
    """Cabecera del vídeo largo: franja superior con logo y nombre, chip de bloque y título; abajo, FUENTES."""
    cab = Image.new("RGBA", (AN2, AL2))
    d = ImageDraw.Draw(cab)
    d.rectangle([0, 0, AN2, 8], fill=ROJO + (255,))
    d.rectangle([0, 8, AN2, 14], fill=AMARILLO + (255,))
    # sombra superior e inferior para legibilidad
    gt = Image.linear_gradient("L").resize((AN2, 230)).point(lambda v: int(max(0, 175 - v)))
    st = Image.new("RGBA", (AN2, 230), (6, 10, 22, 255)); st.putalpha(gt); cab.alpha_composite(st, (0, 0))
    gb = Image.linear_gradient("L").resize((AN2, 170)).point(lambda v: int(max(0, v - 40) * 1.3))
    sb = Image.new("RGBA", (AN2, 170), (6, 10, 22, 255)); sb.putalpha(gb); cab.alpha_composite(sb, (0, AL2 - 170))
    cab.alpha_composite(G2.logo(70), (40, 30))
    f_ = fuente("Inter-Black.ttf", 36)
    d.text((126, 64), "EL HOY ", font=f_, fill=BLANCO + (255,), anchor="lm")
    d.text((126 + f_.getlength("EL HOY "), 64), "FORMATIVO", font=f_, fill=AMARILLO + (255,), anchor="lm")
    y, m, dd = (int(x) for x in fecha[:10].split("-"))
    fe = f"{dd} {['ENE','FEB','MAR','ABR','MAY','JUN','JUL','AGO','SEP','OCT','NOV','DIC'][m - 1]} {y}"
    d.text((AN2 - 40, 64), fe, font=fuente("Inter-Bold.ttf", 28), fill=(230, 235, 245, 255), anchor="rm")
    # chip de bloque + título
    chip = f"{n:02d}/{total:02d}"
    fc = fuente("Inter-Black.ttf", 34)
    w = int(fc.getlength(chip)) + 36
    d.rounded_rectangle([40, 118, 40 + w, 178], radius=12, fill=ROJO + (255,))
    d.text((40 + w / 2, 148), chip, font=fc, fill=BLANCO + (255,), anchor="mm")
    ft = fuente("Inter-Black.ttf", 42)
    tt = titulo if ft.getlength(titulo) < AN2 - 80 - w - 60 else titulo[:48] + "…"
    d.text((40 + w + 24, 148), tt, font=ft, fill=BLANCO + (255,), anchor="lm",
           stroke_width=3, stroke_fill=(0, 0, 0, 255))
    if fuentes:
        # 17-nov: abajo a la DERECHA (abajo a la izquierda va el personaje y las tapaba)
        fu = fuentes[:90]
        lf = fuente("Inter-Black.ttf", 24).getlength("FUENTES  ") + fuente("Inter-SemiBold.ttf", 24).getlength(fu)
        xf = AN2 - 40 - lf
        d.text((xf, AL2 - 44), "FUENTES  ", font=fuente("Inter-Black.ttf", 24), fill=AMARILLO + (255,), anchor="lm")
        x0 = xf + fuente("Inter-Black.ttf", 24).getlength("FUENTES  ")
        d.text((x0, AL2 - 44), fu, font=fuente("Inter-SemiBold.ttf", 24), fill=(225, 230, 240, 255), anchor="lm")
    return cab


def largo(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    # 17-nov-2026 (usuario): sin mini resumen al principio: el vídeo arranca directamente con la primera noticia. La sección
    # sumario sigue en episodio.json (la usan la miniatura, el título y el director de arte), pero no se narra ni se monta.
    secs = [s for s in G["secciones"] if any(p.get("di") for p in s["pasos"]) and not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", []))]
    tmp = dia / "tmp_largo_amb"
    tmp.mkdir(exist_ok=True)
    texto = " ".join(" ".join(p["di"] for p in s["pasos"]) for s in secs)
    pal, dur = voz.locuta([{"di": " ".join(p["di"] for p in s["pasos"])} for s in secs], "normal", tmp / "voz.wav", cola=0.3)
    T = E.Tiempos(texto, pal, 0.0)
    total = dur + 1.0
    import corto as _C
    # límites de bloque y escenas de ambiente por bloque
    usadas_lib = _usadas_dia(dia)                          # ids ya usados HOY (no repetir fondos entre vídeos de la jornada)
    bloques, c = [], 0
    for i, s in enumerate(secs):
        btxt = " ".join(p["di"] for p in s["pasos"])
        t0 = T.en(c)
        titulo = (s.get("titulo") or s.get("tema") or "").strip()
        fuentes = " · ".join(s.get("fuentes", [])[:4])
        quien = next((n2 for p in s["pasos"] if p.get("ve") for n2 in _C.personas_de(p["ve"])), "")
        pseudo = {"quien": quien, "cita": titulo, "contexto": btxt[:400]}
        amb_guion = [e for p in s["pasos"] for e in ((p.get("ve") or {}).get("ambiente") or []) if isinstance(e, str) and e.strip()]
        n_e = 2 if len(btxt.split()) < 90 else 3              # 17-nov: piezas cortas («todo breves»), 2 escenas (menos FLUX)
        escs_txt = amb_guion[:n_e] or escenas_ambiente(pseudo, n_e)   # las que escribe el redactor o, si no, generadas
        # SIEMPRE imagen nueva con FLUX (variedad); se guarda en la biblioteca; si FLUX falla, la mejor de la biblioteca.
        pares, descs = [], []
        for k, esc in enumerate(escs_txt):
            d_ = dia / "vinetas" / f"L{i}_env_{k}.jpg"
            r, origen = _consigue_escena(d_, esc, usadas_lib, sobrio=s.get("tono") == "sobrio", intento=5)
            if r:
                pares.append((r, origen)); descs.append(esc)
        if not pares:                                     # ni biblioteca: fondo de marca (sin personas), nunca una viñeta cualquiera
            bg = dia / "vinetas" / "_fondo_marca.jpg"
            if not bg.exists():
                G2.fondo_marca(2.0).resize((1280, 720)).convert("RGB").save(bg, quality=90)
            pares, descs = [(bg, "lib_simple")], [titulo]
        escenas = []
        for kk, ((r, origen), esc) in enumerate(zip(pares, descs)):
            animar = origen == "lib_clip" or (origen == "nueva" and i < 2 and kk < 1)
            ev = _escena_viva(r, "camera slowly pushes in, subtle natural motion", animar=animar, w=AN2, h=AL2)
            escenas.append(ev)
            if origen == "nueva":
                _guarda_lib(r, esc, ev)
        rutas = [r for r, _ in pares]
        # cambios de escena por frase dentro del bloque
        frases = [f for f in re.split(r"(?<=[.?!])\s+", btxt) if f.strip()]
        tf, pos = [], c
        for f in frases:
            kf = texto.find(f[:22], pos)
            tf.append(T.en(kf) if kf >= 0 else t0); pos = (kf if kf >= 0 else pos) + len(f)
        ne = len(escenas)
        cambios = []
        for j, te in enumerate(tf):
            ei = min(ne - 1, int(j * ne / max(1, len(frases))))
            if not cambios or ei != cambios[-1][1]:
                cambios.append((te, ei))
        subs = _sub_chunks(c, btxt, T)                     # subtítulo karaoke al pie (tiempos absolutos del bloque)
        cajas = [SH._caja(f.strip(), ancho=820, tam=52) if len(f.split()) <= 9 else None for f in frases]  # solo frases cortas
        # Recorte integrado (opción A) por CITA/escena: la foto real de quien dice la cita o de la persona referida.
        base0 = escenas[0][2]
        acento = _acento(base0.crop((0, int(base0.height * 0.45), int(base0.width * 0.4), base0.height)))
        conocidas = _conocidas()
        _cargos_ep = {}
        for pp_ in s["pasos"]:
            ve_ = pp_.get("ve") or {}
            for it_ in ([ve_["persona"]] if isinstance(ve_.get("persona"), dict) else []) + list(ve_.get("items") or []):
                if isinstance(it_, dict) and it_.get("nombre") and it_.get("cargo"):
                    _cargos_ep[it_["nombre"]] = it_["cargo"]
        conocidas = [(n_, _cargos_ep.get(n_, c_)) for n_, c_ in conocidas] + [(n_, c_) for n_, c_ in _cargos_ep.items() if n_ not in dict(conocidas)]
        quotes = _citas_timeline(texto, c, btxt, T, conocidas, quien)
        # 17-nov: recorte más contenido (64 % del alto, antes 82 %: tapaba la escena y el rótulo caía encima) y con la luz
        # y el color de la escena para que se integre
        pol_full, pol_small, barras = _polas_persona(dia, fecha, quotes, acento, 560, 380, dict(conocidas),
                                                      alto_rec=int(AL2 * 0.64), luz=acento)
        # 18-nov: la persona de cada PASO sale de su escena (ve), no de heurísticas del texto
        import unicodedata as _ud
        _n = lambda x: _ud.normalize("NFKD", x or "").encode("ascii", "ignore").decode().lower()
        pasos_p, cc = [], c
        for pp_ in s["pasos"]:
            ve_ = pp_.get("ve") or {}
            pa, pb = T.en(cc), T.en(cc + len(pp_["di"]))
            cc += len(pp_["di"]) + 1
            nom = None
            try:
                nom = (_C.personas_de(ve_) or [None])[0] if ve_.get("tipo") in ("persona", "citas") else None
            except Exception:
                nom = None
            if nom and _es_institucion(nom):
                nom = None
            pasos_p.append((pa, pb, nom))
            for q_ in quotes:                              # la cita de este paso la dice quien dice su escena
                if pa - 0.2 <= q_[0] <= pb and nom and nom in dict(conocidas) | {nom: ""}:
                    q_[2] = nom
        for pa, pb, nom in pasos_p:
            if nom and nom not in pol_full:
                rec = _recorte_integrado(nom, int(AL2 * 0.64), luz=acento)
                if rec is not None:
                    pol_full[nom] = rec; barras[nom] = _barra_nc(nom, _cargos_ep.get(nom) or dict(conocidas).get(nom, ""))
        _qp = [p for *_, p in quotes if p]
        pdom = pasos_p
        if False and pdom not in pol_full:                  # siempre un personaje: aunque no tenga cita, su recorte
            rec = _recorte_integrado(pdom, int(AL2 * 0.64), luz=acento)
            if rec is not None:
                pol_full[pdom] = rec; barras[pdom] = _barra_nc(pdom, dict(conocidas).get(pdom, ""))
        bloques.append({"t0": t0, "i": i, "titulo": titulo, "fuentes": fuentes, "escenas": escenas,
                        "cambios": cambios or [(t0, 0)], "subs": subs, "cajas": cajas, "tf": tf,
                        "n": len(secs), "quotes": quotes, "pol_full": pol_full, "pol_small": pol_small,
                        "barras": barras, "persona_dom": pdom})
        c += len(btxt) + 1
    _guarda_usadas_dia(dia, usadas_lib)                    # registra las de la biblioteca usadas hoy (variedad entre vídeos)
    for a, b in zip(bloques, bloques[1:]):
        a["t1"] = b["t0"]
    bloques[-1]["t1"] = total
    for bl in bloques:                                     # cabecera cacheada por bloque (no se rehace cada fotograma)
        bl["cab"] = _cabecera16(fecha, bl["i"] + 1, bl["n"], bl["titulo"], bl["fuentes"])
    cortes = [cc[0] for bl in bloques for cc in bl["cambios"][1:]] + [bl["t0"] for bl in bloques[1:]]
    musica.mezcla(tmp / "voz.wav", tmp / "audio.wav", 0.0, 1.2, [], efectos=[(x, "whoosh") for x in sorted(cortes)],
                  con_sintonia=True)

    def bloque_en(t):
        return max([k for k, bl in enumerate(bloques) if bl["t0"] <= t] or [0])

    def cuadro(t):
        bl = bloques[bloque_en(t)]
        cam = bl["cambios"]
        kc = max([j for j, (tc, _) in enumerate(cam) if tc <= t] or [0])
        t0 = cam[kc][0]; ie = cam[kc][1]
        t1 = cam[kc + 1][0] if kc + 1 < len(cam) else bl["t1"]
        fr = _vista(bl["escenas"][ie], t - t0, max(1.0, t1 - t0), ie, w=AN2, h=AL2)
        if kc > 0 and (t - t0) < 0.5:
            q = G2.suave((t - t0) / 0.5); ip = cam[kc - 1][1]
            prev = _vista(bl["escenas"][ip], t - cam[kc - 1][0], 6, ip, w=AN2, h=AL2)
            comp = Image.new("RGBA", (AN2, AL2)); comp.paste(prev, (int(-AN2 * 0.2 * q), 0))
            comp.alpha_composite(fr, (int(AN2 * (1 - q)), 0)); fr = comp
        # sombra inferior para el texto
        g = Image.linear_gradient("L").resize((AN2, 430)).point(lambda v: int(max(0, v - 70) * 1.3))
        som = Image.new("RGBA", (AN2, 430), (6, 10, 22, 255)); som.putalpha(g)
        fr.alpha_composite(som, (0, AL2 - 430))
        fr.alpha_composite(bl["cab"], (0, 0))
        _dibuja_polas(fr, t, bl.get("quotes") or [], bl.get("pol_full") or {}, bl.get("pol_small") or {}, "largo",
                      barras=bl.get("barras"), persona_dom=bl.get("persona_dom"), t_ini=bl["t0"])
        cajas, tf = bl.get("cajas") or [], bl.get("tf") or []
        if cajas:                                           # recuadro de la frase a la DERECHA (solo frases cortas)
            fi = max([j for j, te in enumerate(tf) if te <= t] or [0])
            caja = cajas[min(fi, len(cajas) - 1)]
            if caja is not None:                            # cita larga -> solo karaoke (no se pisa con el recuadro)
                fr.alpha_composite(caja, (AN2 - caja.width - 70, 320))
        _dibuja_sub(fr, t, bl.get("subs") or [], "largo", zona=(600, AN2 - 40))   # 17-nov: a la derecha del personaje
        return fr

    out = dia / "episodio.mp4"
    import multiprocessing as mp
    import os
    import time
    total_fr = int(math.ceil(total * FPS))
    nproc = max(1, min(int(os.environ.get("RENDER_PROCESOS", os.cpu_count() or 1)), total_fr // (FPS * 10) or 1))
    bordes = [total_fr * k // nproc for k in range(nproc + 1)]
    t_ini = time.time()

    def dibuja_trozo(k):
        a, b = bordes[k], bordes[k + 1]
        ff = subprocess.Popen([V1.FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{AN2}x{AL2}",
                               "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "21",
                               "-threads", "2", "-pix_fmt", "yuv420p", str(tmp / f"trozo{k}.mp4")], stdin=subprocess.PIPE)
        for fi2 in range(a, b):
            if k == 0 and (fi2 - a) % (FPS * 20) == 0:
                print(f"  fotograma {(fi2 - a) * nproc}/{total_fr} aprox. ({nproc} a la vez)", flush=True)
            ff.stdin.write(cuadro(fi2 / FPS).tobytes())
        ff.stdin.close()
        return ff.wait()

    if nproc > 1:
        try:
            import cv2 as _cv2
            _cv2.setNumThreads(1)                          # evitar que el fork cuelgue con los hilos de OpenCV vivos
        except ImportError:
            pass
        ctx = mp.get_context("fork")

        def hijo(k):
            try:
                os._exit(dibuja_trozo(k))
            except Exception:
                import traceback
                traceback.print_exc(); os._exit(1)
        procs = [ctx.Process(target=hijo, args=(k,)) for k in range(nproc)]
        for pr in procs:
            pr.start()
        for pr in procs:
            pr.join()
        if any(pr.exitcode for pr in procs):
            raise RuntimeError(f"fallo un trozo del render: {[pr.exitcode for pr in procs]}")
    elif dibuja_trozo(0):
        raise RuntimeError("fallo el render")
    lista = tmp / "trozos.txt"
    lista.write_text("".join(f"file 'trozo{k}.mp4'\n" for k in range(nproc)), encoding="utf-8")
    # re-codificar en la concatenación (no «copy»): evita el fallo de h264_mp4toannexb que descartaba un trozo y acortaba el vídeo
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-i", str(tmp / "audio.wav"), "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                    "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
                    "-shortest", str(out)], check=True)
    print(f"  render: {(time.time() - t_ini) / 60:.1f} min con {nproc} proceso(s) para {total / 60:.1f} min", flush=True)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"LARGO (ambiente): {total:.1f} s -> {out}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "largo":
        largo(sys.argv[1])
    else:
        short(sys.argv[1], int(sys.argv[2]))
