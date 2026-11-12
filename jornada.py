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

    def claude(self, puesto, encargo, salida, modelo="sonnet", motivo="Gemini no responde"):
        """Respaldo: el agente de Claude de siempre, solo para este puesto."""
        self.parte(f"{puesto}: {motivo}, lo hace Claude")
        prompt = (f"Eres el agente «{puesto}» de El Hoyformativo: lee y sigue .claude/agents/{puesto}.md. Fecha {self.f}. "
                  f"{encargo} Escribe {salida}. Responde en una línea.")
        try:
            subprocess.run(["claude", "-p", prompt, "--model", modelo, "--permission-mode", "auto"], cwd=RAIZ,
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
        # 10-nov (calidad): elegir las noticias es la decisión que más pesa; la hace Claude Opus (una sola llamada)
        ok = self.claude("jefe-de-edicion", "Haz el consejo de redacción.", (self.dia / "escaleta.json").relative_to(RAIZ),
                         modelo="opus", motivo="consejo de redacción (decisión editorial clave)") and bool(self.json("escaleta.json"))
        if not ok:
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
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(3) as ex:                # 3 a la vez, como los redactores en paralelo de Claude
            list(ex.map(lambda pz: self._redacta(*pz), piezas))
        self.parte(f"redacción: {len(piezas)} piezas escritas y prechequeadas")
        return True

    def _corpus(self):
        if not hasattr(self, "_corp"):
            import unicodedata, re as _re
            txt = " ".join(f.read_text(encoding="utf-8", errors="ignore") for f in
                           [*(self.dia / "dossier").glob("*.md"), *(self.dia / "articulos").glob("*.txt"), self.dia / "redes.md",
                            self.dia / "ganchos_director.md", self.dia / "noticias.json", self.dia / "ganchos.md",
                            self.dia / "encargo.json"] if f.exists())
            self._corp = self._n(txt)
        return self._corp

    @staticmethod
    def _n(t):
        import unicodedata, re as _re
        t = unicodedata.normalize("NFKC", t or "").lower()
        t = _re.sub(r"[«»“”\"'‘’]", " ", t)
        return _re.sub(r"\s+", " ", _re.sub(r"[^\w\s]", " ", t)).strip()

    def calidad_bloque(self, sal, segundos=None):
        """Lo que se puede medir sin criterio: citas literales, gancho al principio, variedad de escenas y duración."""
        import re as _re
        try:
            b = json.loads(sal.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return ["el fichero no es JSON válido"]
        if isinstance(b, list) and len(b) == 1 and isinstance(b[0], dict):   # envuelto en lista: se desenvuelve
            b = b[0]
            sal.write_text(json.dumps(b, ensure_ascii=False, indent=1), encoding="utf-8")
        if not isinstance(b, dict):
            return ["el bloque no es un objeto JSON {titulo, tono, fuentes, pasos}"]
        fallos = []
        pasos = b.get("pasos") or []
        txt = json.dumps(pasos, ensure_ascii=False)
        corp = self._corpus()
        NUM = set("cero uno una dos tres cuatro cinco seis siete ocho nueve diez once doce trece catorce quince veinte "
                  "treinta cuarenta cincuenta sesenta setenta ochenta noventa cien ciento doscientos trescientos mil millón "
                  "millones y".split())
        for c in set(_re.findall(r"«([^«»]{12,400})»", txt)):
            w = [x for x in self._n(c).split() if x not in NUM and not x.isdigit()]   # números: con letras en la voz
            if len(w) < 4 or self._n(c) in corp:
                continue
            ini, fin = " ".join(w[:4]), " ".join(w[-4:])
            if ini not in corp and fin not in corp:     # ni el principio ni el final están literales: inventada
                fallos.append(f"cita no literal en las fuentes: «{c[:90]}»")
        if pasos and "«" not in pasos[0].get("di", "")[:200] and "breve" not in txt[:300]:
            fallos.append("el primer «di» no abre con la frase gancho literal entre «»")
        tipos = [(p.get("ve") or {}).get("tipo") for p in pasos if p.get("ve")]
        if len(set(tipos)) < 3 and "breve" not in tipos:
            fallos.append(f"solo {len(set(tipos))} tipos de escena (mínimo 3)")
        if segundos:
            pal = sum(len(p.get("di", "").split()) for p in pasos)
            if pal < segundos * 2.75 * 0.75:
                fallos.append(f"se queda corto: {pal} palabras para {segundos} s (~{int(segundos * 2.75)}): añade contexto del dossier")
        return fallos

    def _redacta(self, nn, que, dos):
        if True:
            sal = self.dia / "bloques" / f"{nn}.json"
            if not sal.exists():
                self.puesto("redactor", f"Escribe {que}.", [self.dia / "escaleta.json", *dos, *self.comunes()], sal,
                            valida=lambda r: isinstance(r, dict) and r.get("pasos"))
            e = self.json("escaleta.json") or {}
            seg = next((b.get("segundos") for b in e.get("bloques", []) if f"{b['n']:02d}" == nn), None)
            for intento in range(3):                   # lo mecánico y la calidad medible, antes de la mesa
                r = subprocess.run([PY, "prechequeo.py", self.f, nn], cwd=RAIZ, capture_output=True, text=True)
                pre = "" if r.stdout.strip().endswith("OK") else r.stdout[-2500:]
                cal = self.calidad_bloque(sal, seg) if sal.exists() else ["no existe"]
                if not pre and not cal:
                    break
                problemas = (pre + "\n" + "\n".join("- " + c for c in cal)).strip()
                if intento == 2:                       # Gemini no lo ha dejado bien: lo rehace Claude (calidad)
                    self.claude("redactor", f"Bloque {nn}: corrige estos problemas de calidad:\n{problemas}",
                                sal.relative_to(RAIZ), motivo=f"bloque {nn} sin la calidad mínima tras 2 intentos de Gemini")
                    break
                self.puesto("redactor", f"Corrige {que}. Problemas detectados:\n{problemas}",
                            [sal, self.dia / "escaleta.json", *dos, *self.comunes()], sal,
                            valida=lambda r: isinstance(r, dict) and r.get("pasos"))

    def mesa(self):
        if (self.dia / "revision" / "mesa_hecha").exists():
            return True
        bloques = sorted((self.dia / "bloques").glob("*.json"))
        e = self.json("escaleta.json")
        dossieres = sorted((self.dia / "dossier").glob("*.md"))
        revs = {"verificador": "verificacion.md", "defensor-neutralidad": "neutralidad.md", "asesor-cumplimiento": "cumplimiento.md"}
        pendientes = [b.stem for b in bloques]
        for vuelta in (1, 2):
            from concurrent.futures import ThreadPoolExecutor

            def revisa(item, vuelta=vuelta, pendientes=pendientes):
                puesto, nom = item
                self.puesto(puesto, f"Revisa los bloques {', '.join(pendientes)} (vuelta {vuelta}). Una sección por bloque "
                            f"«## Bloque NN» con APTO o CORREGIR, y cada problema con la frase exacta y el cambio.",
                            [self.dia / "bloques" / f"{n}.json" for n in pendientes] + dossieres + [self.dia / "escaleta.json",
                                                                                                   *self.comunes()],
                            self.dia / "revision" / nom, "md")
            with ThreadPoolExecutor(3) as ex:            # los tres revisores a la vez
                list(ex.map(revisa, revs.items()))
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
            if vuelta == 2:                             # 10-nov (calidad): lo que Gemini no ha cerrado, Claude
                for n in corregir:
                    self.claude("verificador", f"Bloque {n}: revísalo contra su dossier y las noticias y, si hay errores, "
                                f"corrígelos tú directamente en bloques/{n}.json (también los de revision/).",
                                (self.dia / "bloques" / f"{n}.json").relative_to(RAIZ),
                                motivo=f"bloque {n} sigue en CORREGIR tras dos vueltas")
            pendientes = corregir
        (self.dia / "revision" / "mesa_hecha").touch()
        return True

    DESPEDIDA = ("Esto ha sido todo por hoy. Si te ha servido, suscríbete y activa la campanita para no perderte el "
                 "resumen de mañana. Gracias por vernos. Mañana, más.")

    def normaliza(self, E):
        """El formato exacto de CONTRATOS.md, que el montaje necesita (Gemini a veces cambia la forma del sumario o
        se deja tono y fuentes): sumario como sección con un paso «sumario», tono y fuentes en cada sección y la
        despedida como último paso."""
        e = self.json("escaleta.json") or {}
        tonos = {b.get("titulo"): b.get("tono", "normal") for b in e.get("bloques", [])}
        fuentes = {}
        for f in (self.dia / "bloques").glob("*.json"):
            try:
                b = json.loads(f.read_text(encoding="utf-8"))
                fuentes[b.get("titulo")] = b.get("fuentes", [])
            except ValueError:
                pass
        secs = []
        for k, s in enumerate(E.get("secciones", [])):
            if not s.get("pasos") and (s.get("items") or s.get("texto")):          # sumario con otra forma
                s = {"titulo": "Lo más importante del día", "pasos": [{"di": s.get("texto") or s.get("di", ""),
                     "ve": {"tipo": "sumario", "items": s.get("items", [])}}]}
            if not s.get("pasos"):
                continue
            s = {"titulo": s.get("titulo") or "Lo más importante del día", "tono": s.get("tono") or tonos.get(s.get("titulo"), "normal"),
                 "fuentes": s.get("fuentes") or fuentes.get(s.get("titulo"), []), "pasos": s["pasos"]}
            s["pasos"] = [p for p in s["pasos"] if isinstance(p, dict) and p.get("di")]
            secs.append(s)
        if secs and (secs[0]["pasos"][0].get("ve") or {}).get("tipo") == "sumario":
            for it in secs[0]["pasos"][0]["ve"].get("items", []):
                it.setdefault("texto", it.get("titular", ""))
                it.setdefault("titular", it.get("texto", ""))
        ult = secs[-1]["pasos"] if secs else []
        if not any((p.get("ve") or {}).get("tipo") == "despedida" for p in ult):
            ult.append({"di": self.DESPEDIDA, "ve": {"tipo": "despedida"}})
        E["secciones"] = secs
        E.setdefault("fecha", e.get("fecha", self.f))
        E.setdefault("titulo_video", e.get("titulo_video", ""))
        return E

    def cierre(self):
        if self.json("episodio.json"):
            return True
        ok = self.puesto("editor-de-cierre", "Monta episodio.json.", [self.dia / "escaleta.json",
                         *sorted((self.dia / "bloques").glob("*.json")), *self.comunes()], self.dia / "episodio.json",
                         valida=lambda r: isinstance(r, dict) and len(r.get("secciones", [])) >= 3)
        if ok:
            E = self.normaliza(self.json("episodio.json"))
            pal = sum(len(p["di"].split()) for s in E["secciones"] for p in s["pasos"])
            if pal / 2.75 / 60 < 3.8:                   # 11-nov: 4-5 min; si falta, más contexto del dossier
                self.parte(f"episodio corto (~{pal / 2.75 / 60:.1f} min): se amplía con contexto")
                self.puesto("editor-de-cierre", f"El episodio dura ~{pal / 2.75 / 60:.1f} min y debe durar 4-5: amplía los "
                            f"bloques con más contexto de sus dossieres (antecedentes, datos, la versión de la otra parte), sin "
                            f"inventar nada y sin tocar las citas. Devuelve el episodio.json completo.",
                            [self.dia / "episodio.json", *sorted((self.dia / "dossier").glob("*.md")), *self.comunes()],
                            self.dia / "episodio.json", valida=lambda r: isinstance(r, dict) and len(r.get("secciones", [])) >= 3)
                E = self.normaliza(self.json("episodio.json"))
            (self.dia / "episodio.json").write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
            pal = sum(len(p["di"].split()) for s in E["secciones"] for p in s["pasos"])
            self.parte(f"cierre: episodio.json listo ({len(E['secciones'])} secciones, ~{pal / 2.75 / 60:.1f} min)")
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
        return self.control_visual()

    def control_visual(self):
        """10-nov (calidad): Gemini mira las hojas de contacto como el agente de control de calidad; si ve problemas,
        entran el control de calidad y el montador de Claude, como antes (máximo una vuelta)."""
        import gem
        from PIL import Image
        hojas = sorted((self.dia / "calidad").glob("hoja_*.png"))
        if not hojas:
            return True
        partes = [{"text": "Eres el control de calidad visual de un informativo de YouTube. Mira estas hojas de contacto (un "
                   "fotograma por escena) y busca SOLO problemas graves: texto cortado o que se sale, piezas que se tapan, "
                   "escenas vacías o negras, letras inventadas en las ilustraciones, una foto que claramente no corresponde al "
                   "nombre que la acompaña (p. ej., una multitud o un objeto en un retrato), subtítulos ilegibles. Responde JSON: "
                   "{\"veredicto\": \"APTO\"|\"CORREGIR\", \"problemas\": [\"hoja N: ...\"]}"}]
        for h in hojas:
            partes += [{"text": h.name}, gem.imagen(Image.open(h), 1600)]
        r = gem.pide(partes, como_json=True) or {}
        prob = r.get("problemas") or []
        (self.dia / "calidad" / "informe_gemini.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        if r.get("veredicto") != "CORREGIR":
            self.parte("control visual (Gemini): APTO")
            return True
        self.parte(f"control visual (Gemini): CORREGIR ({len(prob)} problemas): entran control de calidad y montador de Claude")
        self.claude("control-calidad", "Revisa el vídeo. Gemini ha visto: " + "; ".join(prob)[:1500],
                    (self.dia / "calidad" / "informe.md").relative_to(RAIZ), motivo="el control visual detecta problemas")
        inf = (self.dia / "calidad" / "informe.md")
        if inf.exists() and "CORREGIR" in inf.read_text(encoding="utf-8"):
            (self.dia / "episodio.mp4").unlink(missing_ok=True)
            self.claude("montador", "Arregla lo de calidad/informe.md y vuelve a montar con largo.py.",
                        (self.dia / "episodio.mp4").relative_to(RAIZ), motivo="hay que corregir el montaje")
            if not (self.dia / "episodio.mp4").exists() and self.py("largo.py", self.f, log="render.log", timeout=7200) != 0:
                return False
        return True

    def miniatura(self):
        if (self.dia / "miniatura.png").exists():
            return True
        rc = self.py("miniatura_auto.py", self.f, log="miniatura.log", timeout=1800)
        if rc != 0 or not (self.dia / "miniatura.png").exists():   # 10-nov (calidad): por debajo de 7, el diseñador
            (self.dia / "miniatura.png").unlink(missing_ok=True)
            self.claude("disenador-grafico", "Haz la miniatura del episodio (las versiones automáticas no llegaron a 7).",
                        self.dia.relative_to(RAIZ) / "miniatura.png", motivo="la miniatura automática no llega al 7")
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
