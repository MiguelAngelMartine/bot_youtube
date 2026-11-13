"""BIBLIOTECA DE VIÑETAS DE AMBIENTE (13-nov-2026, decisión del usuario): cada escena de ambiente que se genera con FLUX
se guarda y se etiqueta de forma descriptiva para construir una biblioteca. Dos categorías: «animadas» (la escena tiene
su clip de vídeo IA) y «simples» (solo la imagen). SIEMPRE se intenta crear una imagen nueva primero (máxima variedad);
la generada se guarda; y solo si FLUX falla se busca en la biblioteca la que mejor encaje por el contexto.
Carpeta: canal/biblioteca_ambiente/{simples,animadas}/ + catalogo.json."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import time
from pathlib import Path

RAIZ = Path(__file__).parent
BIB = RAIZ / "canal" / "biblioteca_ambiente"
CAT = BIB / "catalogo.json"
_STOP = {"a", "an", "the", "of", "in", "on", "at", "with", "and", "or", "no", "not", "to", "from", "by", "for", "as",
         "is", "are", "be", "scene", "shot", "wide", "establishing", "view", "background", "foreground", "image",
         "illustration", "comic", "ligne", "claire", "style", "spanish", "spain", "drawn", "detailed", "empty"}


def _kw(desc):
    """Palabras clave descriptivas de una escena (en inglés), para localizarla luego por el contexto."""
    ws = re.findall(r"[a-zá-úñ]+", (desc or "").lower())
    return sorted({w for w in ws if len(w) >= 3 and w not in _STOP})


def _catalogo():
    if CAT.exists():
        try:
            return json.loads(CAT.read_text(encoding="utf-8"))
        except ValueError:
            return []
    return []


def _guarda_cat(cat):
    BIB.mkdir(parents=True, exist_ok=True)
    CAT.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")


def guarda(img, descripcion, clip=None):
    """Añade (o mejora) una escena a la biblioteca. img: imagen generada; clip: su mp4 animado, si lo hay.
    Devuelve el id. No duplica por contenido; si ya estaba como simple y ahora llega con clip, la sube a animada."""
    img = Path(img)
    if not img.exists():
        return None
    try:
        h = hashlib.sha1(img.read_bytes()).hexdigest()[:16]
    except OSError:
        return None
    cat = _catalogo()
    ent = next((e for e in cat if e.get("hash") == h), None)
    animada = bool(clip and Path(clip).exists())
    sub = "animadas" if animada else "simples"
    (BIB / sub).mkdir(parents=True, exist_ok=True)
    if ent is None:
        dest = BIB / sub / f"{h}.jpg"
        if not dest.exists():
            shutil.copy(img, dest)
        ent = {"id": h, "hash": h, "img": f"{sub}/{h}.jpg", "clip": None, "categoria": sub[:-1],
               "desc": descripcion.strip()[:300], "palabras": _kw(descripcion), "fecha": time.strftime("%Y-%m-%d")}
        cat.append(ent)
    if animada and not ent.get("clip"):                   # sube de simple a animada: copia el clip y mueve la imagen
        (BIB / "animadas").mkdir(parents=True, exist_ok=True)
        cdest = BIB / "animadas" / f"{h}.mp4"
        if not cdest.exists():
            shutil.copy(clip, cdest)
        idest = BIB / "animadas" / f"{h}.jpg"
        if not idest.exists():
            shutil.copy(BIB / ent["img"], idest)
        ent["img"], ent["clip"], ent["categoria"] = f"animadas/{h}.jpg", f"animadas/{h}.mp4", "animada"
    _guarda_cat(cat)
    return h


def busca(descripcion, animada=None, usadas=()):
    """La escena de la biblioteca que mejor encaja con `descripcion` (solape de palabras clave). animada: True/False para
    forzar categoría, None cualquiera. usadas: ids a evitar si hay alternativa. Devuelve (ruta_img, ruta_clip|None, id) o None."""
    cat = _catalogo()
    if not cat:
        return None
    kw = set(_kw(descripcion))
    cand = [e for e in cat if animada is None or (e.get("categoria") == "animada") == animada]
    if not cand:
        cand = cat
    def punt(e):
        solape = len(kw & set(e.get("palabras", [])))
        return (solape, -0 if e["id"] in usadas else 1, e.get("fecha", ""))
    cand = [e for e in cand if e["id"] not in usadas] or cand
    mejor = max(cand, key=punt)
    img = BIB / mejor["img"]
    if not img.exists():
        return None
    clip = BIB / mejor["clip"] if mejor.get("clip") and (BIB / mejor["clip"]).exists() else None
    return img, clip, mejor["id"]


if __name__ == "__main__":                                # resumen de la biblioteca
    cat = _catalogo()
    na = sum(1 for e in cat if e.get("categoria") == "animada")
    print(f"biblioteca_ambiente: {len(cat)} escenas ({na} animadas, {len(cat) - na} simples) en {BIB}")
    for e in cat[-10:]:
        print(f"  [{e['categoria']}] {e['id']} · {', '.join(e.get('palabras', [])[:8])} · {e.get('desc', '')[:60]}")
