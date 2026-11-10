"""COORDINADOR DE LA JORNADA EN PYTHON (decisión del usuario del 10-nov-2026: vídeo y Shorts dentro del 8 % del consumo
semanal del plan de Claude y, si se puede, de una ventana de 5 h). Sustituye al agente coordinador (/edicion-diaria con
Sonnet, que gastaba millones de tokens por mantener toda la jornada en su contexto): hace las mismas fases, en el mismo
orden y con los mismos ficheros (oficina/CONTRATOS.md), con programas y con Gemini haciendo de cada puesto
(agente_gemini.py, con las instrucciones de su agente). Claude solo entra si Gemini y freellmpool fallan en un puesto.
Cada fase deja una línea en parte_del_dia.md (jornada.sh la manda por Telegram) y, si su fichero ya existe, se salta:
una jornada cortada se retoma donde iba.

Uso: python jornada.py AAAA-MM-DD     (salida 0 = vídeo y Shorts subidos; 1 = fallo crítico, avisado)"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import agente_gemini as AG

RAIZ = Path(__file__).parent
PY = str(RAIZ / ".venv" / "bin" / "python")
CLAUDE_MIN = 30 * 60                                   # tope de un puesto hecho por Claude (respaldo)


class Jornada:
    def __init__(self, fecha):
        self.f = fecha
        self.dia = RAIZ / "dia" / fecha
        for d in ("dossier", "bloques", "revision", "calidad"):
            (self.dia / d).mkdir(parents=True, exist_ok=True)
        self.parte_f = self.dia / "parte_del_dia.md"

    # ---------------------------------------------------------------- utilidades
    def parte(self, txt):
        with open(self.parte_f, "a", encoding="utf-8") as fh:
            fh.write(f"{time.strftime('%H:%M')} {txt}\n")
        print(f"[{time.strftime('%H:%M')}] {txt}", flush=True)

    def py(self, *args, log=None, timeout=3600):
        out = open(self.dia / log, "a") if log else subprocess.DEVNULL
        try:
            return subprocess.run([PY, "-u", *map(str, args)], cwd=RAIZ, stdout=out, stderr=subprocess.STDOUT,
                                  timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            return 124

    def claude(self, puesto, encargo, salida):
        """Respaldo: el agente de Claude de siempre, solo para este puesto (Sonnet)."""
        self.parte(f"{puesto}: Gemini no responde, lo hace Claude")
        prompt = (f"Eres el agente «{puesto}» de El Hoyformativo: lee y sigue .claude/agents/{puesto}.md. Fecha {self.f}. "
                  f"{encargo} Escribe {salida}. Responde en una línea.")
        try:
            subprocess.run(["claude", "-p", prompt, "--model", "sonnet", "--permission-mode", "auto"], cwd=RAIZ,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=CLAUDE_MIN)
        except subprocess.TimeoutExpired:
            pass
        return Path(RAIZ / salida).exists() if not str(salida).startswith("/") else Path(salida).exists()

    def puesto(self, puesto, encargo, ficheros, salida, formato="json", valida=None):
        """Gemini hace el puesto (2 intentos); si no, Claude. Devuelve True si queda un fichero válido."""
        for _ in range(2):
            r = AG.ejecuta(puesto, self.f, encargo, ficheros, salida, formato)
            if r is not None and (valida is None or valida(r)):
                return True
        return self.claude(puesto, encargo, Path(salida).relative_to(RAIZ))

    def json(self, nombre):
        f = self.dia / nombre
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    # ---------------------------------------------------------------- fases
    def recogida(self):
        if (self.dia / "dossier" / "frases.md").exists():
            return True
        if self.py("recopila.py", log="recogida.log") != 0 or not (self.dia / "noticias.json").exists():
            return False
        self.py("temas_gemini.py", self.f, log="recogida.log")
        if not (self.dia / "temas.json").exists():
            if not self.claude("recopilador", "Agrupa noticias.json por tema.", self.dia.relative_to(RAIZ) / "temas.json"):
                return False
        for s in ("articulos.py", "erratas.py", "contexto.py", "redes.py", "ganchos.py"):
            self.py(s, self.f, log="recogida.log", timeout=1200)
        enc_ok = (self.dia / "encargo.json").exists() and self.py("encargo.py", self.f, log="recogida.log") == 0
        temas = self.json("temas.json") or []
        ids = [t["id"] for t in temas[:6]]
        if enc_ok:
            e = self.json("encargo.json") or {}
            extra = next((t["id"] for t in temas if any(w.lower() in json.dumps(t, ensure_ascii=False).lower()
                                                        for w in (e.get("persona", "").split()[-1:] or ["@@"]))), None)
            if extra and extra not in ids:
                ids.append(extra)
        for i in ids + ["frases"]:
            if self.py("investiga.py", self.f, i, log="recogida.log", timeout=900) != 0:
                self.puesto("investigador", f"Tema {i}: escribe su dossier.", [self.dia / "temas.json", self.dia / "redes.md"],
                            self.dia / "dossier" / f"{i}.md", "md")
        self.parte(f"recogida y dossieres listos ({len(list((self.dia / 'dossier').glob('*.md')))} temas)")
        return True

    def comunes(self):
        return [self.dia / "contexto.md", self.dia / "correcciones.md", self.dia / "ganchos_director.md",
                self.dia / "encargo.json"]

    def escaleta(self):
        if self.json("escaleta.json"):
            return True
        fs = [self.dia / "temas.json", self.dia / "redes.md"] + sorted((self.dia / "dossier").glob("*.md")) + self.comunes()
        ok = self.puesto("jefe-de-edicion", "Haz el consejo de redacción y escribe escaleta.json.", fs,
                         self.dia / "escaleta.json", valida=lambda r: isinstance(r, dict) and r.get("bloques"))
        if ok:
            e = self.json("escaleta.json")
            self.parte(f"escaleta: {len(e['bloques'])} bloques y {len(e.get('breves', []))} breves")
        return ok

    def _dossier(self, idt):
        f = self.dia / "dossier" / f"{idt}.md"
        return [f] if f.exists() else []

    def redaccion(self):
        e = self.json("escaleta.json")
        piezas = [(f"{b['n']:02d}", f"bloque {b['n']:02d} (id {b['id']}, «{b['titulo']}»)", self._dossier(b["id"]))
                  for b in e["bloques"]]
        if e.get("breves"):
            nb = f"{len(e['bloques']) + 1:02d}"
            piezas.append((nb, f"los breves (van todos en bloques/{nb}.json)",
                           sum((self._dossier(b.get("id", "")) for b in e["breves"]), []) + [self.dia / "temas.json"]))
        for nn, que, dos in piezas:
            sal = self.dia / "bloques" / f"{nn}.json"
            if not sal.exists():
                self.puesto("redactor", f"Escribe {que}.", [self.dia / "escaleta.json", *dos, *self.comunes()], sal,
                            valida=lambda r: isinstance(r, dict) and r.get("pasos"))
            for _ in range(2):                         # lo mecánico, antes de la mesa
                r = subprocess.run([PY, "prechequeo.py", self.f, nn], cwd=RAIZ, capture_output=True, text=True)
                if r.stdout.strip().endswith("OK") or not sal.exists():
                    break
                self.puesto("redactor", f"Corrige {que}: el prechequeo mecánico dice:\n{r.stdout[-3000:]}",
                            [sal, self.dia / "escaleta.json", *dos, *self.comunes()], sal,
                            valida=lambda r: isinstance(r, dict) and r.get("pasos"))
        self.parte(f"redacción: {len(piezas)} piezas escritas y prechequeadas")
        return True

    def mesa(self):
        if (self.dia / "revision" / "mesa_hecha").exists():
            return True
        bloques = sorted((self.dia / "bloques").glob("*.json"))
        e = self.json("escaleta.json")
        dossieres = sorted((self.dia / "dossier").glob("*.md"))
        revs = {"verificador": "verificacion.md", "defensor-neutralidad": "neutralidad.md", "asesor-cumplimiento": "cumplimiento.md"}
        pendientes = [b.stem for b in bloques]
        for vuelta in (1, 2):
            for puesto, nom in revs.items():
                self.puesto(puesto, f"Revisa los bloques {', '.join(pendientes)} (vuelta {vuelta}). Una sección por bloque "
                            f"«## Bloque NN» con APTO o CORREGIR, y cada problema con la frase exacta y el cambio.",
                            [self.dia / "bloques" / f"{n}.json" for n in pendientes] + dossieres + [self.dia / "escaleta.json",
                                                                                                   *self.comunes()],
                            self.dia / "revision" / nom, "md")
            corregir = []
            for n in pendientes:
                for nom in revs.values():
                    t = (self.dia / "revision" / nom).read_text(encoding="utf-8") if (self.dia / "revision" / nom).exists() else ""
                    sec = t.split(f"Bloque {n}")[1].split("## ")[0] if f"Bloque {n}" in t else ""
                    if "CORREGIR" in sec:
                        corregir.append(n)
                        break
            self.parte(f"mesa vuelta {vuelta}: CORREGIR en {', '.join(corregir) or 'ninguno'}")
            for n in corregir:                          # el redactor aplica lo que piden las revisiones
                sal = self.dia / "bloques" / f"{n}.json"
                b = next((x for x in e["bloques"] if f"{x['n']:02d}" == n), None)
                self.puesto("redactor", f"Bloque {n}: aplica las correcciones de las revisiones (solo lo que piden).",
                            [sal, *[self.dia / "revision" / v for v in revs.values()], *(self._dossier(b["id"]) if b else []),
                             *self.comunes()], sal, valida=lambda r: isinstance(r, dict) and r.get("pasos"))
            if not corregir:
                break
            pendientes = corregir
        (self.dia / "revision" / "mesa_hecha").touch()
        return True

    def cierre(self):
        if self.json("episodio.json"):
            return True
        ok = self.puesto("editor-de-cierre", "Monta episodio.json.", [self.dia / "escaleta.json",
                         *sorted((self.dia / "bloques").glob("*.json")), *self.comunes()], self.dia / "episodio.json",
                         valida=lambda r: isinstance(r, dict) and len(r.get("secciones", [])) >= 3)
        if ok:
            self.parte("cierre: episodio.json listo")
        return ok

    def grafica(self):
        if (self.dia / "vinetas" / "hoja.png").exists() or (self.dia / "grafica_hecha").exists():
            return True
        import corto as C
        import fotos
        G = self.json("episodio.json")
        nombres = {n for s in G["secciones"] for p in s["pasos"] if p.get("ve") for n in C.personas_de(p["ve"])}
        nombres |= {it["persona"] for p in G["secciones"][0]["pasos"] if (p.get("ve") or {}).get("tipo") == "sumario"
                    for it in p["ve"]["items"] if it.get("persona")}
        cred = self.json("creditos.json") or {}
        tienen = {c.get("persona") for c in cred.values()}
        for n in sorted(nombres - tienen):
            try:
                fotos.mejores(self.f, n, "hablando con energía", 3)
            except Exception as ex:
                print(f"  fotos de {n}: {type(ex).__name__}")
        self.py("ia_vinetas.py", "preparar", self.f, log="grafica.log", timeout=2400)
        self.py("revisa_vinetas.py", self.f, log="grafica.log", timeout=2400)
        (self.dia / "grafica_hecha").touch()
        self.parte(f"gráfica: retratos de {len(nombres)} personas y viñetas revisadas")
        return True

    def montaje(self):
        if (self.dia / "episodio.mp4").exists() and (self.dia / "escenas.json").exists():
            return True
        if self.py("largo.py", self.f, log="render.log", timeout=7200) != 0:
            return False
        self.py("control_calidad.py", self.f, log="calidad.log")
        self.parte("montaje hecho y fotogramas de control sacados")
        return True

    def miniatura(self):
        if (self.dia / "miniatura.png").exists():
            return True
        rc = self.py("miniatura_auto.py", self.f, log="miniatura.log", timeout=1800)
        if rc != 0 or not (self.dia / "miniatura.png").exists():
            self.claude("disenador-grafico", "Haz la miniatura del episodio.", self.dia.relative_to(RAIZ) / "miniatura.png")
        self.parte("miniatura lista")
        return True

    def publicacion(self):
        if not (self.dia / "publicacion.md").exists() and self.py("plataforma.py", self.f, log="publicacion.log") != 0:
            self.claude("editor-plataforma", "Prepara publicacion.md.", self.dia.relative_to(RAIZ) / "publicacion.md")
        if not (self.dia / "youtube.json").exists():
            self.py("control_calidad.py", self.f, "--ligero")
            if self.py("subir.py", self.f, log="publicacion.log", timeout=3600) != 0:
                self.parte("SUBIDA FALLIDA: mira publicacion.log")
                return False
            self.py("notifica.py", self.f)
            self.parte("vídeo subido como privado")
        if not (self.dia / "shorts" / "youtube.json").exists():
            if self.py("shorts_dia.py", self.f, log="shorts.log", timeout=3600) == 0:
                self.py("subir.py", self.f, "shorts", log="publicacion.log", timeout=3600)
                self.parte("Shorts hechos y subidos como privados")
            else:
                self.parte("hoy sin Shorts (sin frases válidas o Gemini no responde)")
        return True

    def corre(self):
        self.parte("coordinador en Python (Gemini; Claude solo de respaldo) en marcha")
        for fase in (self.recogida, self.escaleta, self.redaccion, self.mesa, self.cierre, self.grafica, self.montaje,
                     self.miniatura, self.publicacion):
            if not fase():
                self.parte(f"FALLO en {fase.__name__}")
                subprocess.run([PY, "notifica.py", self.f, "--error", f"la jornada falló en la fase «{fase.__name__}»"], cwd=RAIZ)
                return 1
        self.parte("jornada terminada")
        return 0


if __name__ == "__main__":
    sys.exit(Jornada(sys.argv[1]).corre())
