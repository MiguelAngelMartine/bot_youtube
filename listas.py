"""LISTAS DE REPRODUCCIÓN (23-nov-2026, el usuario aprueba la mejora 6: listas por duelo y personaje alargan la sesión, que
es lo que más premia YouTube, y posicionan en búsquedas). Al subir cada vídeo, subir.py lo añade a:
  - «Los cruces del día» (todos los Shorts) o «El resumen diario» (los largos);
  - la lista de cada político PRINCIPAL que sale («Pedro Sánchez: frases y cruces»).
Las listas son públicas; un vídeo privado o programado no se ve en ellas hasta que se publica. Ids en archivo/listas.json.
Cuota: crear una lista o añadir un vídeo cuesta 50 unidades (subir uno, 1.600).
Uso: python listas.py ver"""
from __future__ import annotations

import json
import sys
import unicodedata
from pathlib import Path

RAIZ = Path(__file__).parent
REG = RAIZ / "archivo" / "listas.json"
GENERALES = {
    "shorts": ("Los cruces del día · El Hoyformativo",
               "Los cruces de declaraciones de la política española, cada día: frases literales y comprobadas, con quién "
               "las dice y a quién. #PolíticaEspañola"),
    "largos": ("El resumen diario · El Hoyformativo",
               "La política española en 2 minutos: lo más impactante del día y el cruce más duro. #PolíticaEspañola"),
}
# políticos con lista propia (los que más salen y más se buscan); el nombre, como lo busca la gente
PRINCIPALES = ["Pedro Sánchez", "Alberto Núñez Feijóo", "Santiago Abascal", "Isabel Díaz Ayuso", "Gabriel Rufián",
               "Yolanda Díaz", "Carles Puigdemont", "Miguel Tellado", "Ada Colau", "Irene Montero", "Ione Belarra",
               "Óscar Puente", "Félix Bolaños", "Cayetana Álvarez de Toledo", "Diana Morant", "Ester Muñoz",
               "Mariano Rajoy", "Pablo Iglesias", "Mónica García", "Juanma Moreno"]


def _n(t):
    t = unicodedata.normalize("NFKD", (t or "").lower())
    return "".join(c for c in t if not unicodedata.combining(c)).strip()


def _principal(nombre):
    """El nombre de la lista de esa persona (por su apellido), o None si no es de las principales."""
    toks = _n(nombre).split()
    for p in PRINCIPALES:
        pt = _n(p).split()
        if toks and (toks == pt or toks[-1] == pt[-1] and (len(toks) == 1 or toks[0] == pt[0])):
            return p
    return None


def _reg():
    return json.loads(REG.read_text(encoding="utf-8")) if REG.exists() else {}


def _lista(yt, clave, titulo, desc):
    reg = _reg()
    if clave in reg:
        return reg[clave]
    r = yt.playlists().insert(part="snippet,status", body={
        "snippet": {"title": titulo[:150], "description": desc[:5000], "defaultLanguage": "es"},
        "status": {"privacyStatus": "public"}}).execute()
    reg[clave] = r["id"]
    REG.write_text(json.dumps(reg, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  lista nueva: {titulo}")
    return r["id"]


def anade(yt, video_id, tipo, personas=()):
    """Añade el vídeo a su lista general y a la de cada persona principal que sale. Devuelve los títulos de las listas."""
    hechas = []
    titulo, desc = GENERALES["shorts" if tipo == "short" else "largos"]
    destinos = [(tipo, titulo, desc)]
    for p in dict.fromkeys(filter(None, (_principal(x) for x in personas))):
        destinos.append((f"persona:{p}", f"{p}: frases y cruces · El Hoyformativo",
                         f"Las frases y los cruces de {p} en la campaña y la actualidad política, literales y con su "
                         f"fuente. #PolíticaEspañola"))
    for clave, t, d in destinos:
        try:
            pl = _lista(yt, clave, t, d)
            yt.playlistItems().insert(part="snippet", body={"snippet": {
                "playlistId": pl, "resourceId": {"kind": "youtube#video", "videoId": video_id}}}).execute()
            hechas.append(t)
        except Exception as e:                           # una lista que falla no para la subida
            print(f"  (lista «{t}» sin añadir: {type(e).__name__})")
    return hechas


if __name__ == "__main__":
    if sys.argv[1:2] == ["ver"]:
        print(json.dumps(_reg(), ensure_ascii=False, indent=1))
