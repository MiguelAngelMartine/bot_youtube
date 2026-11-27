"""FUENTES DEL FUTURO CANAL DE FÚTBOL (27-nov-2026, el usuario: «añade los periódicos deportivos, AS, Marca, Sport, Mundo
Deportivo, Culemanía... y las cuentas oficiales de los clubes, futbolistas, medios de comunicación, El Chiringuito, Pedrerol,
Juanma Rodríguez, esRadio, Jota Jordi, José Álvarez y todos los integrantes del Chiringuito»).

Catálogo SEPARADO del canal de política (no lo usa la jornada de El Hoyformativo). Tono del canal: neutral y ácido con todos
(memoria «demo-deportes-tono»): por eso hay prensa de Madrid y de Barcelona, que se compensan.

  MEDIOS: nombre -> RSS, o búsqueda de Google Noticias del último día si no hay RSS útil: «gnews:dominio[/ruta]» (por
  web) o «gnewsq:texto» (por palabras, p. ej. «site:cadenaser.com fútbol»). Se piden con UA de navegador (Sport da 406
  con otro).
  X: grupo -> {nombre: cuenta}. Igual que en política, lista CERRADA: solo se cita una cuenta que pasó «comprueba.py»
  (existe, el nombre cuadra y tiene seguidores de cuenta real), para no citar nunca una parodia.
Comprobación: python futbol/comprueba.py  -> futbol/fuentes_comprobadas.md"""

MEDIOS = {
    # prensa deportiva
    "Marca": "https://e00-marca.uecdn.es/rss/portada.xml",
    "AS": "https://feeds.as.com/mrss-s/pages/as/site/as.com/portada",
    "AS · Primera": "https://feeds.as.com/mrss-s/pages/as/site/as.com/section/futbol/subsection/primera",
    "Sport": "https://www.sport.es/es/rss/last-news/news.xml",
    "Mundo Deportivo": "https://www.mundodeportivo.com/rss/home",
    "Culemanía": "gnewsq:culemania",                       # sin RSS propio (404) ni índice por dominio
    "Relevo": "gnews:relevo.com",
    "Estadio Deportivo": "gnews:estadiodeportivo.com",
    "Defensa Central": "gnews:defensacentral.com",
    "El Desmarque": "gnews:eldesmarque.com",
    # televisión y radio
    "El Chiringuito": "gnewsq:\"El Chiringuito\"",          # lo que se publica sobre el programa (trae también ecos de sociedad)
    "esRadio / Libertad Digital Deportes": "gnews:libertaddigital.com/deportes",
    "Cadena SER (deportes)": "gnewsq:site:cadenaser.com fútbol",
    "COPE (deportes)": "gnewsq:site:cope.es fútbol",
    "Onda Cero (deportes)": "gnews:ondacero.es/deportes",
    "RTVE Deportes": "gnews:rtve.es/deportes",
    # sección de deportes de los generalistas (los mismos del canal de política)
    "El País · Deportes": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/deportes/portada",
    "El Mundo · Deportes": "https://e00-elmundo.uecdn.es/elmundodeporte/rss/portada.xml",
    "ABC · Deportes": "https://www.abc.es/rss/2.0/deportes/",
    "La Vanguardia · Deportes": "https://www.lavanguardia.com/rss/deportes.xml",
    "20minutos · Deportes": "https://www.20minutos.es/rss/deportes/",
    "El Confidencial · Deportes": "https://rss.elconfidencial.com/deportes/",
    "Europa Press · Deportes": "https://www.europapress.es/rss/rss.aspx?ch=00067",
    "EFE · Deportes": "gnews:efe.com/deportes",
}

X = {
    "Instituciones": {
        "LaLiga": "LaLiga", "RFEF": "rfef", "Selección española": "SEFutbol", "UEFA (español)": "UEFAcom_es",
        "Champions League": "ChampionsLeague", "CSD": "deportegob", "Javier Tebas": "Tebasjavier",
    },
    # Primera 2026-27 (ascendidos: Racing, Deportivo y Málaga) y los de 2025-26; los descendidos se quedan por si vuelven
    "Clubes": {
        "Real Madrid": "realmadrid", "FC Barcelona": "FCBarcelona_es", "Atlético de Madrid": "Atleti",
        "Athletic Club": "AthleticClub", "Villarreal": "VillarrealCF", "Real Betis": "RealBetis", "Sevilla": "SevillaFC",
        "Real Sociedad": "RealSociedad", "Valencia": "valenciacf", "Celta": "RCCelta", "Osasuna": "Osasuna",
        "Girona": "GironaFC", "Rayo Vallecano": "RayoVallecano", "Mallorca": "RCD_Mallorca", "Espanyol": "RCDEspanyol",
        "Alavés": "Alaves", "Getafe": "GetafeCF", "Elche": "elchecf", "Levante": "LevanteUD", "Real Oviedo": "RealOviedo",
        "Racing de Santander": "realracingclub", "Deportivo": "RCDeportivo", "Málaga": "MalagaCF",
    },
    "Presidentes y entrenadores": {
        "Joan Laporta": "JoanLaportaFCB", "Diego Pablo Simeone": "Simeone",
    },
    # 27-nov-2026: sin cuenta oficial de X localizable (fuera hasta que se compruebe una): Lamine Yamal, Raphinha,
    # Julián Álvarez, Nico Williams; Culemanía, Jugones, Movistar Plus+ fútbol y Matías Prats Chacón, igual. @pablogavi
    # (Gavi) fuera: 29.709 seguidores, impropio de él (la marca azul se compra). A confirmar a mano antes de citar:
    # Oyarzabal (@mikel10oyar), Quique de Lucas (@Q1QE22), José Álvarez Haya (@10JoseAlvarez): el nombre cuadra pero
    # tienen pocos seguidores o no están verificados.
    "Futbolistas": {
        "Kylian Mbappé": "KMbappe", "Vinícius Júnior": "vinijr", "Jude Bellingham": "BellinghamJude",
        "Thibaut Courtois": "thibautcourtois", "Fede Valverde": "fedeevalverde", "Rodrygo": "RodrygoGoes",
        "Dani Carvajal": "DaniCarvajal92", "Pedri": "Pedri",
        "Robert Lewandowski": "lewy_official", "Frenkie de Jong": "DeJongFrenkie21",
        "Marc-André ter Stegen": "mterstegen1", "Antoine Griezmann": "AntoGriezmann", "Koke": "Koke6",
        "Jan Oblak": "oblakjan", "Iñaki Williams": "Williaaams45", "Mikel Oyarzabal": "mikel10oyar", "Isco": "isco_alarcon",
        "Iago Aspas": "aspas10",
    },
    "Medios": {
        "Marca": "marca", "AS": "diarioas", "Sport": "sport", "Mundo Deportivo": "mundodeportivo", "Relevo": "relevo", "Estadio Deportivo": "Estadio_ED", "Defensa Central": "defcentral",
        "El Chiringuito": "elchiringuitotv", "esRadio": "esradio", "Radio MARCA": "radiomarca",
        "El Larguero (SER)": "ellarguero", "Carrusel Deportivo (SER)": "carrusel", "Tiempo de Juego (COPE)": "tjcope",
        "El Partidazo de COPE": "partidazocope", "DAZN España": "DAZN_ES",
        "Teledeporte": "teledeporte",
    },
    # 27-nov-2026: no hay lista oficial de la temporada (el programa pasó a Mediaset en agosto); son los habituales
    # conocidos. Que la cuenta exista no dice que sigan en el programa.
    "El Chiringuito": {
        "Josep Pedrerol": "jpedrerol", "Juanma Rodríguez": "juanma_rguez", "Jota Jordi": "jotajordi13",
        "José Álvarez Haya": "10JoseAlvarez", "Tomás Roncero": "As_TomasRoncero", "Cristóbal Soria": "cristobalsoria",
        "Alfredo Duro": "alfredoduro1", "Lobo Carrasco": "lobo_carrasco", "Edu Aguirre": "eduaguirre7",
        "Paco Buyo": "Francisco_Buyo", "Jorge D'Alessandro": "pibedale", "Carme Barceló": "carmebarcelo",
        "Quim Domènech": "quimdomenech", "Quique de Lucas": "Q1QE22", "Siro López": "sirolopez",
        "Paco García Caridad": "pacogcaridad", "Guti": "GUTY14HAZ",
        "Kike Mateu": "kike_mateu", "Toni Freixa": "tonifreixa",
    },
}


UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"}


def url_de(fuente):
    from urllib.parse import quote_plus
    g = "https://news.google.com/rss/search?q={}+when:1d&hl=es&gl=ES&ceid=ES:es"
    if fuente.startswith("gnewsq:"):
        return g.format(quote_plus(fuente[7:]))
    if fuente.startswith("gnews:"):
        return g.format(quote_plus("site:" + fuente[6:]))
    return fuente
