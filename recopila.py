"""Agente 1, RECOPILADOR: noticias de politica espanola de las ultimas 24 h en medios de lineas distintas (RSS publicos).
Guarda dia/AAAA-MM-DD/noticias.json con titular, resumen, medio, enlace y hora."""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import feedparser
import requests

FUENTES = {
    "El País": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/espana/portada",
    "El Mundo": "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
    "ABC": "https://www.abc.es/rss/2.0/espana/",
    "elDiario.es": "https://www.eldiario.es/rss/politica/",
    "La Vanguardia": "https://www.lavanguardia.com/rss/politica.xml",
    "Europa Press": "https://www.europapress.es/rss/rss.aspx?ch=00066",
    "20minutos": "https://www.20minutos.es/rss/nacional/",
    "El Confidencial": "https://rss.elconfidencial.com/espana/",
    # sin RSS util (el de RTVE se quedo en 2022, La Razon bloquea, Publico lo quito): busqueda RSS de Google Noticias
    # por dominio. Solo trae el titular; si una noticia entra en el guion, se lee entera.
    "RTVE": "gnews:rtve.es",
    "La Razón": "gnews:larazon.es",
    "Público": "gnews:publico.es",
    "EFE": "gnews:efe.com",                 # 8-nov-2026: agencia, buena fuente de declaraciones (petición del usuario)
}
UA = {"User-Agent": "Mozilla/5.0 (resumen politico diario; uso personal)"}


def url_de(fuente: str) -> str:
    if fuente.startswith("gnews:"):
        return f"https://news.google.com/rss/search?q=site:{fuente[6:]}+when:1d&hl=es&gl=ES&ceid=ES:es"
    return fuente


def limpia(t: str) -> str:
    t = re.sub(r"<[^>]+>", " ", html.unescape(t or ""))
    return re.sub(r"\s+", " ", t).strip()


def main(horas: float = 24.0) -> Path:
    ahora = datetime.now(timezone.utc)
    desde = ahora - timedelta(hours=horas)
    noticias, estado = [], {}
    for medio, url in FUENTES.items():
        try:
            r = requests.get(url_de(url), headers=UA, timeout=20)
            f = feedparser.parse(r.content)
            n = 0
            for e in f.entries:
                t = e.get("published_parsed") or e.get("updated_parsed")
                fecha = datetime(*t[:6], tzinfo=timezone.utc) if t else None
                if fecha and fecha < desde:
                    continue
                gn = url.startswith("gnews:")
                titular = limpia(e.get("title"))
                if gn:                                        # Google anade " - Medio" al titular y no trae entradilla
                    titular = re.sub(r"\s+-\s+[^-]+$", "", titular)
                noticias.append({"medio": medio, "titular": titular,
                                 "resumen": "" if gn else limpia(e.get("summary") or e.get("description"))[:600],
                                 "enlace": e.get("link"), "hora": fecha.isoformat() if fecha else None})
                n += 1
            estado[medio] = f"{n} noticias (HTTP {r.status_code})"
        except Exception as ex:                       # un medio caido no para a los demas
            estado[medio] = f"FALLO {type(ex).__name__}"
    dia = Path(__file__).parent / "dia" / ahora.astimezone().strftime("%Y-%m-%d")
    dia.mkdir(parents=True, exist_ok=True)
    (dia / "noticias.json").write_text(json.dumps(noticias, ensure_ascii=False, indent=1), encoding="utf-8")
    for m, s in estado.items():
        print(f"  {m:16s} {s}")
    print(f"TOTAL {len(noticias)} noticias -> {dia / 'noticias.json'}")
    return dia


if __name__ == "__main__":
    main(float(sys.argv[1]) if len(sys.argv) > 1 else 24.0)
