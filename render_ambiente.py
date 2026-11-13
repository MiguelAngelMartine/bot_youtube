"""RENDER ESTILO AMBIENTE (13-nov-2026, aprobado por el usuario): escenas de línea clara ANIMADAS a pantalla completa,
SIN personajes en primer plano, acordes a lo que se narra, con la cabecera EH y el recuadro de la frase sincronizado.
La escena cambia cuando empieza la frase que la describe. Animación: LTX (animar_ia) donde hay cuota; si no, cámara 2,5D
(motion_comic). Reemplaza al estilo anterior (panel + fondo borroso) para los Shorts; base del rediseño del vídeo largo.
Uso: python render_ambiente.py AAAA-MM-DD N   (Short N del día)"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
from pathlib import Path

import cv2
from PIL import Image, ImageDraw, ImageOps

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


FALLBACK_ESC = ["an empty political campaign stage with a podium and microphones, Spanish flags and banners, confetti",
                "a Spanish city street covered with election campaign posters on walls and lampposts, festive bunting",
                "a wide empty outdoor rally venue with a distant empty stage and big screens, rows of empty chairs",
                "a ballot box on a table in an empty Spanish polling station, a Spanish flag on the wall",
                "the facade of a Spanish political party headquarters building with flags, empty street in front"]


def escenas_ambiente(S, n_esc=5):
    """Planos de AMBIENTE (lugares, objetos, símbolos) sin personas, acordes al tema del Short. Gemini; si falla, genéricos."""
    try:
        import gem
        base = f"Tema: {S.get('quien', '')}: «{S.get('cita', '')}». Contexto: {S.get('contexto', '')}"
        pr = (f"Para un vídeo de política española en estilo viñeta de línea clara, describe EN INGLÉS {n_esc} PLANOS DE "
              "AMBIENTE (establishing shots) relacionados con el tema, SIN personas en primer plano y SIN caras: lugares, "
              "edificios, objetos y símbolos (plazas, calles con carteles electorales, atriles y escenarios vacíos, urnas, "
              "pancartas, el Congreso, sedes de partidos, banderas...). Cada uno una frase concreta y visual, sin texto "
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


def polaroid_armonica(foto, nombre, cargo, credito, ancho, acento, giro=-3):
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


def _citas_timeline(texto, c0, btxt, T, conocidas, quien_def):
    """Línea de tiempo de las CITAS («...») del bloque: (t_ini, t_fin, persona). La persona es el apellido conocido que
    aparece más cerca ANTES de la cita (sin acentos). Citas muy cortas se alargan; citas seguidas de la misma, se funden."""
    import re as _re
    nbt = _norm(btxt)
    apes = [(_norm(n.split()[-1]), n) for n, _ in conocidas if len(n.split()[-1]) >= 4]
    qs = []
    for m in _re.finditer(r"«([^»]{3,})»", btxt):
        a, b = T.en(c0 + m.start()), T.en(c0 + m.end())
        best, bestpos = quien_def, -1
        for ape, n in apes:
            pos = nbt.rfind(ape, 0, m.start())
            if pos > bestpos:
                bestpos, best = pos, n
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


def _polas_persona(dia, fecha, quotes, acento, ancho_f, ancho_s, cargos=None):
    """Polaroid grande (giro izq.) y pequeña (giro der.) de cada persona que dice alguna cita, con foto real de calidad y
    variedad, en armonía con el fondo. Solo para las personas que de verdad hablan en el bloque."""
    cargos = cargos or {}
    full, small = {}, {}
    for n in dict.fromkeys(p for _, _, p in quotes):
        if not n or n in full:
            continue
        foto, cargo, cred = _foto_persona(dia, fecha, n, cargos.get(n, ""))
        if not foto:
            continue
        try:
            full[n] = polaroid_armonica(foto, n, cargo or cargos.get(n, ""), cred, ancho_f, acento, giro=-3)
            small[n] = polaroid_armonica(foto, n, cargo or cargos.get(n, ""), cred, ancho_s, acento, giro=4)
        except Exception as e:
            print(f"  (Polaroid de {n}: {type(e).__name__})")
    return full, small


def _dibuja_polas(fr, t, quotes, full, small, modo):
    """Dibuja la(s) Polaroid(s) activa(s) en el instante t: la de la cita en curso (grande, con pop); si viene de un cruce
    con otra persona, la anterior se queda pequeña al lado (conversación) hasta que acaba la cita."""
    W, H = fr.size
    i = next((k for k, (a, b, p) in enumerate(quotes) if a - 0.12 <= t <= b), None)
    if i is None:
        return
    a, b, p = quotes[i]
    pop = 0.84 + 0.16 * (1 - (1 - min(1.0, (t - a) / 0.4)) ** 2)

    def esc(img, s):
        return img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BILINEAR) if abs(s - 1) > 0.004 else img
    prev = quotes[i - 1] if i > 0 else None
    conversa = bool(prev and prev[2] != p and a - prev[1] < 1.4 and prev[2] in full)
    cur = full.get(p)
    if modo == "largo":                                    # zona alta (el recuadro de la frase va abajo)
        y = 185
        if conversa and cur:
            ps = small.get(prev[2])
            if ps:
                fr.alpha_composite(ps, (90, y + 70))
            cim = esc(cur, pop)
            fr.alpha_composite(cim, (W - cim.width - 110, y))
        elif cur:
            cim = esc(cur, pop)
            fr.alpha_composite(cim, (90, y))
    else:                                                  # short (vertical): arriba
        if conversa and cur:
            ps = small.get(prev[2])
            if ps:
                fr.alpha_composite(ps, (30, 250))
            cim = esc(cur, pop)
            fr.alpha_composite(cim, (W - cim.width - 30, 230))
        elif cur:
            cim = esc(cur, pop)
            fr.alpha_composite(cim, ((W - cim.width) // 2, 220))


def _foto_persona(dia, fecha, nombre, cargo=""):
    """Foto real, de CALIDAD y con VARIEDAD (nada repetido en 7 días), de la persona para su Polaroid. Usa la del día si la
    hay; si no, la baja con fotos.mejores (descarta caras pequeñas; Gemini elige la mejor). Devuelve (ruta, cargo, credito)."""
    import json
    cred_f = dia / "creditos.json"
    cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else {}

    def busca():
        fs = [(f, c) for f, c in cred.items() if c.get("persona") == nombre and "_recorte" not in f
              and (dia / "imagenes" / f).exists()]
        fs.sort(key=lambda fc: -float(fc[1].get("puntos_gemini", 0) or 0))
        return fs[0] if fs else None

    hit = busca()
    if not hit:
        try:
            import fotos
            fotos.mejores(fecha, nombre, "serio, primer plano, mirando a cámara", 2, solo=True)   # solo individual, calidad + variedad
            cred = json.loads(cred_f.read_text(encoding="utf-8")) if cred_f.exists() else cred
            hit = busca()
        except Exception as e:
            print(f"  (sin foto de {nombre}: {type(e).__name__})")
    if not hit:
        return None, cargo, ""
    f, c = hit
    cr = f"Foto: {c.get('autor', '')[:30]} · {c.get('licencia', 'CC')}"
    return dia / "imagenes" / f, (c.get("cargo") or cargo), cr


def _consigue_escena(destino, esc, usadas_lib, sobrio=False, intento=3):
    """Intenta SIEMPRE una imagen nueva con FLUX (máxima variedad); si FLUX falla, la mejor de la biblioteca de ambiente.
    Devuelve (ruta, origen) con origen en {"nueva","lib_clip","lib_simple"}, o (None, None)."""
    import biblioteca_ambiente as BIB
    if Path(destino).exists():
        return destino, "nueva"
    try:
        IA.ilustra(esc, None, sobrio, intento=intento, ambiente=True).save(destino, quality=92)
        return destino, "nueva"
    except Exception as ex:
        print(f"  (FLUX falla «{esc[:36]}»: {type(ex).__name__}); biblioteca de ambiente")
    got = BIB.busca(esc, usadas=usadas_lib)
    if got:
        usadas_lib.add(got[2])
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
    rutas, descs, usadas_lib = [], [], set()
    mov = S.get("movimiento", "camera slowly pushes in, subtle natural motion, flags and banners sway")
    for k, esc in enumerate(escenas_txt):
        d = dia / "vinetas" / f"short{n}_env_{k}.jpg"
        r, origen = _consigue_escena(d, esc, usadas_lib)
        if r:
            rutas.append((r, origen)); descs.append(esc)
    if not rutas:
        raise SystemExit(f"short {n}: sin escenas de ambiente")
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
    cajas = {i: SH._caja(f.strip(), ancho=940, tam=50) for i, f in enumerate(frases)}

    # Polaroids de quien dice cada CITA (foto real, calidad + variedad), en armonía con el fondo; aparecen con la cita y se
    # quitan al acabarla; en un cruce, la anterior se queda pequeña al lado hasta que termina la segunda (como una charla).
    base0 = escenas[0][2]
    acento_s = _acento(base0.crop((0, int(base0.height * 0.45), base0.width, int(base0.height * 0.75))))
    conocidas = _conocidas()
    quotes = _citas_timeline(texto, 0, texto[:k_fin] if k_fin >= 0 else texto, T, conocidas, S.get("quien", ""))
    pol_full, pol_small = _polas_persona(dia, fecha, quotes, acento_s, 460, 320, dict(conocidas))

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
        _dibuja_polas(fr, t, quotes, pol_full, pol_small, "short")   # Polaroid de la cita en curso (y la del cruce)
        caja = cajas[frase_idx(t)]
        fr.alpha_composite(kick, (50, AL - 300 - caja.height))
        fr.alpha_composite(caja, ((AN - caja.width) // 2, AL - 250 - caja.height // 2))
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
        d.text((40, AL2 - 44), "FUENTES  ", font=fuente("Inter-Black.ttf", 24), fill=AMARILLO + (255,), anchor="lm")
        x0 = 40 + fuente("Inter-Black.ttf", 24).getlength("FUENTES  ")
        d.text((x0, AL2 - 44), fuentes[:90], font=fuente("Inter-SemiBold.ttf", 24), fill=(225, 230, 240, 255), anchor="lm")
    return cab


def largo(fecha):
    dia = RAIZ / "dia" / fecha
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    secs = [s for s in G["secciones"] if any(p.get("di") for p in s["pasos"])]
    tmp = dia / "tmp_largo_amb"
    tmp.mkdir(exist_ok=True)
    texto = " ".join(" ".join(p["di"] for p in s["pasos"]) for s in secs)
    pal, dur = voz.locuta([{"di": " ".join(p["di"] for p in s["pasos"])} for s in secs], "normal", tmp / "voz.wav", cola=0.3)
    T = E.Tiempos(texto, pal, 0.0)
    total = dur + 1.0
    import corto as _C
    # límites de bloque y escenas de ambiente por bloque
    bloques, c = [], 0
    for i, s in enumerate(secs):
        btxt = " ".join(p["di"] for p in s["pasos"])
        t0 = T.en(c)
        titulo = (s.get("titulo") or s.get("tema") or "").strip()
        fuentes = " · ".join(s.get("fuentes", [])[:4])
        quien = next((n2 for p in s["pasos"] if p.get("ve") for n2 in _C.personas_de(p["ve"])), "")
        pseudo = {"quien": quien, "cita": titulo, "contexto": btxt[:400]}
        amb_guion = [e for p in s["pasos"] for e in ((p.get("ve") or {}).get("ambiente") or []) if isinstance(e, str) and e.strip()]
        escs_txt = amb_guion[:3] or escenas_ambiente(pseudo, 3)   # las que escribe el redactor o, si no, generadas
        # SIEMPRE imagen nueva con FLUX (variedad); se guarda en la biblioteca; si FLUX falla, la mejor de la biblioteca.
        pares, descs, usadas_lib = [], [], set()
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
        cajas = [SH._caja(f.strip(), ancho=1480, tam=44) for f in frases]
        # Polaroids por CITA: cada cita «...» muestra la foto real de quien la dice; se quita al acabar; en un cruce, las dos
        base0 = escenas[0][2]
        acento = _acento(base0.crop((0, int(base0.height * 0.45), int(base0.width * 0.4), base0.height)))
        conocidas = _conocidas()
        quotes = _citas_timeline(texto, c, btxt, T, conocidas, quien)
        pol_full, pol_small = _polas_persona(dia, fecha, quotes, acento, 420, 300, dict(conocidas))
        bloques.append({"t0": t0, "i": i, "titulo": titulo, "fuentes": fuentes, "escenas": escenas,
                        "cambios": cambios or [(t0, 0)], "frases": frases, "tf": tf, "cajas": cajas,
                        "n": len(secs), "quotes": quotes, "pol_full": pol_full, "pol_small": pol_small})
        c += len(btxt) + 1
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
        _dibuja_polas(fr, t, bl.get("quotes") or [], bl.get("pol_full") or {}, bl.get("pol_small") or {}, "largo")
        fi = max([j for j, te in enumerate(bl["tf"]) if te <= t] or [0]) if bl["tf"] else 0
        if bl["cajas"]:
            caja = bl["cajas"][min(fi, len(bl["cajas"]) - 1)]
            fr.alpha_composite(caja, ((AN2 - caja.width) // 2, AL2 - 70 - caja.height))
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
    subprocess.run([V1.FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista),
                    "-i", str(tmp / "audio.wav"), "-c:v", "copy", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-ar", "48000",
                    "-c:a", "aac", "-b:a", "192k", "-shortest", str(out)], check=True)
    print(f"  render: {(time.time() - t_ini) / 60:.1f} min con {nproc} proceso(s) para {total / 60:.1f} min", flush=True)
    import shutil
    shutil.rmtree(tmp, ignore_errors=True)
    print(f"LARGO (ambiente): {total:.1f} s -> {out}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[2] == "largo":
        largo(sys.argv[1])
    else:
        short(sys.argv[1], int(sys.argv[2]))
