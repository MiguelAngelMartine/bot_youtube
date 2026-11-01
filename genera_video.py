"""Agentes 5-7, VOZ + IMAGEN + MONTAJE: del guion.json del dia a video.mp4 (1080p), subtitulos.srt y descripcion.txt.
Voz gratuita (edge-tts, voces neuronales de Microsoft, sin clave), diapositivas propias (Pillow) y ffmpeg (imageio-ffmpeg).
Uso: python genera_video.py [AAAA-MM-DD] [voz]"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import wave
from datetime import datetime
from pathlib import Path

import edge_tts
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FF = imageio_ffmpeg.get_ffmpeg_exe()
AN, AL = 1920, 1080
FONDO, TARJETA, TEXTO, GRIS, ROJO, AMARILLO = "#0f1a2e", "#16243d", "#f2f4f8", "#9aa7bd", "#c8102e", "#f1bf00"
F = str(Path(__file__).parent / "fuentes") + "/"     # tipografias libres (OFL) del repositorio: Inter, Barlow Condensed, Caveat
PAUSA = 0.7                     # silencio al final de cada seccion (s)


def fuente(nombre, tam):
    return ImageFont.truetype(F + nombre, tam)


def parte_lineas(d, texto, f, ancho):
    palabras, lineas, l = texto.split(), [], ""
    for p in palabras:
        prueba = (l + " " + p).strip()
        if d.textlength(prueba, font=f) <= ancho:
            l = prueba
        else:
            lineas.append(l)
            l = p
    return lineas + ([l] if l else [])


def diapositiva(sec, i, n, fecha, ruta):
    im = Image.new("RGB", (AN, AL), FONDO)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, AN, 14], fill=ROJO)
    d.rectangle([0, 14, AN, 22], fill=AMARILLO)
    d.text((110, 70), "RESUMEN POLÍTICO · ESPAÑA", font=fuente("Inter-Bold.ttf", 34), fill=AMARILLO)
    d.text((AN - 110, 70), fecha, font=fuente("Inter-Regular.ttf", 34), fill=GRIS, anchor="ra")
    if i > 0:
        d.text((110, 150), f"{i:02d}", font=fuente("Inter-Bold.ttf", 60), fill=ROJO)
    ft = fuente("Inter-Bold.ttf", 76 if i else 96)
    y = 240 if i else 300
    for l in parte_lineas(d, sec["titulo"], ft, AN - 220):
        d.text((110, y), l, font=ft, fill=TEXTO)
        y += 96 if i else 118
    y += 40
    fp = fuente("Inter-Regular.ttf", 46)
    for p in sec["puntos"]:
        ls = parte_lineas(d, p, fp, AN - 330)
        alto = 62 * len(ls) + 34
        d.rounded_rectangle([110, y, AN - 110, y + alto], radius=18, fill=TARJETA)
        d.rectangle([110, y, 122, y + alto], fill=AMARILLO if i == 0 else ROJO)
        yy = y + 17
        for l in ls:
            d.text((160, yy), l, font=fp, fill=TEXTO)
            yy += 62
        y += alto + 22
    if sec.get("fuentes"):
        d.text((110, AL - 80), "Fuentes: " + " · ".join(sec["fuentes"]), font=fuente("Inter-Regular.ttf", 30), fill=GRIS)
    if i > 0:                                                    # barra de avance
        d.rectangle([0, AL - 12, AN, AL], fill=TARJETA)
        d.rectangle([0, AL - 12, int(AN * i / (n - 1)), AL], fill=AMARILLO)
    im.save(ruta)


async def voz(texto, mp3, voz_nombre, rate="+4%", pitch="+0Hz"):
    com = edge_tts.Communicate(texto, voz_nombre, rate=rate, pitch=pitch)
    frases = []
    with open(mp3, "wb") as f:
        async for c in com.stream():
            if c["type"] == "audio":
                f.write(c["data"])
            elif c["type"] in ("SentenceBoundary", "WordBoundary"):
                frases.append((c["offset"] / 1e7, (c["offset"] + c["duration"]) / 1e7, c["text"]))
    return frases


def a_wav(mp3, wav):
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", str(mp3), "-af", f"apad=pad_dur={PAUSA}",
                    "-ar", "48000", "-ac", "2", str(wav)], check=True)
    with wave.open(str(wav)) as w:
        return w.getnframes() / w.getframerate()


def hms(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)) % 1000:03d}"


def trocea(frases, maximo=11):
    """Las frases largas se parten en trozos de ~11 palabras repartiendo su tiempo, para que el subtitulo se lea."""
    out = []
    for a, b, txt in frases:
        p = txt.split()
        k = max(1, -(-len(p) // maximo))
        paso = (b - a) / k
        for j in range(k):
            out.append((a + j * paso, a + (j + 1) * paso, " ".join(p[j * len(p) // k:(j + 1) * len(p) // k])))
    return out


def main(dia_txt=None, voz_nombre="es-ES-AlvaroNeural"):
    dia = Path(__file__).parent / "dia" / (dia_txt or datetime.now().strftime("%Y-%m-%d"))
    G = json.loads((dia / "guion.json").read_text(encoding="utf-8"))
    tmp = dia / "tmp"
    tmp.mkdir(exist_ok=True)
    secs = G["secciones"]
    t0, srt, tramos, n_sub = 0.0, [], [], 1
    for i, s in enumerate(secs):
        png, mp3, wav, mp4 = (tmp / f"s{i}.{e}" for e in ("png", "mp3", "wav", "mp4"))
        diapositiva(s, i, len(secs), G["fecha"], png)
        frases = asyncio.run(voz(s["texto"], mp3, voz_nombre))
        dur = a_wav(mp3, wav)
        subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-framerate", "25", "-i", str(png), "-i", str(wav),
                        "-c:v", "libx264", "-tune", "stillimage", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "160k", "-t", f"{dur:.3f}", str(mp4)], check=True)
        for a, b, txt in trocea(frases):
            srt.append(f"{n_sub}\n{hms(t0 + a)} --> {hms(t0 + b)}\n{txt}\n")
            n_sub += 1
        tramos.append((t0, s["titulo"]))
        t0 += dur
        print(f"  sección {i}: {dur:5.1f} s  {s['titulo']}", flush=True)
    lista = tmp / "lista.txt"
    lista.write_text("".join(f"file 's{i}.mp4'\n" for i in range(len(secs))), encoding="utf-8")
    subprocess.run([FF, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    str(dia / "video.mp4")], check=True)
    (dia / "subtitulos.srt").write_text("\n".join(srt), encoding="utf-8")
    fuentes = sorted({f for s in secs for f in s.get("fuentes", [])})
    capitulos = "\n".join(f"{int(t // 60):d}:{int(t % 60):02d} {tit}" for t, tit in tramos)
    desc = (f"{G['titulo_video']}\n\nLo más relevante de la política española del {G['fecha'].lower()}, en unos minutos.\n\n"
            f"Capítulos:\n{capitulos}\n\nFuentes: {', '.join(fuentes)}.\n\n"
            "Resumen elaborado con ayuda de inteligencia artificial a partir de noticias publicadas por los medios citados, "
            "y revisado antes de su publicación. Voz sintética.")
    (dia / "descripcion.txt").write_text(desc, encoding="utf-8")
    print(f"VIDEO {t0/60:.1f} min -> {dia / 'video.mp4'}")


if __name__ == "__main__":
    main(*(sys.argv[1:3]))
