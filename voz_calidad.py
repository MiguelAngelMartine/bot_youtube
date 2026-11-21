"""CONTROL DE CALIDAD DE VOZ Y GUION (21-nov-2026, petición del usuario): que Tristán suene lo más humano posible. Es control
de la voz Y del guion: la voz lee lo que el guion escribe, así que lo que suena mal se arregla reescribiendo (otra palabra,
una coma, partir una frase). 100 % gratis y local (sin APIs):
  1) PRONUNCIACIÓN por fonemas: wav2vec2 fonético (facebook/wav2vec2-xlsr-53-espeak-cv-ft) oye los sonidos uno a uno, sin
     «corregir» palabras como Whisper; espeak-ng (espeakng-loader) dice cómo deberían sonar. Se comparan palabra a palabra.
  2) Whisper «small» con nota de seguridad por palabra: las que oye con poca seguridad, dudosas.
  3) RITMO y ENTONACIÓN (con los tiempos de Whisper y el tono con librosa.pyin): tramos largos sin respirar, tramos con la
     entonación plana (de robot), velocidad atropellada o lenta y pausas raras a mitad de frase. Propone DÓNDE poner la pausa.
Uso:  from voz_calidad import analiza;  r = analiza(wav, texto)  -> {"problemas": [...], "en_citas": [...], "medidas": {...}}
CLI:  python voz_calidad.py <wav> <texto|fichero.txt>
"""
from __future__ import annotations

import re
import sys
import unicodedata
from functools import lru_cache
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).parent
MODELO_FONEMAS = "facebook/wav2vec2-xlsr-53-espeak-cv-ft"
WHISPER = "small"

# Umbrales (calibrados el 21-nov-2026 con frases buenas del canal y con «ladrillazo va, ladrillazo viene», que sonaba mal).
PER_MAL = 0.34          # error de fonemas por palabra a partir del cual la palabra «no se dice como se escribe»
MIN_FONEMAS = 4         # palabras más cortas: no se juzgan (artículos, «y», «que»…)
PROB_DUDOSA = 0.35      # seguridad de Whisper por debajo de la cual la palabra es dudosa
TRAMO_MAX_S = 4.8       # tramo de voz seguido (sin pausa) más largo que esto: falta respirar
TRAMO_MAX_PAL = 15
PAUSA_MIN = 0.16        # hueco que cuenta como pausa
PLANO_ST = 1.6          # desviación del tono (semitonos) por debajo de la cual un tramo suena plano
SILABAS_MAX = 8.2       # sílabas por segundo: más, atropellado (Tristán va a ~6,5-7)
SILABAS_MIN = 3.2       # menos, arrastrado
PAUSA_RARA = 0.75       # pausa a mitad de frase (sin signo) más larga que esto
CAMBIO_RITMO = 0.18     # un tramo (también una coletilla corta) un 18 % más rápido o lento que la mediana de la pieza

# Sonidos que, para este control, valen lo mismo (alófonos del español y diferencias que no se oyen como error).
_IGUALES = {"β": "b", "ð": "d", "ɣ": "g", "ɡ": "g", "ʝ": "j", "ʎ": "j", "ɟ": "j", "ɛ": "e", "ɔ": "o", "v": "b",
            "ŋ": "n", "ɱ": "m", "ɲ": "ɲ", "r": "ɾ", "ɪ": "i", "ʊ": "u", "ə": "e", "w": "u", "ː": ""}
_PARECIDOS = {frozenset(p) for p in [("m", "n"), ("s", "z"), ("i", "j"), ("u", "w"), ("e", "i"), ("o", "u"), ("d", "t"),
                                     ("b", "p"), ("g", "k"), ("x", "h")]}
_NEXOS = {"y", "pero", "que", "porque", "aunque", "mientras", "cuando", "donde", "como", "ni", "o", "sino", "pues", "así",
          "tras", "para", "con", "sin", "según"}


def _espeak():
    import espeakng_loader
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    EspeakWrapper.set_data_path(espeakng_loader.get_data_path())


@lru_cache(maxsize=1)
def _fonemas_modelo():
    _espeak()
    import torch
    from transformers import AutoProcessor, Wav2Vec2ForCTC
    torch.set_num_threads(4)
    return AutoProcessor.from_pretrained(MODELO_FONEMAS), Wav2Vec2ForCTC.from_pretrained(MODELO_FONEMAS).eval()


@lru_cache(maxsize=1)
def _whisper_modelo():
    from faster_whisper import WhisperModel
    return WhisperModel(WHISPER, device="cpu", compute_type="int8", cpu_threads=4)


def _sin_tildes(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()


def _palabras(texto):
    """Palabras del guion con su marca de «dentro de cita» y de «fin de frase/coma» (para saber dónde ya hay pausa)."""
    out, dentro = [], False
    for m in re.finditer(r"«|»|[\wÁÉÍÓÚÜÑáéíóúüñ'’-]+|[.,;:!?…]", texto):
        t = m.group(0)
        if t == "«":
            dentro = True
        elif t == "»":
            dentro = False
        elif re.match(r"[.,;:!?…]", t):
            if out:
                out[-1]["signo"] = t
        else:
            out.append({"w": t, "cita": dentro, "signo": ""})
    return out


def _plegar(f):
    f = "".join(_IGUALES.get(c, c) for c in f)
    return f


def _tokens(fon):
    """«aɪ» -> a i; «tʃ» se queda junto."""
    out = []
    for t in fon.split():
        t = _plegar(t)
        if not t:
            continue
        if t in ("tʃ", "dʒ", "ts"):
            out.append(t)
        elif len(t) > 1:
            out.extend(c for c in t if c.strip())
        else:
            out.append(t)
    return out


def _esperado(pals):
    """Fonemas esperados de cada palabra (espeak, español de España)."""
    _espeak()
    from phonemizer import phonemize
    from phonemizer.separator import Separator
    fon = phonemize([p["w"] for p in pals], language="es", backend="espeak", strip=True, njobs=1,
                    separator=Separator(phone=" ", word=" | ", syllable=""), with_stress=False)
    fon = [f.replace("|", " ") for f in fon]
    return [_tokens(f) for f in fon]


def _oido_fonemas(y):
    """Fonemas que oye wav2vec2, con su instante (s)."""
    import torch
    proc, mod = _fonemas_modelo()
    trozos, paso = [], 16000 * 20                      # de 20 s en 20 s (memoria y velocidad en CPU)
    for i in range(0, len(y), paso):
        seg = y[i:i + paso]
        if len(seg) < 1600:
            continue
        with torch.inference_mode():
            lg = mod(proc(seg, sampling_rate=16000, return_tensors="pt").input_values).logits[0]
        ids = lg.argmax(-1).tolist()
        prev = None
        for k, t in enumerate(ids):
            if t != prev and t != proc.tokenizer.pad_token_id:
                tok = proc.tokenizer.convert_ids_to_tokens(t)
                for f in _tokens(tok):
                    trozos.append((f, i / 16000 + k * 0.02))
            prev = t
    return trozos


def _coste(a, b):
    if a == b:
        return 0.0
    return 0.5 if frozenset((a, b)) in _PARECIDOS else 1.0


def _alinea(esp, oido):
    """Alineado de edición (Levenshtein con coste) entre la lista de fonemas esperados y los oídos.
    Devuelve, para cada fonema esperado, su coste de error y el fonema oído (o '')."""
    n, m = len(esp), len(oido)
    D = np.zeros((n + 1, m + 1), dtype=np.float32)
    D[:, 0] = np.arange(n + 1)
    D[0, :] = np.arange(m + 1) * 0.7
    for i in range(1, n + 1):
        ei = esp[i - 1]
        for j in range(1, m + 1):
            D[i, j] = min(D[i - 1, j - 1] + _coste(ei, oido[j - 1]), D[i - 1, j] + 1.0, D[i, j - 1] + 0.7)
    i, j, res, extra = n, m, [None] * n, [0.0] * (n + 1)
    while i > 0 or j > 0:
        if i > 0 and j > 0 and abs(D[i, j] - (D[i - 1, j - 1] + _coste(esp[i - 1], oido[j - 1]))) < 1e-4:
            res[i - 1] = (_coste(esp[i - 1], oido[j - 1]), j - 1); i -= 1; j -= 1
        elif i > 0 and abs(D[i, j] - (D[i - 1, j] + 1.0)) < 1e-4:
            res[i - 1] = (1.0, None); i -= 1
        else:
            extra[i] += 0.7; j -= 1                    # inserción: se carga a la palabra en curso
    return res, extra


def pronunciacion(y, pals):
    esp = _esperado(pals)
    oido = _oido_fonemas(y)
    plano, dueno = [], []
    for k, fs in enumerate(esp):
        plano += fs
        dueno += [k] * len(fs)
    res, extra = _alinea(plano, [f for f, _ in oido])
    out = []
    for k, p in enumerate(pals):
        idx = [i for i, d in enumerate(dueno) if d == k]
        if len(idx) < MIN_FONEMAS:
            continue
        err = sum(res[i][0] for i in idx) + sum(extra[i + 1] for i in idx[:-1])
        per = err / len(idx)
        oidos = [oido[res[i][1]][0] for i in idx if res[i][1] is not None]
        t = next((oido[res[i][1]][1] for i in idx if res[i][1] is not None), None)
        graves = sum(1 for i in idx if res[i][0] >= 1.0)          # sonidos claramente distintos (no «parecidos»)
        if per >= PER_MAL or (graves >= 2 and len(idx) >= 6):
            out.append({"k": k, "texto": p["w"], "per": round(per, 2), "t": t, "esperado": "".join(plano[i] for i in idx),
                        "oido": "".join(oidos)})
    return out


def _silabas(w):
    return max(1, len(re.findall(r"[aeiouáéíóúü]+", w.lower())))


def _tono(y):
    import librosa
    f0, voz, _ = librosa.pyin(y, sr=16000, fmin=60, fmax=300, frame_length=1024, hop_length=320)
    return f0, voz


def ritmo(y, texto, pals):
    """Whisper small (palabras con tiempos y seguridad) + tono: tramos sin respirar, planos, atropellados y pausas raras."""
    segs, _ = _whisper_modelo().transcribe(y, language="es", beam_size=5, word_timestamps=True, vad_filter=False)
    # sin initial_prompt a propósito: con el guion delante Whisper «oiría» lo escrito aunque la voz lo diga mal
    ws = [w for s in segs for w in (s.words or [])]
    dudosas = [{"texto": w.word.strip(), "prob": round(w.probability, 2), "t": round(w.start, 2)}
               for w in ws if w.probability < PROB_DUDOSA and len(re.sub(r"\W", "", w.word)) >= 4]
    # tramos de voz seguida (entre pausas)
    tramos, cur = [], []
    for i, w in enumerate(ws):
        if cur and w.start - cur[-1].end >= PAUSA_MIN:
            tramos.append(cur); cur = []
        cur.append(w)
    if cur:
        tramos.append(cur)
    f0, voz = _tono(y)
    problemas, medidas = [], []
    for tr in tramos:
        t0, t1 = tr[0].start, tr[-1].end
        dur = max(0.01, t1 - t0)
        texto_tr = "".join(w.word for w in tr).strip()
        sil = sum(_silabas(w.word) for w in tr) / dur
        a, b = int(t0 / 0.02), int(t1 / 0.02)
        f = f0[a:b][voz[a:b]] if b > a else np.array([])
        st = float(np.std(12 * np.log2(f / np.median(f)))) if len(f) > 20 else None
        medidas.append({"t": round(t0, 2), "dur": round(dur, 2), "pal": len(tr), "silabas_s": round(sil, 1),
                        "tono_st": round(st, 2) if st is not None else None, "texto": texto_tr[:80]})
        if (dur > TRAMO_MAX_S and len(tr) >= TRAMO_MAX_PAL):
            problemas.append({"tipo": "sin respirar", "texto": texto_tr, "t": round(t0, 2),
                              "detalle": f"{dur:.1f} s y {len(tr)} palabras seguidas sin pausa",
                              "pausa_tras": _donde_pausa(tr)})
        if st is not None and st < PLANO_ST and len(tr) >= 6:
            problemas.append({"tipo": "plano", "texto": texto_tr, "t": round(t0, 2),
                              "detalle": f"entonación plana ({st:.1f} semitonos de variación)",
                              "pausa_tras": _donde_pausa(tr) if len(tr) >= 9 else None})
        if len(tr) >= 7 and sil > SILABAS_MAX:
            problemas.append({"tipo": "atropellado", "texto": texto_tr, "t": round(t0, 2),
                              "detalle": f"{sil:.1f} sílabas por segundo", "pausa_tras": _donde_pausa(tr)})
        if len(tr) >= 5 and sil < SILABAS_MIN:
            problemas.append({"tipo": "arrastrado", "texto": texto_tr, "t": round(t0, 2),
                              "detalle": f"{sil:.1f} sílabas por segundo", "pausa_tras": None})
    # 21-nov-2026 (el usuario: «no quiero que la voz cambie de ritmo con las frases hechas ni coletillas»): un tramo, por
    # corto que sea, que va claramente más rápido o más lento que el resto de la pieza.
    validos = [m["silabas_s"] for m in medidas if m["pal"] >= 4]
    if len(validos) >= 3:
        mediana = float(np.median(validos))
        for m, tr in zip(medidas, tramos):
            if m["pal"] >= 3 and abs(m["silabas_s"] / mediana - 1) > CAMBIO_RITMO:
                problemas.append({"tipo": "cambio de ritmo", "texto": m["texto"], "t": m["t"],
                                  "detalle": f"{m['silabas_s']:.1f} sílabas por segundo frente a {mediana:.1f} del resto "
                                             f"({'más rápido' if m['silabas_s'] > mediana else 'más lento'})",
                                  "pausa_tras": None})
    # pausas largas a mitad de frase (donde el guion no tiene signo)
    con_signo = {_sin_tildes(p["w"].lower()) for p in pals if p["signo"]}
    for a_, b_ in zip(ws, ws[1:]):
        hueco = b_.start - a_.end
        prev = _sin_tildes(re.sub(r"[^\w]", "", a_.word.lower()))
        if hueco > PAUSA_RARA and not re.search(r"[.,;:!?…]$", a_.word.strip()) and prev not in con_signo:
            problemas.append({"tipo": "pausa rara", "texto": f"{a_.word.strip()} … {b_.word.strip()}", "t": round(a_.end, 2),
                              "detalle": f"silencio de {hueco:.1f} s a mitad de frase", "pausa_tras": None})
    return " ".join(w.word.strip() for w in ws), dudosas, problemas, medidas


def _donde_pausa(tr):
    """Dónde pondría un locutor la pausa: 1) donde el guion ya tiene un signo y la voz no paró (se lo «comió»);
    2) antes de un nexo (y, pero, que…) lo más cerca de la mitad del tramo."""
    n = len(tr)
    mejor, dist = None, 1e9
    for i in range(1, n - 1):
        if re.search(r"[.;:!?…»\"]$", tr[i].word.strip()):
            d = abs(i - n / 2)
            if d < dist:
                mejor, dist = tr[i].word.strip(), d
    if mejor:
        return mejor
    for i in range(2, n - 2):
        w = _sin_tildes(re.sub(r"[^\w]", "", tr[i].word.lower()))
        if w in _NEXOS:
            d = abs(i - n / 2)
            if d < dist:
                mejor, dist = tr[i - 1].word.strip(), d
    return mejor or tr[n // 2 - 1].word.strip()


def _norm_pal(t):
    return [w for w in _sin_tildes(re.sub(r"[^\w\s]", " ", t.lower())).split() if w]


def _diferencias(texto, oido):
    """Palabras del guion (≥ 5 letras, no números) que Whisper oye CLARAMENTE distintas."""
    import difflib
    a, b = _norm_pal(texto), _norm_pal(oido)
    out = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op not in ("replace", "delete"):
            continue
        oyo = " ".join(b[j1:j2])
        for w in a[i1:i2]:
            if len(w) >= 5 and not w.isdigit() and w not in oyo.replace(" ", "") and \
                    difflib.SequenceMatcher(None, w, oyo.replace(" ", "")).ratio() < 0.75 and \
                    max((difflib.SequenceMatcher(None, w, x).ratio() for x in b[j1:j2]), default=0) < 0.75:
                out.append((w, oyo))
    return out


def _mezcla(texto, frag):
    """El tramo tiene palabras de narración (fuera de las citas), no solo de una cita."""
    fuera = set(_norm_pal(re.sub(r"«[^»]*»", " ", texto)))
    dentro = set(_norm_pal(" ".join(re.findall(r"«([^»]*)»", texto))))
    return any(w in fuera and w not in dentro and len(w) >= 4 for w in _norm_pal(frag))


def _en_cita(texto, frag):
    sin = re.sub(r"«[^»]*»", " ", texto).lower()
    return _sin_tildes(frag.lower().strip(" .,…")) not in _sin_tildes(sin)


def analiza(wav, texto):
    import librosa
    y, _ = librosa.load(str(wav), sr=16000)
    pals = _palabras(texto)
    pron = pronunciacion(y, pals)
    oido, dudosas, prosodia, medidas = ritmo(y, texto, pals)
    problemas, en_citas = [], []
    for p in pron:
        it = {"texto": p["texto"], "tipo": "pronunciación", "fuente": "fonemas",
              "detalle": f"no suena como se escribe (se esperaba /{p['esperado']}/ y suena /{p['oido']}/, error {p['per']:.0%})",
              "alternativa": "otra palabra o expresión que la voz diga bien"}
        k = p["k"]
        if p["texto"][:1].isupper() and k > 0 and not pals[k - 1]["signo"] in (".", "!", "?", "…"):
            it["tipo"] = "nombre propio"                # no se cambia: se avisa solo si el error es grande
            if p["per"] >= 0.5:                        # («Feijóo» sale siempre /faixo/, 33 %: no es aviso útil)
                en_citas.append(it)
        else:
            (en_citas if pals[k]["cita"] else problemas).append(it)
    malas = {_sin_tildes(p["texto"].lower()) for p in pron}
    for w, oyo in _diferencias(texto, oido):           # Whisper small oye otra palabra (p. ej., «ladrillazo» → «trilazova»)
        if w in malas:
            continue
        malas.add(w)
        it = {"texto": w, "tipo": "se oye otra cosa", "fuente": "whisper small",
              "detalle": f"Whisper entiende «{oyo or '(nada)'}»", "alternativa": "otra palabra que la voz diga claro"}
        (en_citas if _en_cita(texto, w) else problemas).append(it)
    for d in dudosas:                                  # Whisper duda y los fonemas no lo han marcado ya
        w = _sin_tildes(re.sub(r"[^\w]", "", d["texto"].lower()))
        if w in malas:
            continue
        it = {"texto": d["texto"], "tipo": "dudosa", "fuente": "whisper small",
              "detalle": f"se entiende con poca seguridad ({d['prob']:.0%})", "alternativa": "otra palabra más clara"}
        (en_citas if _en_cita(texto, d["texto"]) else problemas).append(it)
    for p in prosodia:
        if p["tipo"] == "cambio de ritmo":
            p["alternativa"] = ("la voz cambia de velocidad aquí: vuelve a generar la voz (voz.py corrige el ritmo de cada "
                                "trozo); si se repite, cambia la coletilla por otra o intégrala en la frase anterior")
        elif p["tipo"] in ("sin respirar", "plano", "atropellado") and p.get("pausa_tras"):
            p["alternativa"] = (f"la voz no para: pon una pausa (coma, dos puntos o punto y seguido) después de «{p['pausa_tras']}» "
                                "o parte la frase en dos" if p["tipo"] != "atropellado" else
                                f"se lee atropellado: acorta la frase o pon una coma después de «{p['pausa_tras']}»")
        else:
            p["alternativa"] = "reescribe la frase para que se lea con naturalidad"
        p["fuente"] = "ritmo"
        # se puede arreglar si la pausa propuesta cae fuera de una cita (o el tramo tiene narración)
        arreglable = (p.get("pausa_tras") and not _en_cita(texto, p["pausa_tras"].strip("«»\".,;:"))) or \
            not _en_cita(texto, p["texto"]) or _mezcla(texto, p["texto"])
        (problemas if arreglable else en_citas).append(p)
    return {"problemas": problemas, "en_citas": en_citas, "oido": oido, "medidas": medidas}


if __name__ == "__main__":
    import json
    wav, txt = sys.argv[1], sys.argv[2]
    if Path(txt).exists():
        txt = Path(txt).read_text(encoding="utf-8")
    r = analiza(wav, txt)
    print(json.dumps({k: r[k] for k in ("problemas", "en_citas")}, ensure_ascii=False, indent=1))
    for m in r["medidas"]:
        print(m)
