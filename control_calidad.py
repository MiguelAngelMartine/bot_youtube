"""Herramienta del CONTROL DE CALIDAD: saca un fotograma de cada escena (cuando ya han aparecido sus elementos), hojas de
contacto de 4 en 4 y datos.md con duracion, volumen (LUFS) y sincronia de la voz segun render.log.
Uso: python control_calidad.py AAAA-MM-DD [--ligero]   (--ligero: solo hace la copia 720p para el movil)"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()


def fotograma(video, t, salida):
    subprocess.run([FF, "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                    "-vf", "scale=960:540", str(salida)], check=True)


def ligero(dia):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(dia / "episodio.mp4"), "-vf", "scale=1280:720", "-c:v", "libx264",
                    "-crf", "26", "-preset", "veryfast", "-c:a", "aac", "-b:a", "128k", str(dia / "episodio_720p.mp4")], check=True)
    print(f"copia ligera -> {dia / 'episodio_720p.mp4'}")


def main(dia_txt, solo_ligero=False):
    dia = Path(__file__).parent / "dia" / dia_txt
    if solo_ligero:
        return ligero(dia)
    cal = dia / "calidad"
    cal.mkdir(exist_ok=True)
    E = json.loads((dia / "escenas.json").read_text(encoding="utf-8"))
    video = dia / "episodio.mp4"
    fotos = []
    for k, e in enumerate(E["escenas"]):
        # al 85 % de la escena ya han entrado todos sus elementos y aun no ha empezado el fundido de salida
        t = e["t0"] + max(0.5, (e["t1"] - e["t0"]) * 0.85 - 0.4)
        f = cal / f"escena_{k:02d}.png"
        fotograma(video, t, f)
        fotos.append((f, e, t))
    for extra, t in (("entrada", 2.5), ("cierre", E["fin_voz"] + 3.0)):
        fotograma(video, t, cal / f"{extra}.png")
    for h in range(0, len(fotos), 4):
        hoja = Image.new("RGB", (1920, 1080))
        for j, (f, _, _) in enumerate(fotos[h:h + 4]):
            hoja.paste(Image.open(f), ((j % 2) * 960, (j // 2) * 540))
        hoja.save(cal / f"hoja_{h // 4}.png")
    r = subprocess.run([FF, "-i", str(video), "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    lufs = re.findall(r"I:\s+(-?[\d.]+) LUFS", r.stderr)
    log = (dia / "render.log").read_text(encoding="utf-8", errors="replace") if (dia / "render.log").exists() else ""
    sinc = re.findall(r"bloque (\d+):\s+([\d.]+) s, (\d+)/(\d+) palabras", log)
    avisos = [l.strip() for l in log.splitlines() if "AVISO" in l or "Traceback" in l or "Error" in l]
    datos = [f"# Datos técnicos · {dia_txt}", "", f"- Duración: {E['total'] / 60:.1f} min ({E['total']:.0f} s)",
             f"- Volumen integrado: {lufs[-1] if lufs else '?'} LUFS (objetivo -14)", "- Sincronía voz-texto por bloque:"]
    datos += [f"  - bloque {b}: {s} s, {n}/{m} palabras" for b, s, n, m in sinc]
    datos += ["- Avisos del render: " + ("ninguno" if not avisos else "")] + [f"  - {a}" for a in avisos]
    datos += ["", "## Fotogramas", "| fichero | segundo | bloque | tono | escena |", "|---|---|---|---|---|"]
    datos += [f"| {f.name} | {t:.1f} | {e['titulo']} | {e['tono']} | {e['tipo']} |" for f, e, t in fotos]
    datos += ["", "Además: entrada.png (s 2,5) y cierre.png (pantalla final)."]
    (cal / "datos.md").write_text("\n".join(datos), encoding="utf-8")
    print("\n".join(datos[:8 + len(sinc) + len(avisos)]))
    print(f"{len(fotos)} fotogramas y {(len(fotos) + 3) // 4} hojas en {cal}")


if __name__ == "__main__":
    main(sys.argv[1], "--ligero" in sys.argv)
