"""episodio_descripcion.txt desde episodio.json + creditos.json (15-nov-2026): el motor nuevo (render_ambiente) no lo
escribe —lo hacía el antiguo (episodio.py)— y plataforma.py lo necesita. Capítulos estimados por duración (2,75 pal/s),
fuentes de las secciones, aviso de IA/voz sintética y créditos de las fotos reales usadas en las Polaroids.
Uso: python descripcion.py AAAA-MM-DD   (no reescribe si ya existe)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import genera_video2 as G2

RAIZ = Path(__file__).parent
WPS = 2.75
MARCA = 3.0                                    # golpe de marca al inicio


def escribe(fecha, forzar=False):
    dia = RAIZ / "dia" / fecha
    destino = dia / "episodio_descripcion.txt"
    if destino.exists() and not forzar:
        return destino
    G = json.loads((dia / "episodio.json").read_text(encoding="utf-8"))
    secs = G["secciones"]
    t, cap = MARCA, ["0:00 Inicio"]
    for s in secs:
        if not (not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", []))):
            continue                                    # 17-nov: el sumario ya no se monta en el vídeo
        pal = sum(len(p.get("di", "").split()) for p in s.get("pasos", []))
        if t >= 10:
            cap.append(f"{int(t // 60)}:{int(t % 60):02d} {s.get('titulo', '')}")
        t += pal / WPS + 1.0
    fuentes = sorted({x for s in secs for x in s.get("fuentes", []) if x})
    desc = (f"{G['titulo_video']}\n\n{G2.MARCA.title().replace(' En ', ' en ')}: lo más relevante de la política española "
            f"del {G['fecha'].lower()}, con datos, citas textuales y la fuente de cada información.\n\n"
            f"Capítulos:\n" + "\n".join(cap) + f"\n\nFuentes: {', '.join(fuentes)}.\n\n"
            "Resumen informativo elaborado con ayuda de inteligencia artificial a partir de noticias publicadas por los "
            "medios citados, y revisado por el equipo editorial antes de su publicación. Voz sintética con licencia "
            "comercial. Música original del canal. Las escenas de ambiente son ilustraciones generadas con IA (estilo "
            "línea clara); no representan a personas reales.")
    cj = dia / "creditos.json"
    if cj.exists():
        try:
            cred = json.loads(cj.read_text(encoding="utf-8"))
            vistos, lineas = set(), []
            for c in (cred.values() if isinstance(cred, dict) else cred):
                if not isinstance(c, dict):
                    continue
                aut, lic = c.get("autor", ""), c.get("licencia", "")
                pag = c.get("pagina") or c.get("url", "")
                if aut and (aut, pag) not in vistos:
                    vistos.add((aut, pag))
                    lineas.append(f"- {aut} ({lic}): {pag}")
            if lineas:
                desc += ("\n\nFotografías de archivo (licencias libres, adaptadas al color y encuadre del canal):\n"
                         + "\n".join(lineas[:20]))
        except (ValueError, OSError):
            pass
    destino.write_text(desc, encoding="utf-8")
    return destino


if __name__ == "__main__":
    d = escribe(sys.argv[1], forzar="--forzar" in sys.argv)
    print(f"episodio_descripcion.txt listo -> {d}")
