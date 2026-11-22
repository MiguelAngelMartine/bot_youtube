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
        mono = self.monografico()
        if mono:                                         # 20-nov-2026 (el usuario): día monográfico, solo ESE tema
            claves = [c.lower() for c in mono.get("claves", [])]
            suyos = [t["id"] for t in temas if any(c in json.dumps(t, ensure_ascii=False).lower() for c in claves)]
            if suyos:
                ids, enc_ok = suyos[:6], False
                self.parte(f"día monográfico ({mono.get('tema', '')}): {len(ids)} temas del día sobre él")
            else:
                self.parte(f"AVISO: día monográfico pero ningún tema de hoy casa con {claves}: sigue la jornada normal")
        if enc_ok:
            e = self.json("encargo.json") or {}
            claves = e.get("claves") or e.get("persona", "").split()[-1:] or ["@@"]   # 21-nov: o las claves del cruce
            extra = next((t["id"] for t in temas if any(w.lower() in json.dumps(t, ensure_ascii=False).lower()
                                                        for w in claves)), None)
            if extra and extra not in ids:
                ids.append(extra)
        for i in ids + ["frases"]:
            if self.py("investiga.py", self.f, i, log="recogida.log", timeout=900) != 0:
                self.puesto("investigador", f"Tema {i}: escribe su dossier.", [self.dia / "temas.json", self.dia / "redes.md"],
                            self.dia / "dossier" / f"{i}.md", "md")
        self.parte(f"recogida y dossieres listos ({len(list((self.dia / 'dossier').glob('*.md')))} temas)")
        return True

    def monografico(self):
        """20-nov-2026 (el usuario: «los vídeos y shorts de hoy tienen que ser exclusivos del cara a cara»): si
        encargo.json trae "monografico", el largo y los Shorts del día tratan SOLO ese tema (ver NORMAS.md §5)."""
        e = self.json("encargo.json") if (self.dia / "encargo.json").exists() else None
        m = (e or {}).get("monografico")
        return m if isinstance(m, dict) and m.get("tema") else None

    def encargo_escaleta(self):
        m = self.monografico()
        if not m:
            # 21-nov-2026: Short pedido por el director con frase comprobada (encargo.py): su noticia entra también en el
            # largo, para que el Short tenga el contexto del guion aprobado.
            e = (self.json("encargo.json") if (self.dia / "encargo.json").exists() else None) or {}
            if e.get("verificada") and e.get("tema") and e.get("cruce"):      # 21-nov: Short de cruce por encargo
                quienes = ", ".join(dict.fromkeys(x["persona"] for x in e["cruce"] if x.get("verificada")))
                return (f" ENCARGO DEL DIRECTOR (dia/{self.f}/encargo.json): hoy hay un Short de cruce de declaraciones "
                        f"sobre «{e['tema']}» ({quienes}; frases comprobadas en encargo.json). Incluye un bloque sobre esa "
                        "noticia en el largo (con su dossier), con la frase, las réplicas y la contrarréplica.")
            if e.get("verificada") and e.get("tema") and e.get("persona"):
                return (f" ENCARGO DEL DIRECTOR (dia/{self.f}/encargo.json): hoy hay un Short dedicado a «{e['tema']}» con "
                        f"la frase comprobada de {e['persona']} «{e['frase']}». Incluye un bloque sobre esa noticia en el "
                        "largo (con su dossier), con las reacciones de las otras partes si las hay.")
            return ""
        return (f" ENCARGO DEL DIRECTOR (dia/{self.f}/encargo.json → monografico, manda sobre la línea editorial habitual): "
                f"HOY EL VÍDEO ES MONOGRÁFICO: TODOS los bloques tratan SOLO de «{m['tema']}»; ningún otro tema del día "
                f"entra. {m.get('instrucciones', '')} Mismo formato «todo breves» de 2:30-3:00 y breves vacío. El campo "
                "\"id\" de cada bloque tiene que ser el nombre de un dossier que exista en dossier/ (varios bloques pueden "
                "compartir dossier). Equilibrio estricto entre los dos protagonistas (mismo número de frases y de tiempo).")

    def comunes(self):
        # 19-nov-2026: NORMAS.md (la guía única: tono, paleta de coletillas, reglas del guion) y EJEMPLOS_GANCHOS.md SIEMPRE
        # van con el guionista.
        return [self.dia / "contexto.md", self.dia / "correcciones.md", self.dia / "ganchos_director.md",
                self.dia / "encargo.json", RAIZ / "archivo" / "palabras_vetadas.json",   # lista negra de palabras para la voz
                RAIZ / "NORMAS.md", RAIZ / "oficina" / "EJEMPLOS_GANCHOS.md",
                RAIZ / "archivo" / "coletillas_evitar.txt"]   # coletillas usadas estos días: NO repetir (variedad)

    def escaleta(self):
        if self.json("escaleta.json"):
            return True
        fs = [self.dia / "temas.json", self.dia / "redes.md"] + sorted((self.dia / "dossier").glob("*.md")) + self.comunes()
        # 10-nov (calidad): elegir las noticias es la decisión que más pesa; la hace Claude Opus (una sola llamada)
        ok = self.claude("jefe-de-edicion", "Haz el consejo de redacción." + self.encargo_escaleta(), (self.dia / "escaleta.json").relative_to(RAIZ),
                         modelo="opus", motivo="consejo de redacción (decisión editorial clave)") and bool(self.json("escaleta.json"))
        if not ok:
            ok = self.puesto("jefe-de-edicion", "Haz el consejo de redacción y escribe escaleta.json." + self.encargo_escaleta(), fs,
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
        minimo = 2 if (segundos or 99) <= 35 else 3        # 17-nov: piezas de 20-30 s (formato «todo breves»), 2 bastan
        if len(set(tipos)) < minimo and "breve" not in tipos:
            fallos.append(f"solo {len(set(tipos))} tipos de escena (mínimo {minimo})")
        try:                                               # 17-nov: coletillas ya usadas estos días o repetidas en la pieza
            import coletillas as COL
            fallos += [f"coletilla: {x}; cámbiala por OTRA de la paleta que no esté en coletillas_evitar.txt"
                       for x in COL.problemas(*(p.get("di", "") for p in pasos), excluir_fecha=self.f)]
        except Exception:
            pass
        try:                                               # 19-nov (usuario: «estás repitiendo partes»): nada dos veces
            import shorts_guion as SG
            reps = SG.repeticiones(" ".join(p.get("di", "") for p in pasos), n=5, cierre=False)
            if reps:
                fallos.append(f"repite partes ({'; '.join(reps[:8])}): cada dato, cita, idea y muletilla UNA sola vez")
        except Exception:
            pass
        if segundos:
            pal = sum(len(p.get("di", "").split()) for p in pasos)
            if pal < segundos * 2.75 * 0.75:
                fallos.append(f"se queda corto: {pal} palabras para {segundos} s (~{int(segundos * 2.75)}): añade contexto del dossier")
        return fallos

    def _redacta(self, nn, que, dos):
        if True:
            sal = self.dia / "bloques" / f"{nn}.json"
            # 15-nov-2026 (ESENCIA DEL CANAL, petición del usuario): el GUION lo escribe SIEMPRE Opus —es quien tiene el
            # tono ácido/Vikingo, las coletillas y el sarcasmo, y adapta el texto para que la voz lo lea bien—, NUNCA Gemini.
            if not sal.exists():
                self.claude("redactor", f"Escribe {que} en {sal.name} (lee escaleta.json y el dossier del tema).",
                            sal.relative_to(RAIZ), modelo="opus", motivo="el guion siempre lo escribe Opus")
            e = self.json("escaleta.json") or {}
            seg = next((b.get("segundos") for b in e.get("bloques", []) if f"{b['n']:02d}" == nn), None)
            for intento in range(2):                   # lo mecánico y la calidad medible, antes de la mesa
                r = subprocess.run([PY, "prechequeo.py", self.f, nn], cwd=RAIZ, capture_output=True, text=True)
                pre = "" if r.stdout.strip().endswith("OK") else r.stdout[-2500:]
                cal = self.calidad_bloque(sal, seg) if sal.exists() else ["no existe"]
                if not pre and not cal:
                    break
                problemas = (pre + "\n" + "\n".join("- " + c for c in cal)).strip()
                self.claude("redactor", f"Corrige {que} en {sal.name}: {problemas}",
                            sal.relative_to(RAIZ), modelo="opus", motivo=f"corrección de calidad del guion (bloque {nn}, Opus)")

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
                if isinstance(b, list):                    # 17-nov: Claude a veces envuelve el bloque en una lista
                    b = b[0] if b and isinstance(b[0], dict) else {}
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
            pal = sum(len(p["di"].split()) for s in E["secciones"] if not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", [])) for p in s["pasos"])
            # 17-nov-2026 (formato «todo breves»): 2:30-3:00. Se corrige si se va de ese margen (antes: ampliar si < 3,8 min)
            if not 2.2 <= pal / 2.75 / 60 <= 3.2:
                largo_ = pal / 2.75 / 60 > 3.2
                self.parte(f"episodio de ~{pal / 2.75 / 60:.1f} min: se {'recorta' if largo_ else 'amplía'} a 2:30-3:00")
                self.puesto("editor-de-cierre", f"El episodio dura ~{pal / 2.75 / 60:.1f} min y debe durar 2:30-3:00 (410-500 "
                            + ("palabras): recorta las piezas más largas quitando datos secundarios, sin tocar las citas ni las "
                               "réplicas, ritmo de breves." if largo_ else
                               "palabras): amplía un poco las piezas con datos de sus dossieres, sin inventar nada y sin tocar las citas.")
                            + " Devuelve el episodio.json completo.",
                            [self.dia / "episodio.json", *sorted((self.dia / "dossier").glob("*.md")), *self.comunes()],
                            self.dia / "episodio.json", valida=lambda r: isinstance(r, dict) and len(r.get("secciones", [])) >= 3)
                E = self.normaliza(self.json("episodio.json"))
            (self.dia / "episodio.json").write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
            # 17-nov-2026 (usuario: «se mascaba el pescao» salió dos veces en el largo): las piezas se escriben en paralelo,
            # así que el episodio ENTERO se revisa aquí: cada coletilla, una sola vez y no usada en los últimos días.
            try:
                import coletillas as COL
                for _ in range(2):
                    av = COL.problemas(*(p.get("di", "") for s in E["secciones"] for p in s["pasos"]), excluir_fecha=self.f)
                    if not av:
                        break
                    self.parte(f"coletillas repetidas en el episodio: {'; '.join(av)}")
                    self.claude("redactor", "En episodio.json cambia SOLO estas coletillas por otras distintas de la paleta de "
                                "NORMAS.md (§4) que no estén en archivo/coletillas_evitar.txt ni en el resto del "
                                f"episodio (cada coletilla, una sola vez en todo el vídeo); no toques nada más: {'; '.join(av)}",
                                (self.dia / "episodio.json").relative_to(RAIZ), modelo="opus",
                                motivo="coletillas repetidas en el episodio")
                    E = self.normaliza(self.json("episodio.json"))
                    (self.dia / "episodio.json").write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as ex:
                self.parte(f"aviso: control de coletillas no aplicado ({type(ex).__name__})")
            # 19-nov-2026 (usuario: «estás repitiendo partes», «aplícalo en todo»): el episodio ENTERO, sin repetir lo mismo
            # entre piezas (misma cita o mismo trozo de 5+ palabras); el sumario no se narra y no cuenta.
            try:
                import shorts_guion as SG
                for _ in range(2):
                    narr = " ".join(p.get("di", "") for s in E["secciones"]
                                    if not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", []))
                                    for p in s["pasos"])
                    reps = SG.repeticiones(narr, n=5, muletillas=False, cierre=False)
                    if not reps:
                        break
                    self.parte(f"repeticiones en el episodio: {'; '.join(reps[:6])}")
                    self.claude("redactor", "En episodio.json hay partes que se dicen DOS veces (entre piezas o dentro de "
                                f"una): {'; '.join(reps)}. Reescribe SOLO lo necesario para que cada dato, cita e idea salga "
                                "una sola vez en todo el vídeo, con el mismo tono Vikingo, las citas literales «» intactas y "
                                "la misma duración aproximada; no toques nada más.",
                                (self.dia / "episodio.json").relative_to(RAIZ), modelo="opus",
                                motivo="repeticiones en el episodio")
                    E = self.normaliza(self.json("episodio.json"))
                    (self.dia / "episodio.json").write_text(json.dumps(E, ensure_ascii=False, indent=1), encoding="utf-8")
            except Exception as ex:
                self.parte(f"aviso: control de repeticiones no aplicado ({type(ex).__name__})")
            pal = sum(len(p["di"].split()) for s in E["secciones"] if not any((p.get("ve") or {}).get("tipo") == "sumario" for p in s.get("pasos", [])) for p in s["pasos"])
            self.parte(f"cierre: episodio.json listo ({len(E['secciones'])} secciones, ~{pal / 2.75 / 60:.1f} min)")
            try:                                           # registra las coletillas del largo y refresca el «a evitar» para los Shorts
                import coletillas as COL
                COL.registra(self.f, *(p.get("di", "") for s in E["secciones"] for p in s["pasos"]))
                COL.escribe_evitar(RAIZ / "archivo" / "coletillas_evitar.txt")
            except Exception:
                pass
        return ok

    def grafica(self):
        if (self.dia / "vinetas" / "hoja.png").exists() or (self.dia / "grafica_hecha").exists():
            return True
        # 20-nov-2026 (el usuario): formato «presentador» SIEMPRE (NORMAS.md §6). Ya no se buscan fotos ni se generan viñetas
        # con FLUX: el montaje usa solo Imagenes/ (fondos, presentador y políticos). La fase solo avisa de quién no tiene imagen.
        if True:
            import presentador as PR
            G = self.json("episodio.json")
            _, _, pols = PR.catalogo()
            quienes = {it.get("nombre") or it.get("persona") for s in G["secciones"] for p in s["pasos"]
                       for it in ((p.get("ve") or {}).get("items") or []) if isinstance(it, dict) and it.get("cita")}
            sin = sorted(q for q in quienes if q and not PR.figura_de(q, pols, {}))
            (self.dia / "grafica_hecha").touch()
            self.parte("gráfica: formato presentador" + (f"; sin imagen en Imagenes/Políticos: {', '.join(sin)}" if sin else ""))
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
        if (self.dia / "episodio.mp4").exists():
            return True
        # 15-nov-2026 (petición del usuario): estilo vigente = escenas de ambiente + Polaroid (render_ambiente),
        # ya no el tablero antiguo (largo.py).
        # 21-nov-2026 (el usuario): control de calidad de VOZ Y GUION también en el largo (voz_calidad, local y gratis).
        # Lo que no suena natural vuelve a Opus (palabra, pausa o partir la frase); las citas no se tocan.
        self.control_voz_largo()
        if self.py("prevuelo_voz.py", self.f, "largo", log="calidad.log", timeout=3600) != 0 and \
                (self.dia / "calidad" / "prevuelo_voz.md").exists():
            self.parte("control de voz del largo: tras corregir aún hay cosas a revisar (calidad/prevuelo_voz.md)")
        # 20-nov-2026 (el usuario): formato «presentador» SIEMPRE (presentador.py; NORMAS.md §6).
        if self.py("presentador.py", self.f, "largo", log="render.log", timeout=7200) != 0:
            return False
        # render_ambiente no deja escenas.json: las hojas de contacto para el control visual (Gemini) las saca hojas.py
        # muestreando el mp4.
        self.py("hojas.py", self.f, log="calidad.log")
        self.parte("montaje hecho y fotogramas de control sacados")
        return self.control_visual()

    def control_voz_largo(self):
        import re as _re
        ep = self.dia / "episodio.json"
        try:
            import prechequeo as PQ
            import prevuelo_voz as PV
            G = json.loads(ep.read_text(encoding="utf-8"))
            lista = []
            for s_ in G.get("secciones", []):
                txt = " ".join(p.get("di", "") for p in s_.get("pasos", []))
                if txt.strip():
                    v = PV.revisa(txt)
                    lista += [f"[sección «{s_.get('titulo', '')[:30]}»] [{p.get('tipo', 'oído')}] «{p['texto'][:90]}»: "
                              f"{p.get('detalle', '')} → {p.get('alternativa', '')}" for p in v["problemas"]]
            if not lista:
                self.parte("control de voz del largo: suena natural")
                return
            self.parte(f"control de voz del largo: {len(lista)} cosas que no suenan naturales, vuelven a Opus")
            antes = ep.read_text(encoding="utf-8")
            citas = lambda t: sorted(PQ._n(c) for c in _re.findall(r"«([^»]+)»", " ".join(
                p.get("di", "") for s_ in json.loads(t).get("secciones", []) for p in s_.get("pasos", []))))
            self.claude("redactor", f"Control de calidad de VOZ Y GUION del vídeo largo (dia/{self.f}/episodio.json): la "
                        f"locución no suena natural en: {'; '.join(lista)}. Arregla CADA punto en el texto \"di\" de su "
                        "paso: cambia la palabra que la voz no dice bien por otra natural, o pon la pausa (coma, dos puntos "
                        "o punto y seguido) donde se indica, o parte la frase en dos. Las citas «» se quedan letra a letra. "
                        "No cambies nada más del fichero.", ep.relative_to(RAIZ), modelo="opus",
                        motivo="control de calidad de voz del largo")
            try:
                ok = citas(ep.read_text(encoding="utf-8")) == citas(antes)
            except ValueError:
                ok = False
            if not ok:
                ep.write_text(antes, encoding="utf-8")
                self.parte("control de voz del largo: Opus tocó una cita o rompió el fichero; se queda el guion anterior")
        except Exception as ex:
            ep_ok = ep.exists()
            self.parte(f"control de voz del largo sin hacer ({type(ex).__name__}{'' if ep_ok else ', sin episodio.json'})")

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
            self.claude("montador", "Arregla lo de calidad/informe.md y vuelve a montar con render_ambiente.py.",
                        (self.dia / "episodio.mp4").relative_to(RAIZ), motivo="hay que corregir el montaje")
            if not (self.dia / "episodio.mp4").exists() and self.py("render_ambiente.py", self.f, "largo", log="render.log", timeout=7200) != 0:
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
        # 15-nov-2026: render_ambiente no escribe episodio_descripcion.txt (lo hacía el motor antiguo) y plataforma.py lo
        # necesita: lo genera descripcion.py desde episodio.json + creditos.json (capítulos, fuentes, aviso de IA, créditos).
        self.py("descripcion.py", self.f, log="publicacion.log")
        if not (self.dia / "publicacion.md").exists() and self.py("plataforma.py", self.f, log="publicacion.log") != 0:
            self.claude("editor-plataforma", "Prepara publicacion.md.", self.dia.relative_to(RAIZ) / "publicacion.md")
        # 21-nov-2026 (el usuario): NO se sube a YouTube sin su OK. Se le manda por Telegram y se sube cuando lo aprueba
        # (`subir.py FECHA`), así no se gastan subidas en versiones que luego se rehacen (límite diario de YouTube).
        if not (self.dia / "youtube.json").exists() and not (self.dia / "revision.json").exists():
            self.py("control_calidad.py", self.f, "--ligero")
            if self.py("notifica.py", self.f, "--pide-ok", "largo") != 0:
                self.parte("NO SE PUDO MANDAR EL VÍDEO POR TELEGRAM")
                return False
            self.parte("vídeo enviado por Telegram para revisar; se sube a YouTube cuando el usuario dé el OK")
        return True

    def shorts(self):
        # 16-nov-2026 (petición del usuario): los Shorts se hacen y suben ANTES que el vídeo largo. Solo dependen del
        # cierre (episodio.json), no del largo. La cuota de FLUX es fresca a las 10:30; si se agota, la biblioteca cubre.
        carpeta = self.dia / "shorts"
        if (carpeta / "youtube.json").exists() or (carpeta / "revision.json").exists():
            return True
        import json as _json
        import time
        enc = self.dia / "encargo.json"
        try:
            num = int(_json.loads(enc.read_text(encoding="utf-8")).get("num_shorts", 2)) if enc.exists() else 2
        except (ValueError, TypeError, OSError):
            num = 2
        # 1) SELECCIÓN de frases + borrador: shorts_guion.py (Gemini; la selección sí puede ser de Gemini).
        for intento in range(2):
            r = subprocess.run([PY, "-u", "shorts_guion.py", self.f, str(num)], cwd=RAIZ)
            if r.returncode != 2:
                break
            if intento == 0:
                time.sleep(180)
        jsons = sorted(carpeta.glob("short_*.json"), key=lambda x: int(x.stem.split("_")[1])) if carpeta.exists() else []
        try:                                               # 22-nov: los Shorts del encargo ya montados no se retocan
            hechos = {int(k) for k in (_json.loads(enc.read_text(encoding="utf-8")).get("shorts_hechos") or [])} if enc.exists() else set()
        except (ValueError, TypeError, OSError):
            hechos = set()
        jsons = [j for j in jsons if int(j.stem.split("_")[1]) not in hechos]
        if not jsons:
            self.parte("hoy sin Shorts (sin frases válidas o Gemini no responde)")
            return True
        # 2) ESENCIA DEL CANAL: el GUION de cada Short lo escribe SIEMPRE Opus (tono ácido/Vikingo, coletillas, adaptado a
        # la voz), SOLO su propio tema (prohibido el bleed). Opus reescribe «voz» y «ambiente» de cada short_N.json.
        borrador = {j: _json.loads(j.read_text(encoding="utf-8")).get("voz", "") for j in jsons}   # comprobado literal
        for j in jsons:
            mf = (_json.loads(j.read_text(encoding="utf-8")) or {}).get("mejores_frases")
            extra = (" Es un Short de LAS MEJORES FRASES de una sola persona (campo \"frases\"): salen TODAS sus frases "
                     "literales «», en ese orden, cada una con su contexto breve, sin declarar ganador ni valorar quién "
                     "estuvo mejor (NORMAS.md §3).") if mf else ""
            self.claude("redactor", extra.strip() + f" Reescribe SOLO los campos \"voz\" y \"ambiente\" de {j.name} (un Short vertical de "
                        "25-40 s). Tono Vikingo ácido y desenfadado con coletillas y frases hechas (lee tu agente y "
                        "NORMAS.md (§4)). Usa SOLO el tema de ESTE Short (su gancho, cita, contexto y réplica); "
                        "PROHIBIDO colar material de otros Shorts o bloques (bleed). Escribe para el formato PRESENTADOR "
                        "(NORMAS.md §4 «Escribir para el presentador»: cada cita literal sola, con quién la dice JUSTO antes, "
                        "y una frase del presentador entre cita y cita). Si tiene réplica, sigue «El Short de cruce modelo» "
                        "(NORMAS.md §4): frase que lo desata, puente de ≤ 12 palabras, réplica; contexto del presentador "
                        "entre cruces; remate neutral; pregunta corta con el nombre; ≤ 60 s (unas 145 palabras con el cierre). Abre con el gancho literal, sin "
                        "preguntas en el cuerpo. El gancho se dice UNA SOLA VEZ: ni la entrada ni la cita que viene "
                        "después lo repiten (si la cita empieza por el gancho, tras él va solo el RESTO de la cita). NADA SE "
                        "DICE DOS VECES: cada dato, cada cita y cada idea, una sola vez; si la entrada ya lo cuenta, el "
                        "contexto no lo vuelve a contar, y si la réplica ya está, no se anuncia otra vez. Tampoco repitas "
                        "muletillas («según él», «lo suyo», «y claro»...) ni uses fórmulas fijas como «Y la explicación es "
                        "esta»: varía los enlaces. Al terminar, relee el guion entero buscando repeticiones. Nada de «.:» ni «?:», y cierra con la pregunta final nombrando a quien dijo la frase + «Te leo "
                        "en comentarios» y suscríbete. En «ambiente», SOLO sitios relacionados con la política (Senado, Congreso, "
                        "Moncloa, palacios de congresos, sedes de partidos, parlamentos, ayuntamientos, ministerios, salas de "
                        "prensa) o paisajes urbanos sobrios; nunca playas, puertos, terrazas ni calles turísticas. No toques "
                        "las citas «» ni los demás campos.",
                        j.relative_to(RAIZ), modelo="opus", motivo="el guion de los Shorts siempre lo escribe Opus")
        import shorts_guion as SG                          # 19-nov (usuario: «estás repitiendo partes»): control medible
        for j in jsons:
            voz_ = _json.loads(j.read_text(encoding="utf-8")).get("voz", "")
            reps = SG.repeticiones(voz_) + SG.vetadas(voz_)        # 19-nov: y nunca «zasca»
            if reps:
                self.parte(f"{j.name}: repeticiones o palabras prohibidas en el guion ({'; '.join(reps[:6])}), vuelve a Opus")
                self.claude("redactor", f"El campo \"voz\" de {j.name} REPITE partes o usa palabras prohibidas: {'; '.join(reps)}. "
                            "Reescríbelo sin palabras prohibidas y para que cada dato, cita, idea y muletilla salga UNA sola vez, con el mismo tono Vikingo, las "
                            "mismas citas literales «» y el mismo cierre. No toques los demás campos.",
                            j.relative_to(RAIZ), modelo="opus", motivo="quitar repeticiones del guion del Short")
        for j in jsons:                                    # 20-nov-2026: Opus no puede cambiar ni «completar» una cita
            inv = SG.citas_inventadas(self.f, _json.loads(j.read_text(encoding="utf-8")).get("voz", ""))
            if inv:
                self.parte(f"{j.name}: citas que no están literales en las fuentes ({'; '.join(c[:40] for c in inv)}), vuelve a Opus")
                self.claude("redactor", f"El campo \"voz\" de {j.name} trae citas «» que NO están literales en las fuentes: "
                            f"{'; '.join(inv)}. Pon las citas EXACTAMENTE como están en el borrador comprobado, letra a letra "
                            f"(sin completarlas ni retocarlas): {borrador[j]} No toques los demás campos.",
                            j.relative_to(RAIZ), modelo="opus", motivo="cita no literal en el guion del Short")
                S_ = _json.loads(j.read_text(encoding="utf-8"))
                if SG.citas_inventadas(self.f, S_.get("voz", "")):
                    S_["voz"] = borrador[j]               # sin arreglo: el borrador, que ya estaba comprobado
                    j.write_text(_json.dumps(S_, ensure_ascii=False, indent=1), encoding="utf-8")
                    self.parte(f"{j.name}: Opus sigue sin respetar las citas: va el borrador comprobado")
        try:                                               # 20-nov-2026: CONTROL DE LECTURA (prevuelo_voz) de cada Short
            import prevuelo_voz as PV
            for j in jsons:
                S_ = _json.loads(j.read_text(encoding="utf-8"))
                antes = S_.get("voz", "")
                v = PV.revisa(antes)
                fuera = v.get("problemas", [])
                if fuera:
                    # 21-nov-2026: control de VOZ Y GUION (voz_calidad): palabra mal dicha, tramo sin respirar, plano o
                    # atropellado. Se arregla escribiendo: otra palabra, una pausa (coma, dos puntos, punto) o partir la frase.
                    lista = "; ".join(f"[{p.get('tipo', 'oído')}] «{p['texto'][:90]}»: {p.get('detalle', '')} → {p.get('alternativa', '')}"
                                      for p in fuera)
                    self.parte(f"{j.name}: control de voz: {lista[:240]}, vuelve a Opus")
                    self.claude("redactor", f"Control de calidad de VOZ Y GUION del campo \"voz\" de {j.name}: la locución no "
                                f"suena natural en: {lista}. Arregla CADA punto como se indica: cambia la palabra que la voz "
                                "no dice bien por otra natural, o pon la pausa (coma, dos puntos o punto y seguido) donde se "
                                "indica, o parte la frase en dos. Fuera de las citas «» (las citas, letra a letra como están). "
                                "No toques los demás campos.", j.relative_to(RAIZ), modelo="opus",
                                motivo="control de calidad de voz del Short")
                    S2 = _json.loads(j.read_text(encoding="utf-8"))
                    if SG.citas_inventadas(self.f, S2.get("voz", "")):
                        S2["voz"] = antes                 # Opus tocó una cita: vuelve el texto anterior (ya comprobado)
                        j.write_text(_json.dumps(S2, ensure_ascii=False, indent=1), encoding="utf-8")
                        self.parte(f"{j.name}: Opus cambió una cita al arreglar la voz; se queda el texto anterior")
                    elif S2.get("voz", "") != antes:
                        v2 = PV.revisa(S2["voz"])           # segunda escucha
                        if v2.get("problemas"):
                            self.parte(f"{j.name}: AVISO, tras corregir aún suena raro: "
                                       + "; ".join(f"«{p['texto'][:40]}» ({p.get('tipo')})" for p in v2["problemas"])[:200])
                        v = v2
                if v.get("en_citas"):
                    self.parte(f"{j.name}: AVISO, dentro de una cita literal suena raro: "
                               + "; ".join(f"«{p['texto']}»" for p in v["en_citas"])[:200] + " (revisa el Short antes de publicar)")
        except Exception as ex:
            self.parte(f"control de lectura de los Shorts sin hacer ({type(ex).__name__})")
        try:                                               # registra las coletillas de los Shorts (variedad para mañana)
            import coletillas as COL
            COL.registra(self.f, *(_json.loads(j.read_text(encoding="utf-8")).get("voz", "") for j in jsons))
        except Exception:
            pass
        # 3) RENDER de cada Short con el motor de ambiente.
        hechos = []
        for j in jsons:
            k = j.stem.split("_")[1]
            if self.py("presentador.py", self.f, k, log="shorts.log", timeout=1800) == 0 and (carpeta / f"short_{k}.mp4").exists():
                hechos.append(k)
        if hechos:
            import shorts_dia
            shorts_dia.hoja(carpeta)
            self.py("notifica.py", self.f, "--pide-ok", "shorts")      # 21-nov-2026: sin el OK del usuario no se suben
            self.parte(f"{len(hechos)} Shorts (guion Opus) enviados por Telegram para revisar; se suben con el OK del usuario")
        else:
            self.parte("hoy sin Shorts (fallo al renderizar)")
        return True

    def corre(self):
        self.parte("coordinador en Python (Gemini; Claude solo de respaldo) en marcha")
        try:                                               # coletillas usadas estos días -> el redactor NO las repite
            import coletillas as COL
            COL.escribe_evitar(RAIZ / "archivo" / "coletillas_evitar.txt")
        except Exception:
            pass
        for fase in (self.recogida, self.escaleta, self.redaccion, self.mesa, self.cierre, self.shorts, self.grafica,
                     self.montaje, self.miniatura, self.publicacion):
            if not fase():
                self.parte(f"FALLO en {fase.__name__}")
                subprocess.run([PY, "notifica.py", self.f, "--error", f"la jornada falló en la fase «{fase.__name__}»"], cwd=RAIZ)
                return 1
        self.parte("jornada terminada")
        return 0


if __name__ == "__main__":
    sys.exit(Jornada(sys.argv[1]).corre())
