"""TÍTULOS APTOS PARA ANUNCIOS (10-nov-2026, camino a la monetización): los insultos personales y los tacos en el título o
la miniatura hacen saltar los «anuncios limitados» de YouTube. La frase literal puede ir en el vídeo y en la descripción,
pero el título se elige entre candidatos limpios. Las descalificaciones políticas («corrupto», «dictador») no se tocan."""
import re
import unicodedata

TACOS = ["payaso", "idiota", "imbecil", "gilipollas", "cabron", "mierda", "cono", "hostia", "puta", "puto", "joder",
         "huevos", "capullo", "subnormal", "mamarracho", "cojones", "polla", "zorra", "maricon", "retrasado", "tonto",
         "estupido", "hijo de", "sinverguenza", "chulo", "pringado"]


def _n(t):
    return unicodedata.normalize("NFKD", (t or "").lower()).encode("ascii", "ignore").decode()


def limpio(texto):
    t = _n(texto)
    return not any(re.search(r"\b" + re.escape(x) + r"\b", t) for x in TACOS)


def elige(*candidatos):
    """El primer candidato sin tacos ni insultos personales; si ninguno lo es, el último (respaldo neutro)."""
    for c in candidatos:
        if c and limpio(c):
            return c
    return candidatos[-1]
