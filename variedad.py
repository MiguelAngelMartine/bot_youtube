"""VARIEDAD DE IMÁGENES (decisión del usuario del 8-nov-2026): una foto o una viñeta usada en un vídeo o un Short no se
vuelve a usar hasta pasados 7 días, para que el canal no parezca repetitivo.

Registro: archivo/imagenes_usadas.json  {"foto:<página de Commons o url>": "AAAA-MM-DD", "vin:<sha1 del jpg>": ..., "bib:<id>": ...}
- subir.py llama a registra_dia(fecha) después de subir el vídeo largo o los Shorts (lo que de verdad se publicó).
- fotos.py (mejores, buscar, elegir), ia_vinetas.py (ilustra, de_biblioteca) consultan reciente() y buscan otra.
El mismo día sí se puede repetir (largo, Shorts y miniatura comparten fotos).
Uso: python variedad.py registra AAAA-MM-DD  |  python variedad.py estado"""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

RAIZ = Path(__file__).parent
REG = RAIZ / "archivo" / "imagenes_usadas.json"
DIAS = 7


# Fotos vetadas para siempre (no son quien dicen: 9-nov-2026, "Santiago Abascal" de aiaraldea.eus era otra persona)
VETADAS = ("File:Santiago_Abascal_Escuza.jpg", "File:Reuni%C3%B3n_del_CECOPI_por_el_accidente_ferroviario_de_Urda_-_55619911237.jpg", "File:Reuni%C3%B3n_del_CECOPI_en_Toledo_-_55618943296.jpg", "File:Madrid_Gay_Pride_2026_-_Parade_-_260704_192440.jpg",)   # 9-nov: fotos de grupo donde no se ve a la persona


def _lee():
    try:
        return json.loads(REG.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _fecha(f):
    return date.fromisoformat(str(f)[:10]) if f else date.today()


def reciente(clave, fecha=None, dias=DIAS):
    """La fecha en que se usó si fue en los `dias` anteriores (sin contar el mismo día); si no, None."""
    if not clave:
        return None
    if any(v in clave for v in VETADAS):
        return "9999-12-31"
    u = _lee().get(clave)
    if not u:
        return None
    hoy = _fecha(fecha)
    d = date.fromisoformat(u)
    return u if hoy - timedelta(days=dias) < d < hoy else None


def clave_foto(cred):
    return "foto:" + (cred.get("pagina") or cred.get("url") or "").split("?")[0] if cred else ""


def clave_vineta(ruta):
    try:
        return "vin:" + hashlib.sha1(Path(ruta).read_bytes()).hexdigest()[:20]
    except OSError:
        return ""


def marca(claves, fecha):
    reg = _lee()
    f = str(_fecha(fecha))
    for c in claves:
        if c and reg.get(c, "") < f:
            reg[c] = f
    REG.parent.mkdir(exist_ok=True)
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=0, sort_keys=True), encoding="utf-8")


def registra_dia(fecha_txt):
    """Marca como usadas hoy las fotos de imagenes/ con crédito, las viñetas del día y las de la biblioteca."""
    dia = RAIZ / "dia" / fecha_txt
    claves = []
    cred = json.loads((dia / "creditos.json").read_text(encoding="utf-8")) if (dia / "creditos.json").exists() else {}
    for nom, c in cred.items():
        if (dia / "imagenes" / nom).exists() and not nom.endswith(("_recorte.png", "_caricatura.jpg")):
            claves.append(clave_foto(c))
    for v in (dia / "vinetas").glob("s*_*.jpg") if (dia / "vinetas").exists() else []:
        claves.append(clave_vineta(v))
    origen = dia / "vinetas" / "origen.json"
    if origen.exists():
        for o in json.loads(origen.read_text(encoding="utf-8")).values():
            if isinstance(o, dict) and o.get("biblioteca"):
                claves.append("bib:" + o["biblioteca"])
    marca(claves, fecha_txt[:10])
    print(f"variedad: {len([c for c in claves if c])} imágenes marcadas como usadas el {fecha_txt[:10]}")


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "registra":
        registra_dia(sys.argv[2])
    else:
        r = _lee()
        print(f"{len(r)} imágenes registradas; {sum(1 for v in r.values() if reciente('x') is None and _fecha(None) - date.fromisoformat(v) < timedelta(days=DIAS))} bloqueadas esta semana")
